#!/usr/bin/env python3

import unittest
from context import quit
import quit.namespace
from os import path, environ
from pygit2 import init_repository, Repository, clone_repository
from pygit2 import GIT_SORT_TOPOLOGICAL, GIT_SORT_REVERSE, Signature
from tempfile import TemporaryDirectory, NamedTemporaryFile


class VocabularyTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass


def main():
    unittest.main()


if __name__ == '__main__':
    main()
