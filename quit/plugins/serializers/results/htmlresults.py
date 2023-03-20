# Parts of this file were taken from https://github.com/RDFLib/rdflib-web
# Copyrights by Gunnar Aastrand Grimnes <http://gromgull.net/>
#
# LICENSE AGREEMENT FOR RDFLIB
# ------------------------------------------------
# Copyright (c) 2002-2017, RDFLib Team
# See CONTRIBUTORS and http://github.com/RDFLib/rdflib
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#   * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
#   * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following
# disclaimer in the documentation and/or other materials provided
# with the distribution.
#
#   * Neither the name of Daniel Krech nor the names of its
# contributors may be used to endorse or promote products derived
# from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import rdflib

from jinja2 import Environment, contextfilter, Markup
from rdflib.query import ResultSerializer

__all__ = ('HTMLResultSerializer')

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
    except Exception:
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
