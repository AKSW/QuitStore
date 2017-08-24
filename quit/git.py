import os
import pygit2
import re
import logging

from datetime import datetime
from exceptions import RepositoryNotFound, RevisionNotFound, NodeNotFound
from rdflib import Graph, Literal, URIRef, ConjunctiveGraph, Dataset, BNode
from quit.namespace import FOAF, RDFS, PROV, QUIT, is_a, XSD
from quit.utils import graphdiff, clean_path
from quit.cache import Cache
from quit.benchmark import benchmark

PROPERTY_REGEX = r"^((?P<key>([\w0-9_]+))\s*:\s*((?P<value>([\w0-9_]+))|(?P<quoted>(\".*\"|'[^']*'))))"

logger = logging.getLogger('quit.git')

# roles
role_author = QUIT['author']
role_committer = QUIT['committer']

CACHE = Cache()

def _git_timestamp(ts, offset):
    import quit.utils as tzinfo
    if offset == 0:
        tz = tzinfo.TZ(0, "UTC")
    else:
        hours, rem = divmod(abs(offset), 60)
        tzname = 'UTC%+03d:%02d' % ((hours, -hours)[offset < 0], rem)
        tz = tzinfo.TZ(offset, tzname)
    return datetime.fromtimestamp(ts, tz)


class Repository(object):
    def __init__(self, path, **params):
        origin = params.get('origin', None)

        try:
            self._repository = pygit2.Repository(path)
        except KeyError:
            if not params.get('create', False):
                raise RepositoryNotFound('Repository "%s" does not exist' % path)

            if origin:
                self.callback = self._callback(origin)
                pygit2.clone_repository(url=origin, path=path, bare=False)
            else:
                pygit2.init_repository(path)

        name = os.path.basename(path).lower()

        self.name = name
        self.path = path
        self.params = params

    def _callback(self, origin):
        """Set a pygit callback for user authentication when acting with remotes.
        This method uses the private-public-keypair of the ssh host configuration.
        The keys are expected to be found at ~/.ssh/
        Warning: Create a keypair that will be used only in QuitStore and do not use
        existing keypairs.
        Args:
            username: The git username (mostly) given in the adress.
            passphrase: The passphrase of the private key.
        """
        from os.path import expanduser
        ssh = join(expanduser('~'), '.ssh')
        pubkey = join(ssh, 'id_quit.pub')
        privkey = join(ssh, 'id_quit')

        from re import search
        # regex to match username in web git adresses
        regex = '(\w+:\/\/)?((.+)@)*([\w\d\.]+)(:[\d]+){0,1}\/*(.*)'
        p = search(regex, origin)
        username = p.group(3)

        passphrase = ''

        try:
            credentials = Keypair(username, pubkey, privkey, passphrase)
        except Exception:
            self.logger.debug('GitRepo, setcallback: Something went wrong with Keypair')
            return

        return RemoteCallbacks(credentials=credentials)

    def _clone(self, origin, path):
        try:
            self.addRemote('origin', origin)
            repo = pygit2.clone_repository(
                url=origin, path=path, bare=False, callbacks=self.callback
            )
            return repo
        except Exception:
            raise Exception('Could not clone from', origin)

    @property
    def is_empty(self):
        return self._repository.is_empty

    @property
    def is_bare(self):
        return self._repository.is_bare

    def close(self):
        self._repository = None

    def revision(self, id='HEAD'):
        try:
            commit = self._repository.revparse_single(id)
        except KeyError:
            raise RevisionNotFound(id)

        return Revision(self, commit)

    def revisions(self, name=None, order=pygit2.GIT_SORT_REVERSE):
        seen = set()

        def lookup(name):
            for template in ['refs/heads/%s', 'refs/tags/%s']:
                try:
                    return self._repository.lookup_reference(template % name)
                except KeyError:
                    pass
            raise RevisionNotFound(ref)

        def traverse(ref, seen):
            for commit in self._repository.walk(ref.target, order):
                oid = commit.oid
                if oid not in seen:
                    seen.add(oid)
                    yield Revision(self, commit)

        def iter_commits(name, seen):
            commits = []

            if not name:
                for name in self.branches:
                    ref = self._repository.lookup_reference(name)
                    commits += traverse(ref, seen)
            else:
                ref = lookup(name)
                commits += traverse(ref, seen)
            return commits

        return iter_commits(name, seen)

    @property
    def branches(self):
        return [x for x in self._repository.listall_references() if x.startswith('refs/heads/')]

    @property
    def tags(self):
        return [x for x in self._repository.listall_references() if x.startswith('refs/tags/')]

    @property
    def tags_or_branches(self):
        return [
            x for x in self._repository.listall_references()
            if x.startswith('refs/tags/') or x.startswith('refs/heads/')
        ]

    def index(self, revision=None):
        index = Index(self)
        if revision:
            index.set_revision(revision)
        return index

    def pull(self, remote_name='origin', branch='master'):
        for remote in self._repository.remotes:
            if remote.name == remote_name:
                remote.fetch()
                remote_master_id = self._repository.lookup_reference(
                    'refs/remotes/origin/{}'.format(branch)
                ).target
                merge_result, _ = self._repository.merge_analysis(remote_master_id)

                # Up to date, do nothing
                if merge_result & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE:
                    return

                # We can just fastforward
                elif merge_result & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD:
                    self._repository.checkout_tree(self._repository.get(remote_master_id))
                    try:
                        master_ref = self._repository.lookup_reference('refs/heads/%s' % (branch))
                        master_ref.set_target(remote_master_id)
                    except KeyError:
                        self._repository.create_branch(branch, repo.get(remote_master_id))
                    self._repository.head.set_target(remote_master_id)

                elif merge_result & pygit2.GIT_MERGE_ANALYSIS_NORMAL:
                    self._repository.merge(remote_master_id)

                    if self._repository.index.conflicts is not None:
                        for conflict in repo.index.conflicts:
                            logging.error('Conflicts found in: {}'.format(conflict[0].path))
                        raise AssertionError('Conflicts, ahhhhh!!')

                    user = self._repository.default_signature
                    tree = self._repository.index.write_tree()
                    commit = self._repository.create_commit(
                        'HEAD', user, user, 'Merge!', tree,
                        [self._repository.head.target, remote_master_id]
                    )
                    # We need to do this or git CLI will think we are still merging.
                    self._repository.state_cleanup()
                else:
                    raise AssertionError('Unknown merge analysis result')

    def push(self, remote_name='origin', ref='refs/heads/master:refs/heads/master'):
        for remote in self._repository.remotes:
            if remote.name == remote_name:
                remote.push(ref)

    def __prov__(self):

        commit_graph = self.instance(commit.id, True)
        pass


