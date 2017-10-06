import os
import pygit2
import re
import logging

from datetime import datetime
from os.path import expanduser, join
from quit.exceptions import RepositoryNotFound, RevisionNotFound, NodeNotFound
from rdflib import Literal, ConjunctiveGraph
from quit.namespace import FOAF, RDFS, PROV, QUIT, is_a
from quit.cache import Cache
import pygit2

PROPERTY_REGEX = r"^("
PROPERTY_REGEX += r"(?P<key>([\w0-9_]+))\s*:"
PROPERTY_REGEX += r"\s*((?P<value>([\w0-9_]+))|(?P<quoted>(\".*\"|'[^']*')))"
PROPERTY_REGEX += r")"

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
                raise RepositoryNotFound(
                    'Repository "%s" does not exist' % path)

            if origin:
                self.callback = QuitRemoteCallbacks()
                self._repository = pygit2.clone_repository(
                    url=origin, path=path, bare=False, callbacks=self.callback
                )
            else:
                self._repository = pygit2.init_repository(path)

        self.path = path
        self.params = params

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
            raise RevisionNotFound(name)

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
        logger.debug('Pulling branch: {} from {}'.format(branch, remote_name))
        for remote in self._repository.remotes:
            if remote.name == remote_name:
                remote.fetch()
                remote_master_id = self._repository.lookup_reference(
                    'refs/remotes/origin/{}'.format(branch)
                ).target
                merge_result, _ = self._repository.merge_analysis(
                    remote_master_id)

                # Up to date, do nothing
                if merge_result & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE:
                    return

                # We can just fastforward
                elif merge_result & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD:
                    self._repository.checkout_tree(
                        self._repository.get(remote_master_id))
                    try:
                        master_ref = self._repository.lookup_reference(
                            'refs/heads/%s' % (branch))
                        master_ref.set_target(remote_master_id)
                    except KeyError:
                        self._repository.create_branch(
                            branch, self._repository.get(remote_master_id))
                    self._repository.head.set_target(remote_master_id)

                elif merge_result & pygit2.GIT_MERGE_ANALYSIS_NORMAL:
                    self._repository.merge(remote_master_id)

                    if self._repository.index.conflicts is not None:
                        for conflict in self._repository.index.conflicts:
                            logger.error(
                                'Conflicts found in: {}'.format(conflict[0].path))
                        raise AssertionError('Conflicts, ahhhhh!!')

                    user = self._repository.default_signature
                    tree = self._repository.index.write_tree()
                    self._repository.create_commit(
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

    def _extract(self, message):
        captures = {}

        matches = re.finditer(PROPERTY_REGEX, message,
                              re.DOTALL | re.MULTILINE)

        if matches:
            for _, match in enumerate(matches):
                if match.group('key') and match.group('value'):
                    key, value = match.group('key'), match.group('value')

                if match.group('key') and match.group('quoted'):
                    key, value = match.group('key'), match.group('quoted')
                    value = value[1: len(value) - 1]  # remove quotes

                captures[key] = value
            message = re.sub(PROPERTY_REGEX, "", message, 0,
                             re.DOTALL | re.MULTILINE).strip(" \n")
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
            self._parents = [Revision(self._repository, id)
                             for id in self._commit.parents]
        return self._parents

    def node(self, path=None):
        return Node(self._repository, self._commit, path)


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
            self.name = os.path.normpath(path)
            if self.obj.type == pygit2.GIT_OBJ_TREE:
                self.kind = Node.DIRECTORY
                self.tree = self.obj
            elif self.obj.type == pygit2.GIT_OBJ_BLOB:
                self.kind = Node.FILE
                self.blob = self.obj

        self._repository = repository
        self._commit = commit

    @property
    def oid(self):
        return self.obj.id

    @property
    def is_dir(self):
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
                    self._repository, self._commit, '/'.join(
                        x for x in [dirname, entry.name] if x)
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

    def history(self):
        walker = self._repository._repository.walk(self._commit.oid, pygit2.GIT_SORT_TIME)

        c0 = self._commit
        e0 = c0.tree[self.name]

        for c1 in walker:
            try:
                e1 = c1.tree[self.name]
                if e0 and e0.oid != e1.oid:
                    yield Node(self._repository, c1, self.name)
            except KeyError:
                return

            c0 = c1
            e0 = e1


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
        path = os.path.normpath(path)

        oid = self.repository._repository.create_blob(contents)

        self.stash[path] = (oid, mode or pygit2.GIT_FILEMODE_BLOB)

    def remove(self, path):
        path = os.path.normpath(path)

        self.stash[path] = (None, None)

    def commit(self, message, author_name, author_email, **kwargs):
        if self.dirty:
            raise IndexError('Index already commited')

        ref = kwargs.pop('ref', 'HEAD')
        commiter_name = kwargs.pop('commiter_name', author_name)
        commiter_email = kwargs.pop('commiter_email', author_email)
        parents = kwargs.pop(
            'parents', [self.revision.id] if self.revision else [])

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

        return self.repository._repository.create_commit(
            ref, author, commiter, message, oid, parents
        )


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
                None, self.repository._repository.TreeBuilder(
                    self.revision._commit.tree)
            )
        else:
            self.builders[''] = (
                None, self.repository._repository.TreeBuilder())

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
                            'Cannot create a tree builder. "{}" is a file'.format(
                                node.name)
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
        """Attach and writes all builders and return main builder oid."""
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


