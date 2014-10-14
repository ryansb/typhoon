import logging
import tornado.ioloop
import tornado.web
import tornado.httpserver
import tornado.web
from tornado.options import options
from typhoon.server.settings import settings
from typhoon.server.url_patterns import url_patterns


class App(tornado.web.Application):

    def __init__(self):
        """App wrapper constructor, global objects within our Tornado platform
        should be managed here."""
        self.logger = logging.getLogger(self.__class__.__name__)

        tornado.web.Application.__init__(self, url_patterns, **settings)


def main():
    """Main function for running stand alone"""

    logger = logging.getLogger()
    tornado.options.parse_command_line()
    app = App()
    http_server = tornado.httpserver.HTTPServer(app, xheaders=True)
    http_server.listen(options.port)

    logger.info('Tornado server started on port %s', options.port)

    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        logger.info("Stopping server on port %s",  options.port)