class Revision(object):

    def __init__(self, repository, commit):
        author = Signature(
            commit.author.name, commit.author.email, _git_timestamp(
                commit.author.time, commit.author.offset
            ), commit.author.offset
        )
        committer = Signature(
            commit.committer.name, commit.committer.email, _git_timestamp(
                commit.committer.time, commit.committer.offset
            ), commit.committer.offset
        )

        self.id = commit.hex
        self.short_id = self.id[:10]
        self.author = author
        self.author_date = author.datetime
        self.committer = committer
        self.committer_date = committer.datetime

        self._repository = repository
        self._commit = commit
        self._parents = None
        self._parsed_message = None

    @benchmark
    def _extract(self, message):
        captures = {}

        matches = re.finditer(PROPERTY_REGEX, message, re.DOTALL | re.MULTILINE)

        if matches:
            for _, match in enumerate(matches):
                if match.group('key') and match.group('value'):
                    key, value = match.group('key'), match.group('value')

                if match.group('key') and match.group('quoted'):
                    key, value = match.group('key'), match.group('quoted')
                    value = value[1 : len(value)-1] #remove quotes

                captures[key] = value
            message = re.sub(PROPERTY_REGEX, "", message, 0, re.DOTALL | re.MULTILINE).strip(" \n")
        return captures, message

    @property
    def properties(self):
        if not self._parsed_message:
            self._parsed_message = self._extract(self._commit.message)
        return self._parsed_message[0]

    @property
    def message(self):
        if not self._parsed_message:
            self._parsed_message = self._extract(self._commit.message)
        return self._parsed_message[1]

    @property
    def parents(self):
        if self._parents is None:
            self._parents = [Revision(self._repository, id) for id in self._commit.parents]
        return self._parents

    def node(self, path=None):
        return Node(self._repository, self._commit, path)

    def graph(store):
        mapping = dict()

        for entry in self.node().entries(recursive=True):
            if not entry.is_file:
                continue

            for (public_uri, g) in entry.graph(store):
                if public_uri is None:
                    continue

                mapping[public_uri] = g

        return InstanceGraph(mapping)

    def __prov__(self):

        uri = QUIT['commit-' + self.id]

        g = ConjunctiveGraph(identifier=QUIT.default)

        # default activity
        g.add((uri, is_a, PROV['Activity']))

        # special activity
        if 'import' in self.properties.keys():
            g.add((uri, is_a, QUIT['Import']))
            g.add((uri, QUIT['dataSource'], URIRef(self.properties['import'].strip())))

        # properties
        g.add((uri, PROV['startedAtTime'], Literal(self.author_date, datatype=XSD.dateTime)))
        g.add((uri, PROV['endedAtTime'], Literal(self.committer_date, datatype=XSD.dateTime)))
        g.add((uri, RDFS['comment'], Literal(self.message)))

        # parents
        for parent in self.parents:
            parent_uri = QUIT['commit-' + parent.id]
            g.add((uri, QUIT["preceedingCommit"], parent_uri))

        g.add((role_author, is_a, PROV['Role']))
        g.add((role_committer, is_a, PROV['Role']))

        # author
        (author_uri, author_graph) = self.author.__prov__()

        g += author_graph
        g.add((uri, PROV['wasAssociatedWith'], author_uri))

        qualified_author = BNode()
        g.add((uri, PROV['qualifiedAssociation'], qualified_author))
        g.add((qualified_author, is_a, PROV['Association']))
        g.add((qualified_author, PROV['agent'], author_uri))
        g.add((qualified_author, PROV['role'], role_author))

        # commiter
        if self.author.name != self.committer.name:
            (committer_uri, committer_graph) = self.committer.__prov__()

            g += committer_graph
            g.add((uri, PROV['wasAssociatedWith'], committer_uri))

            qualified_committer = BNode()
            g.add((uri, PROV['qualifiedAssociation'], qualified_committer))
            g.add((qualified_committer, is_a, PROV['Association']))
            g.add((qualified_committer, PROV['agent'], author_uri))
            g.add((qualified_committer, PROV['role'], role_committer))
        else:
            g.add((qualified_author, PROV['role'], role_committer))

        # diff
        diff = graphdiff(parent_graph, commit_graph)
        for ((resource_uri, hex), changesets) in diff.items():
            for (op, update_graph) in changesets:
                update_uri = QUIT['update-' + hex]
                op_uri = QUIT[op + '-' + hex]
                g.add((uri, QUIT['updates'], update_uri))
                g.add((update_uri, QUIT['graph'], resource_uri))
                g.add((update_uri, QUIT[op], op_uri))
                g.addN((s, p, o, op_uri) for s, p, o in update_graph)

        # entities
        for entity in self.node().entries(recursive=True):
            for (entity_uri, entity_graph) in self.committer.__prov__():
                g += entity_graph
                g.add((entity_uri, PROV['wasGeneratedBy'], uri))

        return (uri, g)