class QuitRemoteCallbacks (pygit2.RemoteCallbacks):
    """Set a pygit callback for user authentication when acting with remotes."""

    def credentials(self, url, username_from_url, allowed_types):
        """
        The callback to return a suitable authentication method.
        it supports GIT_CREDTYPE_SSH_KEY and GIT_CREDTYPE_USERPASS_PLAINTEXT
        GIT_CREDTYPE_SSH_KEY with an ssh agent configured in the env variable SSH_AUTH_SOCK
          or with id_rsa and id_rsa.pub in ~/.ssh (password must be the empty string)
        GIT_CREDTYPE_USERPASS_PLAINTEXT from the env variables GIT_USERNAME and GIT_PASSWORD
        """
        if pygit2.credentials.GIT_CREDTYPE_SSH_KEY & allowed_types:
            if "SSH_AUTH_SOCK" in os.environ:
                # Use ssh agent for authentication
                return pygit2.KeypairFromAgent(username_from_url)
            else:
                ssh = join(expanduser('~'), '.ssh')
                if "QUIT_SSH_KEY_HOME" in os.environ:
                    ssh = os.environ["QUIT_SSH_KEY_HOME"]
                # public key is still needed because:
                # _pygit2.GitError: Failed to authenticate SSH session:
                # Unable to extract public key from private key file:
                # Method unimplemented in libgcrypt backend
                pubkey = join(ssh, 'id_rsa.pub')
                privkey = join(ssh, 'id_rsa')
                # check if ssh key is available in the directory
                if os.path.isfile(pubkey) and os.path.isfile(privkey):
                    return pygit2.Keypair(username_from_url, pubkey, privkey, "")
                else:
                    raise Exception(
                        "No SSH keys could be found, please specify SSH_AUTH_SOCK or add keys to " +
                        "your ~/.ssh/"
                    )
        elif pygit2.credentials.GIT_CREDTYPE_USERPASS_PLAINTEXT & allowed_types:
            if "GIT_USERNAME" in os.environ and "GIT_PASSWORD" in os.environ:
                return pygit2.UserPass(os.environ["GIT_USERNAME"], os.environ["GIT_PASSWORD"])
            else:
                raise Exception(
                    "Remote requested plaintext username and password authentication but " +
                    "GIT_USERNAME or GIT_PASSWORD are not set."
                )
        else:
            raise Exception("Only unsupported credential types allowed by remote end")
