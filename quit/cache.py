import collections

class Cache:
    """"""
 
    def __init__(self, capacity = 50):
        """
		Constructor
		"""
        self.cache = collections.OrderedDict()
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


    def __contains__(self, key):
        return key in self.cache


    @property
    def size(self):
        """
        Return the size of the cache
        """
        return len(self.cache)


