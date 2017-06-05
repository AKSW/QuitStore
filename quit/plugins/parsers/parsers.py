from flask.ext.api.parsers import BaseParser


class NQuadsParser(BaseParser):
    """A parser for n-quads."""

    media_type = 'application/nquads'

    def parse(self, stream, media_type, **options):
        """Simply return a string representing the body of the request."""
        return stream.read().decode('utf8')
