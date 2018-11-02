import os
import pygit2
import re
import logging

from _pygit2 import GitError, Oid
from os.path import expanduser, join
from quit.exceptions import RepositoryNotFound, RevisionNotFound, NodeNotFound, RemoteNotFound
from quit.exceptions import QuitMergeConflict, QuitGitRefNotFound, QuitGitRepoError
from quit.namespace import QUIT

import subprocess

PROPERTY_REGEX = r"^("
PROPERTY_REGEX += r"(?P<key>([\w0-9_]+))\s*:"
PROPERTY_REGEX += r"\s*((?P<value>([\w0-9_]+))|(?P<quoted>(\".*\"|'[^']*')))"
PROPERTY_REGEX += r")"

logger = logging.getLogger('quit.git')

# roles
role_author = QUIT['author']
role_committer = QUIT['committer']


class Repository(object):
    """The Quit class for wrapping a git repository.

    TODO:
    - There is no possibility to set remotes on a Quit Repository object.
    """

    def __init__(self, path, origin=None, create=False, garbageCollection=False, callback=None):
        """Initialize a quit repo at a given location of the filesystem.

        Keyword arguments:
        path -- the location of an existing git repository or where the repository should be created
        origin -- if the repository does not exist and origin is given the origin repository is
                  cloned to the given path (default: None)
        create -- boolean whether to create a new repository if the specified path is empty
                  (default: False)
        garbageCollection -- boolean whether to activate the garbage collection on the git
                  repository (default: False)
        callback -- an instance of pygit2.RemoteCallbacks to handle cedentials and
                  push_update_reference (default: None)
        """
        if not callback:
            callback = QuitRemoteCallbacks()
        self.callback = callback

        try:
            self._repository = pygit2.Repository(path)
        except (KeyError, GitError):
            if not create:
                raise RepositoryNotFound(
                    'Repository "%s" does not exist' % path)

            if origin:
                self._repository = pygit2.clone_repository(
                    url=origin, path=path, bare=False, callbacks=self.callback
                )
            else:
                self._repository = pygit2.init_repository(path)

        if garbageCollection:
            self.init_garbageCollection(path)

        self.path = path

    def init_garbageCollection(self, path):
        """Set the threshold for automatic garbage collection for the git repository."""
        try:
            with subprocess.Popen(
                ["git", "config", "gc.auto"],
                stdout=subprocess.PIPE,
                cwd=path
            ) as gcAutoThresholdProcess:
                stdout, stderr = gcAutoThresholdProcess.communicate()
                gcAutoThreshold = stdout.decode("UTF-8").strip()

            if not gcAutoThreshold:
                gcAutoThreshold = 256
                subprocess.Popen(["git", "config", "gc.auto", str(gcAutoThreshold)], cwd=path)
                logger.info("Set default gc.auto threshold {}".format(gcAutoThreshold))

            logger.info(
                "Garbage Collection is enabled with gc.auto threshold {}".format(gcAutoThreshold)
            )
        except Exception as e:
            # Disable garbage collection for the rest of the run because it
            # is likely that git is not available
            logger.info('Git garbage collection could not be configured and was disabled')
            logger.debug(e)

    @property
    def is_empty(self):
        return self._repository.is_empty

    @property
    def is_bare(self):
        return self._repository.is_bare

    def close(self):
        self._repository = None

    def lookup(self, name):
        """Lookup the oid for a reference.

        The name is looked for in "refs/heads/<name>", "refs/tags/<name>" and directly.
        It does not matter weather the found reference is a symbolic or a direct, it will be
        resolved to an oid.

        Return:
        Oid
        """
        for template in ['refs/heads/%s', 'refs/tags/%s', '%s']:
            try:
                reference = self._repository.lookup_reference(template % name)
                return reference.resolve().target
            except KeyError:
                pass
        raise RevisionNotFound(name)

    def revision(self, id='HEAD'):
        try:
            commit = self._repository.revparse_single(id)
        except KeyError:
            raise RevisionNotFound(id)

        return Revision(self, commit)

    def revisions(self, name=None, order=pygit2.GIT_SORT_REVERSE):
        seen = set()

        def traverse(ref, seen):
            for commit in self._repository.walk(ref, order):
                oid = commit.oid
                if oid not in seen:
                    seen.add(oid)
                    yield Revision(self, commit)

        def iter_commits(name, seen):
            commits = []

            if not name:
                for name in self.branches:
                    ref = self.lookup(name)
                    commits += traverse(ref, seen)
            else:
                oid = self.lookup(name)
                commits += traverse(oid, seen)
            return commits

        return iter_commits(name, seen)

    @property
    def current_head(self):
        if not self._repository.head_is_unborn:
            return re.sub("refs/heads/", "", self._repository.head.name)
        return None

    @property
    def branches(self):
        return [x for x in self._repository.listall_references() if x.startswith('refs/heads/')]

    @property
    def tags(self):
        return [x for x in self._repository.listall_references() if x.startswith('refs/tags/')]

    @property
    def references(self):
        return self._repository.listall_references()

    @property
    def remotes(self):
        return [{"name": x.name, "url": x.url} for x in self._repository.remotes]

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

    def getUpstreamOfHead(self):
        if self._repository.head_is_unborn:
            return (None, None, None)
        localBranchName = re.sub("^refs/heads/", "", self._repository.head.name)
        localBranch = self._repository.lookup_branch(localBranchName)
        if localBranch.upstream is not None:
            refspecPattern = re.compile("^refs/remotes/([^/]*)/(.*)$")
            remote_name = localBranch.upstream.remote_name
            remote_ref = localBranch.upstream.name
            if remote_ref.startswith("refs/remotes/"):
                matchgroups = refspecPattern.match(remote_ref)
                remote_branch = matchgroups.group(2)
            else:
                remote_branch = remote_ref
            return (remote_name, remote_branch, remote_ref)
        return (None, None, None)

    def fetch(self, remote_name=None, remote_branch=None):
        """Fetch changes from a remote.

        If no remote_name and no remote_branch is given, the method will fetch changes from the
        remote called origin or if the current branch referenced by HEAD has upstream configured, it
        will fetch the configured upstream branch.

        Keyword arguments:
        remote_name --The name of the remote from where to fetch.
        remote_branch -- The name of the remote branch to fetch or a local reference to a remote
                         branch (refs/remotes/.../...)
        """
        remote_ref = None
        if (remote_name is None and
                remote_branch is not None and
                remote_branch.startswith("refs/remotes/")):
            refspecPattern = re.compile("^refs/remotes/([^/]*)/(.*)$")
            remote_ref = remote_branch
            matchgroups = refspecPattern.match(remote_branch)
            remote_name = matchgroups.group(1)
            remote_branch = matchgroups.group(2)
        if remote_branch is None and not self._repository.head_is_unborn:
            (head_remote_name, head_remote_branch, head_remote_ref) = self.getUpstreamOfHead()
            if remote_name is None or remote_name == head_remote_name:
                remote_name = head_remote_name
                remote_branch = head_remote_branch
                remote_ref = head_remote_ref
        if remote_name is None:
            remote_name = 'origin'
        else:
            remote_ref = 'refs/remotes/{remote}/{remote_branch}'.format(remote=remote_name,
                                                                        remote_branch=remote_branch)
        logger.debug('Fetching: {} from {} ({})'.format(remote_branch or "all references",
                                                        remote_name, remote_ref))
        for remote in self._repository.remotes:
            if remote.name == remote_name:
                if remote_branch is not None:
                    remote_branch = [remote_branch]
                remote.fetch(remote_branch, callbacks=self.callback)

                if remote_branch is None:
                    return None

                return self._repository.lookup_reference(remote_ref).target
        raise RemoteNotFound("There is no remote \"{}\".".format(remote_name))

    def pull(self, remote_name=None, refspec=None):
        """Pull (fetch and merge) changes from a remote repository.

        Keyword arguments:
        remote_name -- The name of a remote repository as configured on the underlaying git
                       repository (default: "origin")
        refspec -- The refspec of remote branch to fetch and the local reference/branch to update.
                   An optional plus (+) in the beginning of the refspec is ignored.
        """
        remote_branch = None
        local_branch = None
        if refspec is not None:
            rerefspec = re.compile("^(?P<plus>[+]?)(?P<src>[^:]*)(:(?P<dst>.*))?$")
            groups = rerefspec.match(refspec)
            if groups is None:
                raise QuitGitRepoError("The respec \"{}\" could not be understood".format(refspec))
            plus = groups.group("plus")
            remote_branch = groups.group("src")
            local_branch = groups.group("dst")
            logger.debug("pull: parsed refspec is: {}, {}, {}".format(plus, remote_branch,
                                                                      local_branch))
        remote_reference = self.fetch(remote_name=remote_name, remote_branch=remote_branch)
        if remote_reference is not None:
            self.merge(reference=local_branch, branch=remote_reference)

    def push(self, remote_name=None, refspec=None):
        """Push changes on a local repository to a remote repository.

        Keyword arguments:
        remote_name -- The name of a remote repository as configured on the underlaying git
                       repository (default: "origin")
        refspec -- The local and remote reference to push divided with a colon.
                   (refs/heads/master:refs/heads/master)
        """

        if refspec is None:
            (head_remote_name, head_remote_branch, head_remote_ref) = self.getUpstreamOfHead()
            if head_remote_ref is None:
                raise QuitGitRefNotFound("There is no upstream configured for the current branch")
            refspec = '{src}:{dst}'.format(self._repository.head.name, head_remote_ref)
            remote_name = head_remote_name

        if remote_name is None:
            remote_name = 'origin'

        try:
            left, right = refspec.split(':')
        except Exception:
            left = refspec
            right = None

        refspec = ""
        if left:
            if not left.startswith("refs/heads/"):
                refspec = "refs/heads/" + left
            else:
                refspec = left
        if right:
            if not right.startswith('refs/heads/'):
                refspec += ':refs/heads/' + right
            else:
                refspec += ':' + right

        logger.debug("push: refspec {} to {}".format(refspec, remote_name))

        for remote in self._repository.remotes:
            if remote.name == remote_name:
                remote.push([refspec], callbacks=self.callback)
                if self.callback.push_error is not None:
                    raise self.callback.push_error
                return
        raise RemoteNotFound("There is no remote \"{}\".".format(remote_name))

    def merge(self, reference=None, target=None, branch=None):
        """Merge two commits and set the reference to the result.

        merge 'branch' into 'target' and set 'reference' to the resulting commit
        - if only 'reference' is given, do nothing
        - if 'reference' and 'branch' are given, merge 'branch' into 'reference' and set 'reference'
          to the resulting commit
        - if 'reference', 'branch' and 'target' are given, merge 'branch' into 'target' and set
          'reference' to the resulting commit

        Keyword arguments:
        reference -- The reference which should point to the result of the merge
        target -- The target of the merge operation (if omitted, 'branch' will be merged into
                  'reference')
        branch -- The branche which should be merged into 'target' respective 'reference'
        """

        if reference is None:
            reference = "master"
        if target is None:
            target = "HEAD"
        if branch is None:
            branch = "FETCH_HEAD"

        logger.debug("merge: {}, {}, {}".format(reference, target, branch))

        if not isinstance(branch, Oid):
            branch_id = self._repository.lookup_reference(branch).target
        else:
            branch_id = branch
        merge_result, _ = self._repository.merge_analysis(branch_id)

        if reference != "master":
            raise Exception("We first have to implement switching branches")

        if target != "HEAD":
            raise Exception("We currently are only able to merge into the HEAD of a branch")

        # Up to date, do nothing
        if merge_result & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE:
            return

        # We can just fastforward
        elif merge_result & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD:
            self._repository.checkout_tree(self._repository.get(branch))
            try:
                master_ref = self._repository.lookup_reference(
                    'refs/heads/{}'.format(reference))
                master_ref.set_target(branch)
            except KeyError:
                self._repository.create_branch(
                    reference, self._repository.get(branch))
            self._repository.head.set_target(branch)
            return

        elif merge_result & pygit2.GIT_MERGE_ANALYSIS_NORMAL:
            self._repository.merge(branch)

            if self._repository.index.conflicts is not None:
                for conflict in self._repository.index.conflicts:
                    logger.error('Conflicts found in: {}'.format(conflict[0].path))
                raise QuitMergeConflict('Conflicts, ahhhhh!!')

            user = self._repository.default_signature
            tree = self._repository.index.write_tree()
            self._repository.create_commit(
                'HEAD', user, user, 'Merge!', tree,
                [self._repository.head.target, branch]
            )
            # We need to do this or git CLI will think we are still merging.
            self._repository.state_cleanup()
            return
        else:
            raise AssertionError('Unknown merge analysis result')
        raise Exception('Please have a look at https://github.com/libgit2/pygit2/issues/725')

    def revert(self, reference='', target='', branch=''):
        """Revert a commit."""
        raise Exception('Not yet supported')


