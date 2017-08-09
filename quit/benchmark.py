import time

def benchmark(f):

    def timed(*args, **kw):

        print("starting '%r'" % (f.__name__))

        ts = time.time()
        result = f(*args, **kw)
        te = time.time()

        print("ending '%r' after %2.4f sec" % (f.__name__, te-ts))
        return result

    return timed


