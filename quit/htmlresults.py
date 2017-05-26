import rdflib
from rdflib.query import ResultSerializer

from jinja2 import Environment, contextfilter, Markup

SELECT_TEMPLATE="""
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
            <td>{{row[var]}}</td>
        {% endfor %}
        </tr>
    {% endfor %}
</tbody>
</table>
"""

env=Environment()

class HTMLResultSerializer(ResultSerializer):

    def __init__(self, result): 
        ResultSerializer.__init__(self, result)

    def serialize(self, stream, encoding="utf-8"):
        if self.result.type=='ASK':
            stream.write("<strong>true</strong>".encode(encoding))
            return
        if self.result.type=='SELECT':
            template = env.from_string(SELECT_TEMPLATE)
            stream.write(template.render(result=self.result))