import time
import json
from flask import Flask, Response, redirect, request, stream_with_context
from flask_restful import Api,abort
from gevent.wsgi import WSGIServer
from redis import StrictRedis

from multivac.version import version
from multivac.models import JobsDB
from multivac.resources import Jobs, Actions, Hello, Confirm

resource_map = { Hello   : '/',
                 Jobs    : '/jobs',
                 Actions : '/actions',
                 Confirm : '/confirm' }

class Api(object):
    def __init__(self, redis_host, redis_port):
        self.app = Flask('multivac')
        self.api = Api(app)

        self.app.config['db'] = JobsDB(redis_host, redis_port)

        for resource,path in resource_map.iteritems(): 
            self.api.add_resource(resource, path)

        @app.route('/logs')
        def logs():
            if not request.args.has_key('id'):
                return json.dumps({'error':'no id provided'}), 400

            logstream = app.config['db'].get_logstream(request.args['id'], append_newline=True)
            return Response(stream_with_context(logstream))

    def start_server(self, listen_port):
        http_server = WSGIServer('', listen_port, self.app)
        http_server.serve_forever()

if __name__ == "__main__":
    app.logger.info('Starting multivac v%s' % version)
    app.run(host='localhost', port=8000, debug=True)
