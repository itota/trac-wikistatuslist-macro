# Copyright (c) 2010, Takashi Ito
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the authors nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from trac.core import *
from trac.web.api import IRequestFilter
from trac.web.chrome import add_stylesheet, ITemplateProvider
from trac.wiki.macros import WikiMacroBase
from trac.util import format_datetime, pretty_timedelta
from genshi.builder import tag


class WikiStatusListMacro(WikiMacroBase):

    implements(IRequestFilter, ITemplateProvider)

    headers = ['Page', 'Last modified', 'Version', 'Author', 'Comment']
    thead = tag.thead(tag.tr([tag.th(x) for x in headers]))

    def _build_row(self, name, time, author, version, comment):
        cols = []
        # page name
        if self.pagename == 'short':
            _name = name.rsplit('/', 1)[-1]
        else:
            _name = name
        cols.append(tag.td(tag.a(_name, href=self.href.wiki(name)), class_='name'))
        # last modified
        href_ago = self.href('timeline', precision='seconds', from_=format_datetime(time, 'iso8601'))
        a_ago = [' (', tag.a(pretty_timedelta(time), href=href_ago), ' ago)']
        cols.append(tag.td(format_datetime(time, self.date_format), a_ago, class_='time'))
        # version
        a_version = tag.a(version, href=self.href.wiki(name, version=version))
        a_diff = tag.a('d', title='diff', href=self.href.wiki(name, action='diff', version=version))
        a_history = tag.a('h', title='history', href=self.href.wiki(name, action='history'))
        cols.append(tag.td(a_version, ' [', a_diff, '|', a_history, ']', class_='version'))
        cols.append(tag.td(author, class_='author'))
        cols.append(tag.td(comment, class_='comment'))
        return tag.tr(cols)

    # WikiMacroBase methods
    def expand_macro(self, formatter, name, content, args={}):
        self.href = formatter.req.href
        db = self.env.get_db_cnx()
        cursor = db.cursor()

        params = [x.strip() for x in content.split(',')]
        pages = [x for x in params if '=' not in x]
        kwargs = dict([x.split('=', 1) for x in params if '=' in x])
        if not pages:
            pages = ['*']

        order = kwargs.get('order') != 'reverse' and 'DESC' or ''
        self.date_format = kwargs.get('date_format', '%Y-%m-%d %H:%M:%S')
        self.pagename = kwargs.get('pagename')

        cursor.execute(
            'SELECT name, time, author, version, comment FROM wiki AS w1' +
            ' WHERE version=(SELECT MAX(version) FROM wiki AS w2 WHERE w1.name=w2.name) AND (' +
            ' OR '.join(['name LIKE "%s"' %  x.replace('*', '%') for x in pages]) + ')' +
            ' ORDER BY time ' + order)

        rows = [self._build_row(*x) for x in cursor]

        return tag.table(self.thead, tag.tbody(rows),
                         class_='wikistatuslist',
                         bgcolor=kwargs.get('bgcolor', '#F0F0F0'))

    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        return handler

    def post_process_request(self, req, template, data, content_type):
        add_stylesheet(req, 'wikistatuslist/style.css')
        return (template, data, content_type)

    # ITemplateProvider methods
    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('wikistatuslist', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        return []

