from __future__ import with_statement
from flask import Response
import os
import contextlib
import signal
import sys
from datetime import tzinfo, timedelta, datetime
from quit.graphs import InMemoryAggregatedGraph

ZERO = timedelta(0)
HOUR = timedelta(hours=1)


class TZ(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(minutes=offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO


def git_timestamp(ts, offset):
    import quit.utils as tzinfo
    if offset == 0:
        tz = tzinfo.TZ(0, "UTC")
    else:
        hours, rem = divmod(abs(offset), 60)
        tzname = 'UTC%+03d:%02d' % ((hours, -hours)[offset < 0], rem)
        tz = tzinfo.TZ(offset, tzname)
    return datetime.fromtimestamp(ts, tz)


def sparqlresponse(result, format):
    """Create a FLASK HTTP response for sparql-result+json."""
    return Response(
        result.serialize(format=format['format']).decode('utf-8'),
        content_type=format['mime']
    )


def splitinformation(quads, GraphObject):
    """Split quads ."""
    data = []
    graphsInRequest = set()
    for quad in quads:
        graph = quad[3].n3().strip('[]')
        if graph.startswith('_:', 0, 2):
            graphsInRequest.add('default')
            data.append({
                        'graph': 'default',
                        'quad': quad[0].n3() + ' ' + quad[1].n3() + ' ' + quad[2].n3() + ' .\n'
                        })
        else:
            graphsInRequest.add(graph.strip('<>'))
            data.append(
                {
                    'graph': graph.strip('<>'),
                    'quad': quad[0].n3() + ' ' +
                    quad[1].n3() + ' ' +
                    quad[2].n3() + ' ' +
                    graph + ' .\n'
                }
            )
    return {'graphs': graphsInRequest, 'data': data, 'GraphObject': GraphObject}


def graphdiff(first, second):
    """
    Diff between graph instances, should be replaced/included in quit diff
    """
    from rdflib.compare import to_isomorphic, graph_diff

    diffs = []
    iris = set()

    if first is not None and isinstance(first, InMemoryAggregatedGraph):
        first_identifiers = list((g.identifier for g in first.graphs()))
        iris = iris.union(first_identifiers)
    if second is not None and isinstance(second, InMemoryAggregatedGraph):
        second_identifiers = list((g.identifier for g in second.graphs()))
        iris = iris.union(second_identifiers)

    for iri in iris:
        changes = []

        if (
            first is not None and iri in first_identifiers
        ) and (
            second is not None and iri in second_identifiers
        ):
            g1 = first.get_context(iri)
            g2 = second.get_context(iri)
            in_both, in_first, in_second = graph_diff(to_isomorphic(g1), to_isomorphic(g2))

            if len(in_second) > 0:
                changes.append(('additions', ((s, p, o) for s, p, o in in_second)))
            if len(in_first) > 0:
                changes.append(('removals', ((s, p, o) for s, p, o in in_first)))
        elif first is not None and iri in first_identifiers:
            changes.append(('removals', ((s, p, o) for s, p, o in first.get_context(iri))))
        elif second is not None and iri in second_identifiers:
            changes.append(('additions', ((s, p, o) for s, p, o in second.get_context(iri))))
        else:
            continue

        diffs.append({iri: changes})
    return diffs


def _sigterm_handler(signum, frame):
    sys.exit(0)


_sigterm_handler.__enter_ctx__ = False


@contextlib.contextmanager
def handle_exit(callback=None, append=False):
    """A context manager which properly handles SIGTERM and SIGINT
    (KeyboardInterrupt) signals, registering a function which is
    guaranteed to be called after signals are received.
    Also, it makes sure to execute previously registered signal
    handlers as well (if any).

    >>> app = App()
    >>> with handle_exit(app.stop):
    ...     app.start()
    ...
    >>>

    If append == False raise RuntimeError if there's already a handler
    registered for SIGTERM, otherwise both new and old handlers are
    executed in this order.
    """
    old_handler = signal.signal(signal.SIGTERM, _sigterm_handler)
    if (old_handler != signal.SIG_DFL) and (old_handler != _sigterm_handler):
        if not append:
            raise RuntimeError("there is already a handler registered for "
                               "SIGTERM: %r" % old_handler)

        def handler(signum, frame):
            try:
                _sigterm_handler(signum, frame)
            finally:
                old_handler(signum, frame)
        signal.signal(signal.SIGTERM, handler)

    if _sigterm_handler.__enter_ctx__:
        raise RuntimeError("can't use nested contexts")
    _sigterm_handler.__enter_ctx__ = True

    try:
        yield
    except KeyboardInterrupt:
        pass
    except SystemExit as err:
        # code != 0 refers to an application error (e.g. explicit
        # sys.exit('some error') call).
        # We don't want that to pass silently.
        # Nevertheless, the 'finally' clause below will always
        # be executed.
        if err.code != 0:
            raise
    finally:
        _sigterm_handler.__enter_ctx__ = False
        if callback is not None:
            callback()


if __name__ == '__main__':
    # ===============================================================
    # --- test suite
    # ===============================================================

    import unittest
    import os

    class TestOnExit(unittest.TestCase):

        def setUp(self):
            # reset signal handlers
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            self.flag = None

        def tearDown(self):
            # make sure we exited the ctx manager
            self.assertTrue(self.flag is not None)

        def test_base(self):
            with handle_exit():
                pass
            self.flag = True

        def test_callback(self):
            callback = []
            with handle_exit(lambda: callback.append(None)):
                pass
            self.flag = True
            self.assertEqual(callback, [None])

        def test_kinterrupt(self):
            with handle_exit():
                raise KeyboardInterrupt
            self.flag = True

        def test_sigterm(self):
            with handle_exit():
                os.kill(os.getpid(), signal.SIGTERM)
            self.flag = True

        def test_sigint(self):
            with handle_exit():
                os.kill(os.getpid(), signal.SIGINT)
            self.flag = True

        def test_sigterm_old(self):
            # make sure the old handler gets executed
            queue = []
            signal.signal(signal.SIGTERM, lambda s, f: queue.append('old'))
            with handle_exit(lambda: queue.append('new'), append=True):
                os.kill(os.getpid(), signal.SIGTERM)
            self.flag = True
            self.assertEqual(queue, ['old', 'new'])

        def test_sigint_old(self):
            # make sure the old handler gets executed
            queue = []
            signal.signal(signal.SIGINT, lambda s, f: queue.append('old'))
            with handle_exit(lambda: queue.append('new'), append=True):
                os.kill(os.getpid(), signal.SIGINT)
            self.flag = True
            self.assertEqual(queue, ['old', 'new'])

        def test_no_append(self):
            # make sure we can't use the context manager if there's
            # already a handler registered for SIGTERM
            signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))
            try:
                with handle_exit(lambda: self.flag.append(None)):
                    pass
            except RuntimeError:
                pass
            else:
                self.fail("exception not raised")
            finally:
                self.flag = True

        def test_nested_context(self):
            self.flag = True
            try:
                with handle_exit():
                    with handle_exit():
                        pass
            except RuntimeError:
                pass
            else:
                self.fail("exception not raised")

    unittest.main()
