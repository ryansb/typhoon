"""
Copyright (C) 2014 Ryan Brown <sb@ryansb.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from tornado.options import define, options
from tornado import httpclient
import tornado.ioloop
import tornado.process
from tornado.ioloop import PeriodicCallback

define("target", default="http://starfighter.csh.rit.edu:8080/")
define("requests", default=1000)

fizz = 0
factor = 0

def main():
    import tornado.options
    tornado.options.parse_command_line()
    global factor
    factor = int(float(options.requests) / float(tornado.process.cpu_count()))
    tornado.process.fork_processes(None)

    PeriodicCallback(is_done, 200).start()

    main_loop = tornado.ioloop.IOLoop.instance()
    main_loop.add_callback(request_all_things)
    main_loop.start()


def is_done():
    global fizz

    if fizz >= factor-4:
        print("Completed {} requests".format(fizz))
        tornado.ioloop.IOLoop.current().stop()

def request_all_things():
    http_client = httpclient.AsyncHTTPClient()

    def add_fizz(arg=None):
        global fizz
        fizz += 1

    for i in range(0, int(factor)):
        http_client.fetch(options.target, add_fizz)
