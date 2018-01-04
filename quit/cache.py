import logging
from collections import OrderedDict
from sortedcontainers import SortedList

logger = logging.getLogger('quit.cache')


class Cache:

    logger = logging.getLogger('quit.cache.Cache')

    def __init__(self, capacity=50):
        self.stack = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        """Get a value from the cache.

        Raises:
            KeyError if no value was found for the given key
        """
        value = self.stack.pop(key)
        self.stack[key] = value
        self.logger.debug('Found {} {}'.format(key, value))
        return value

    def set(self, key, value):
        try:
            self.stack.pop(key)
            logger.debug('Removed existent key {}'.format(key))
        except KeyError:
            if len(self.stack) >= self.capacity:
                self.logger.debug('Cache reached it\'s capacity. pop current item.')
                self.stack.popitem(last=False)
        self.stack[key] = value
        self.logger.debug('Set {} {}'.format(key, value))

    def remove(self, key):
        try:
            self.logger.debug('Remove {} with value {}'.format(key,  self.get(key)))
            return self.stack.pop(key)
        except KeyError:
            self.logger.debug('Nothing to remove {}'.format(key))
            return

    def __contains__(self, key):
        return key in self.stack

    def __iter__(self):
        return (c for c in self.stack)

    @property
    def size(self):
        """
        Return the size of the cache
        """
        return len(self.stack)


class FileReference:
    """A class that manages n-quad files.
    This class stores inforamtation about the location of a n-quad file and is
    able to add and delete triples/quads to that file.
    """

    logger = logging.getLogger('quit.cache.FileReference')

    def __init__(self, path, content):
        """Initialize a new FileReference instance.
        Args:
            filelocation: A string of the filepath.
            filecontentinmem: Boolean to decide if local filesystem should be used to
                or if file content should be kept in memory too . (Defaults false)
        Raises:
            ValueError: If no file at the filelocation, or in the given directory + filelocation.
        """

        self.logger.debug('Initialize FileReference for {} with {}'.format(path, content))
        if isinstance(content, str):
            content = content.splitlines() or []

        self._path = path
        self._content = SortedList(content)
        self._modified = False

    @property
    def path(self):
        return self._path

    @property
    def content(self):
        return "\n".join(self._content)

    def add(self, data):
        """Add a quad to the file content."""
        self.logger.debug('Add content {}'.format(data))
        self._content.add(data)

    def extend(self, data):
        """Add quads to the file content."""
        self.logger.debug('Extend content {}'.format(data))
        self._content.extend(data)

    def remove(self, data):
        """Remove quad from the file content."""
        logger.debug('Remove content {}'.format(data))
        self._content.remove(data)
