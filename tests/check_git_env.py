import unittest
from helpers import TemporaryRepository, TemporaryRepositoryFactory

class CheckPyGitEnv(unittest.TestCase):
    with TemporaryRepository() as repository:
        print(type(repository))
        signature = repository.default_signature
        print(signature)
        print(signature.name)
        print(signature.email)
        print(signature.raw_name)
        print(signature.raw_email)
