from collections import OrderedDict
from sortedcontainers import SortedList

class Cache:
    """"""

    def __init__(self, capacity=50):
        """
                Constructor
                """
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        try:
            value = self.cache.pop(key)
            self.cache[key] = value
            return value
        except KeyError:
            return None

    def set(self, key, value):
        try:
            self.cache.pop(key)
        except KeyError:
            if len(self.cache) >= self.capacity:
                self.cache.popitem(last=False)
        self.cache[key] = value

    def remove(self, key):
        try:
            return self.cache.pop(key)
        except KeyError:
            return

    def __contains__(self, key):
        return key in self.cache

    def __iter__(self):
        return (c for c in self.cache)

    @property
    def size(self):
        """
        Return the size of the cache
        """
        return len(self.cache)


class FileReference:
    """A class that manages n-quad files.
    This class stores inforamtation about the location of a n-quad file and is
    able to add and delete triples/quads to that file.
    """

    def __init__(self, path, content):
        """Initialize a new FileReference instance.
        Args:
            filelocation: A string of the filepath.
            versioning: Boolean if versioning is enabled or not. (Defaults true)
            filecontentinmem: Boolean to decide if local filesystem should be used to
                or if file content should be kept in memory too . (Defaults false)
        Raises:
            ValueError: If no file at the filelocation, or in the given directory + filelocation.
        """
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
        self._content.add(data)

    def extend(self, data):
        """Add quads to the file content."""
        self._content.extend(data)

    def remove(self, data):
        """Remove quad from the file content."""
        self.content.remove(data)