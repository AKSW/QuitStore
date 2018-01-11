#!/usr/bin/env python3

import unittest
from context import quit
from quit.cache import Cache, FileReference
from os import path, environ
from pygit2 import init_repository, Repository, clone_repository
from pygit2 import GIT_SORT_TOPOLOGICAL, GIT_SORT_REVERSE, Signature
from tempfile import TemporaryDirectory, NamedTemporaryFile


class CacheTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testCacheCapacity(self):
        cache = Cache(capacity=1)
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        with self.assertRaises(KeyError):
            cache.get("key1")

        self.assertEqual(cache.get("key2"), "value2")
        self.assertEqual(cache.size, 1)

    def testRemoveEntry(self):
        cache = Cache()
        cache.set("key", "value")
        self.assertEqual(cache.size, 1)
        cache.remove("key")
        self.assertEqual(cache.size, 0)

    def testSetEntry(self):
        cache = Cache()
        cache.set("key", "value")
        self.assertEqual(cache.get("key"), "value")
        self.assertEqual(cache.size, 1)

    def testOverwriteEntry(self):
        cache = Cache()
        cache.set("key", "value")
        cache.set("key", "value2")
        self.assertEqual(cache.get("key"), "value2")
        self.assertEqual(cache.size, 1)


class FileReferenceTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass


def main():
    unittest.main()


if __name__ == '__main__':
    main()
