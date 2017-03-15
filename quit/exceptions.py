#!/usr/bin/env python3

class Error(Exception):
    pass

class InvalidConfigurationError(Error):
    pass

class MissingConfigurationError(Error):
    pass

class MissingFileError(Error):
    pass