class Signature(object):

    def __init__(self, name, email, datetime, offset):
        self.name = name
        self.email = email
        self.offset = offset
        self.datetime = datetime

    def __str__(self):
        return '{name} <{email}> {date}{offset}'.format(**self.__dict__)

    def __repr__(self):
        return '<{0}> {1}'.format(self.__class__.__name__, self.name).encode('UTF-8')

    def __prov__(self):

        hash = pygit2.hash(self.email).hex
        uri = QUIT['user-' + hash]

        g = ConjunctiveGraph(identifier=QUIT.default)

        g.add((uri, is_a, PROV['Agent']))
        g.add((uri, RDFS.label, Literal(self.name)))
        g.add((uri, FOAF.mbox, Literal(self.email)))

        return (uri, g)


class Node(object):

    DIRECTORY = "dir"
    FILE = "file"

    def __init__(self, repository, commit, path=None):

        if path in (None, '', '.'):
            self.obj = commit.tree
            self.name = ''
            self.kind = Node.DIRECTORY
            self.tree = self.obj
        else:
            try:
                entry = commit.tree[path]
            except KeyError:
                raise NodeNotFound(path, commit.hex)
            self.obj = repository._repository.get(entry.oid)
            self.name = clean_path(path)
            if self.obj.type == pygit2.GIT_OBJ_TREE:
                self.kind = Node.DIRECTORY
                self.tree = self.obj
            elif self.obj.type == pygit2.GIT_OBJ_BLOB:
                self.kind = Node.FILE
                self.blob = self.obj

        self._repository = repository
        self._commit = commit

    @property
    def hex(self) :
        return self.obj.hex

    @property
    def is_dir(self) :
        return self.kind == Node.DIRECTORY

    @property
    def is_file(self):
        return self.kind == Node.FILE

    @property
    def dirname(self):
        return os.path.dirname(self.name)

    @property
    def basename(self):
        return os.path.basename(self.name)

    @property
    def content(self):
        if not self.is_file:
            return None
        return self.blob.data.decode("utf-8")

    def entries(self, recursive=False):
        if isinstance(self.obj, pygit2.Tree):
            for entry in self.obj:
                dirname = self.is_dir and self.name or self.dirname
                node = Node(
                    self._repository, self._commit, '/'.join(x for x in [dirname, entry.name] if x)
                )

                yield node
                if recursive and node.is_dir and node.obj is not None:
                    for x in node.entries(recursive=True):
                        yield x

    @property
    def content_length(self):
        if self.is_file:
            return self.blob.size
        return None

    def graph(store):
        if self.is_file:

            tmp = ConjunctiveGraph()
            tmp.parse(data=self.content, format='nquads')

            for context in tmp.context():

                public_uri = QUIT[context]
                private_uri = QUIT[context + '-' + self.blob.hex]

                g = ReadOnlyRewriteGraph(entry.blob.hex, identifier=private_uri)
                g.parse(data=entry.content, format='nquads')

                yield (public_uri, g)

    def __prov__(self):
        if self.is_file:

            tmp = ConjunctiveGraph()
            tmp.parse(data=self.content, format='nquads')

            for context in tmp.context():
                g = ConjunctiveGraph(identifier=QUIT.default)

                public_uri = QUIT[context]
                private_uri = QUIT[context + '-' + self.blob.hex]

                g.add((private_uri, is_a, PROV['Entity']))
                g.add((private_uri, PROV['specializationOf'], public_uri))
                g.addN(
                    (s, p, o, private_uri) for s, p, o, _ in tmp.quads(None, None, None, context)
                )

                yield (private_uri, g)


