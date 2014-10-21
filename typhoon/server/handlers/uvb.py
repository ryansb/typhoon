"""
This file is part of typhoon, a request-counting web server.
Copyright (C) 2014 Ryan Brown <sb@ryansb.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from tornado.gen import coroutine
import tornado.web


class CountingHandler(tornado.web.RequestHandler):
    @coroutine
    def get(self):
        self.application._counters[self.get_argument('name')] += 1
        self.write("yolo")
