from ..exceptions import ServiceException

_services = {}


class Service(object):
    """
    A Service object for sparql
    """

    def __init__(self, name, graph):
        self.name = name
        self.graph = graph


def register(name, graph):
    s = Service(name, graph)
    _services[name] = s


def get(name):
    try:
        s = _services[name]
    except KeyError:
        raise ServiceException("No service registered for %s" % name)
    return s.graph
