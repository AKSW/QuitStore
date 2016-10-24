#!/usr/bin/env python3

from context import GitRepo
from os import unlink
from pygit2 import init_repository, Repository
from tempfile import TemporaryDirectory, NamedTemporaryFile

dir = TemporaryDirectory()
init_repository(dir.name)
repo = GitRepo(dir.name)
file = NamedTemporaryFile(dir=dir.name)
file.write(b'Test\n')
testrepo = Repository(dir.name)
testrepo = None
repo.addfile(file.name)
testrepo = Repository(dir.name)
index = testrepo.index
index.read()

repo = GitRepo(dir.name)

testrepo = Repository(dir.name)
# print('Commitloglänge', len(testrepo.walk(testrepo.head.target)), 0)
testrepo = None

# Commit 1
repo.commit()
testrepo = Repository(dir.name)
all_refs = testrepo.listall_references()
print('Refs', all_refs)
commits = testrepo.walk(testrepo.head.target)
print('Commitloglänge', len(list(testrepo.walk(testrepo.head.target))), 1)
testrepo = None

# Commit 2
testrepo = Repository(dir.name)
# print('Commitloglänge', len(testrepo.walk(testrepo.head.target)), 0)
testrepo = None

file.write(b'Test2\n')
file.write(b'Test3\n')
f = open(file.name, 'w')
f.write('Test2')
f.write('Test3')
f.close
print('Refs', all_refs)
print('Should not be clear', repo.isstagingareaclean())
file.read()
repo.update()
print('Refs', all_refs)
print('Should be Clear', repo.isstagingareaclean())
repo.commit()
testrepo = Repository(dir.name)
all_refs = testrepo.listall_references()
print('Clear', repo.isstagingareaclean())
commits = testrepo.walk(testrepo.head.target)
testrepo = None
# self.assertEqual(len(testrepo.walk(testrepo.head.target)), 1)