from heapq import heappush, heappop

class Index(object):
    def __init__(self, repository):
        self.repository = repository
        self.revision = None
        self.stash = {}
        self.dirty = False

    def set_revision(self, revision):
        try:
            self.revision = self.repository.revision(revision)
        except RevisionNotFound as e:
            raise IndexError(e)

    def add(self, path, contents, mode=None):
        path = clean_path(path)

        oid = self.repository._repository.create_blob(contents)

        self.stash[path] = (oid, mode or pygit2.GIT_FILEMODE_BLOB)

    def remove(self, path):
        path = clean_path(path)

        self.stash[path] = (None, None)

    def commit(self, message, author_name, author_email, **kwargs):
        if self.dirty:
            raise IndexError('Index already commited')

        ref = kwargs.pop('ref', 'HEAD')
        commiter_name = kwargs.pop('commiter_name', author_name)
        commiter_email = kwargs.pop('commiter_email', author_email)
        parents = kwargs.pop('parents', [self.revision.id] if self.revision else [])

        author = pygit2.Signature(author_name, author_email)
        commiter = pygit2.Signature(commiter_name, commiter_email)

        # Sort index items
        items = sorted(self.stash.items(), key=lambda x: (x[1][0], x[0]))

        # Create tree
        tree = IndexTree(self)
        while len(items) > 0:
            path, (oid, mode) = items.pop(0)

            if oid is None:
                tree.remove(path)
            else:
                tree.add(path, oid, mode)

        oid = tree.write()
        self.dirty = True

        try:
            return self.repository._repository.create_commit(
                ref, author, commiter, message, oid, parents
            )
        except Exception as e:
            logger.exception(e)
            return None


class IndexHeap(object):
    def __init__(self):
        self._dict = {}
        self._heap = []

    def __len__(self):
        return len(self._dict)

    def get(self, path):
        return self._dict.get(path)

    def __setitem__(self, path, value):
        if path not in self._dict:
            n = -path.count(os.sep) if path else 1
            heappush(self._heap, (n, path))

        self._dict[path] = value

    def popitem(self):
        key = heappop(self._heap)
        path = key[1]
        return path, self._dict.pop(path)


class IndexTree(object):
    def __init__(self, index):
        self.repository = index.repository
        self.revision = index.revision
        self.builders = IndexHeap()
        if self.revision:
            self.builders[''] = (
                None, self.repository._repository.TreeBuilder(self.revision._commit.tree)
            )
        else:
            self.builders[''] = (None, self.repository._repository.TreeBuilder())

    def get_builder(self, path):
        parts = path.split(os.path.sep)

        # Create builders if needed
        for i in range(len(parts)):
            _path = os.path.join(*parts[0:i + 1])

            if self.builders.get(_path):
                continue

            args = []
            try:
                if self.revision:
                    node = self.revision.node(_path)
                    if node.is_file:
                        raise IndexError(
                            'Cannot create a tree builder. "{}" is a file'.format(node.name)
                        )
                    args.append(node.obj.oid)
            except NodeNotFound:
                pass

            self.builders[_path] = (os.path.dirname(
                _path), self.repository._repository.TreeBuilder(*args))

        return self.builders.get(path)[1]

    def add(self, path, oid, mode):
        builder = self.get_builder(os.path.dirname(path))
        builder.insert(os.path.basename(path), oid, mode)

    def remove(self, path):
        self.revision.node(path)
        builder = self.get_builder(os.path.dirname(path))
        builder.remove(os.path.basename(path))

    def write(self):
        """
        Attach and writes all builders and return main builder oid
        """
        # Create trees
        while len(self.builders) > 0:
            path, (parent, builder) = self.builders.popitem()
            if parent is not None:
                oid = builder.write()
                builder.clear()
                self.builders.get(parent)[1].insert(
                    os.path.basename(path), oid, pygit2.GIT_FILEMODE_TREE)

        oid = builder.write()
        builder.clear()

        return oid
