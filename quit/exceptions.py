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

class UnSupportedQueryType(Exception):
    """
    Thrown when providing an unsupported query type
    """
    def __init__(self):
        pass

    def __str__(self):
        return ("This query is not allowed by this endpoint")


class UnknownConfigurationError(Error):
    pass


class QuitGitRepoError(Error):
    pass
