# Parts of this file were taken from https://github.com/RDFLib/rdflib-web
# Copyrights by Gunnar Aastrand Grimnes <http://gromgull.net/>

import rdflib

from jinja2 import Environment, contextfilter, Markup
from rdflib.query import ResultSerializer

__all__ = ['HTMLResultSerializer']

namespace_manager = rdflib.Graph().namespace_manager
namespace_manager.bind('xsd', rdflib.XSD)

nm = rdflib.Graph().namespace_manager
nm.bind('xsd', rdflib.XSD)


def qname(ctx, term):
    try:
        if "graph" in ctx:
            label = ctx["graph"].namespace_manager.compute_qname(term, False)
        else:
            label = nm.compute_qname(term, False)
        return u'%s:%s' % (label[0], label[2])
    except Exception as e:
        return term


@contextfilter
def term_to_string(ctx, term):
    if isinstance(term, rdflib.URIRef):
        label = qname(ctx, term)
        return Markup(u"<a href='%s'>%s</a>" % (term, label))
    elif isinstance(term, rdflib.Literal):
        if term.language:
            return '"%s"@%s' % (term, term.language)
        elif term.datatype:
            return '"%s"^^&lt;%s&gt;' % (term, qname(ctx, term.datatype))
        else:
            return '"%s"' % term
    return term


env = Environment()
env.filters["term_to_string"] = term_to_string

RESULT_TEMPLATE = """
<table class="table">
<thead>
    <tr>
    {% for var in result.vars %}
        <th>{{var}}</th>
    {% endfor %}
    </tr>
</thead>
<tbody>
    {% for row in result.bindings %}
        <tr>
        {% for var in result.vars %}
            <td>{{row[var]|term_to_string}}</td>
        {% endfor %}
        </tr>
    {% endfor %}
</tbody>
</table>
"""


class HTMLResultSerializer(ResultSerializer):

    def __init__(self, result):
        ResultSerializer.__init__(self, result)

    def serialize(self, stream, encoding="utf-8"):
        if self.result.type == 'ASK':
            stream.write("<strong>true</strong>".encode(encoding))
            return
        if self.result.type == 'SELECT':
            template = env.from_string(RESULT_TEMPLATE)
            stream.write(template.render(result=self.result))
