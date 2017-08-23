import rdflib

from jinja2 import Environment, Markup
from rdflib.query import ResultSerializer

__all__ = ['HTMLResultSerializer']

namespace_manager = rdflib.Graph().namespace_manager
namespace_manager.bind('xsd', rdflib.XSD)

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
            print("hello")
            template = env.from_string(RESULT_TEMPLATE)
            stream.write(template.render(result=self.result))
