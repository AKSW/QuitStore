import git
from datetime import datetime


class GitRepo:
    """A class that manages a git repository.

    This class enables versiong via git for a repository.
    You can stage and commit files and checkout different commits of the repository.
    """

    commits = []
    ids = []

    def __init__(self, path):
        """Initialize a new repository.

        Args:
            path: A string containing the path to the repository.

        Raises:
            Exception if path is not a git repository.
        """
        self.path = path

        try:
            self.repo = git.Repo(self.path)
        except:
            raise

        self.git = self.repo.git
        self.__setcommits()

        return

    def __setcommits(self):
        """Save a list of all git commits, commit messages and dates."""
        commits = []
        ids = []
        log = self.repo.iter_commits('master')

        for entry in log:
            # extract timestamp and convert to datetime
            commitdate = datetime.fromtimestamp(float(entry.committed_date)).strftime('%Y-%m-%d %H:%M:%S')
            ids.append(str(entry))
            commits.append({
                'id': str(entry),
                'message': str(entry.message),
                'committeddate': commitdate
            })

        self.commits = commits
        self.ids = ids

        return

    def addfile(self, filename):
        """Add a file that should be tracked.

        Args:
            filename: A string containing the path to the file.
        Raises:
            Exception: If file was not found under 'filename' or if file is part of store.
        """
        gitstatus = self.git.status('--porcelain')

        if gitstatus == '':
            self.modified = False
            return

        try:
            print("Trying to stage file", filename)
            self.git.add([filename])
        except:
            print('Couldn\'t stage file', filename)
            raise

    def getcommits(self):
        """Return meta data about exitsting commits.

        Returns:
            A list containing dictionaries with commit meta data
        """
        return self.commits

    def checkout(self, commitid):
        """Checkout a commit by a commit id.

        Args:
            commitid: A string cotaining a commitid.
        """
        print('Trying to checkout', commitid)
        self.git.checkout(commitid)
        try:
            self.git.checkout(commitid)
        except:
            raise Exception()

        return

    def commitexist(self, commitid):
        """Check if a commit id is part of the repository history.

        Args:
            commitid: String of a Git commit id.
        Returns:
            True, if commitid is part of commit log
            False, else.
        """
        if commitid in self.ids:
            return True
        else:
            return False

    def update(self):
        """Trie to add all updated files.

        Raises:
            Exception: If no tracked file was changed.
        """
        gitstatus = self.git.status('--porcelain')

        if gitstatus == '':
            print('Nothing to add')
            return

        try:
            print("Staging file(s)")
            self.git.add([''], '-u')
        except:
            raise

        return

    def commit(self, message=None):
        """Commit staged files.

        Args:
            message: A string for the commit message.
        Raises:
            Exception: If no files in staging area.
        """
        gitstatus = self.git.status('--porcelain')

        if gitstatus == '':
            print('Nothing to commit')
            return

        if message is None:
            message = '\"New commit from quit-store\"'

        # TODO Add a meta data
        # committer = str.encode('Quit-Store <quit.store@aksw.org>')
        # commitid = self.repo.do_commit(msg, committer)

        try:
            print('Commit updates')
            self.git.commit('-m', message)
            self.__setcommits()
        except git.exc.GitCommandError:
            raise

        return