class Revision(object):

    def __init__(self, repository, commit):
        self.id = commit.hex
        self.short_id = self.id[:10]
        self.author = commit.author
        self.committer = commit.committer

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

    def __init__(self, session=None):
        self.session = session

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
            if self.session and "OAUTH_TOKEN" in self.session:
                return pygit2.UserPass(self.session["OAUTH_TOKEN"], 'x-oauth-basic')
            elif "GIT_USERNAME" in os.environ and "GIT_PASSWORD" in os.environ:
                return pygit2.UserPass(os.environ["GIT_USERNAME"], os.environ["GIT_PASSWORD"])
            else:
                raise Exception(
                    "Remote requested plaintext username and password authentication but " +
                    "GIT_USERNAME or GIT_PASSWORD are not set."
                )
        else:
            raise Exception("Only unsupported credential types allowed by remote end")

    def push_update_reference(self, refname, message):
        """This callback is called for a push operation.

        In the case, that the remote rejects a push, message will be set.
        Because we can't raise an Exception here, we have to write it to self.push_error, thus it is
        important to check on the callback object if push_error is not None after a push.
        """
        self.push_error = None
        if message:
            self.push_error = QuitGitPushError(
                "The reference \"{}\" could not be pushed. Remote told us: {}".format(
                    refname.decode("utf-8"), message))
            return -1
        pass
