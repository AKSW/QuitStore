#!/usr/bin/env python3


class Error(Exception):
    pass


class InvalidConfigurationError(Error):
    pass


class MissingConfigurationError(Error):
    pass


class MissingFileError(Error):
    pass


class RepositoryNotFound(Error):
    """
    Exception raised when a repository is invalid
    """


class ResourceNotFound(Error):
    """
    Thrown when a non-existent resource is requested
    """


class RevisionNotFound(ResourceNotFound):
    """
    Thrown when a non-existent revision is requested
    """

    def __init__(self, id):
        ResourceNotFound.__init__(self, "No commit '%s' in the repository," % id)


class NodeNotFound(ResourceNotFound):
    """
    Thrown when a non-existent node is requested
    """

    def __init__(self, path, id):
        ResourceNotFound.__init__(self, "No node '%s' in commit '%s'," % (path, id))


class IndexError(Error):
    """
    Thrown during indexing
    """
    pass


class ServiceException(Error):
    """
    Thrown when requesting a missing service
    """
    pass


class UnSupportedQuery(Exception):
    """
    Thrown when providing a query which includes an unsupported keyword
    """

    def __init__(self, message=None):
        self.message = message
        pass

    def __str__(self):
        if self.message is not None:
            return ("This query is not supported by this endpoint: {}".format(self.message))
        else:
            return ("This query is not supported by this endpoint")


class UnSupportedQueryType(UnSupportedQuery):
    """
    Thrown when providing an unsupported query type
    """
    pass


class SparqlProtocolError(Error):
    pass


class UnknownConfigurationError(Error):
    pass


class QuitGitRepoError(Error):
    pass


class RemoteNotFound(QuitGitRepoError):
    """Raised when a requested remote is not configured on the repository."""
    pass


class QuitGitRefNotFound(QuitGitRepoError):
    """Raised when a reference could not be found."""
    pass


class QuitGitPushError(QuitGitRepoError):
    """Raised when it is not possible to push to a remote repository."""
    pass


class QuitMergeConflict(QuitGitRepoError):
    """Raised for a merge conflict."""
    pass
