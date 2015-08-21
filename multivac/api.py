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

class MultivacApi(object):
    def __init__(self, redis_host, redis_port):
        self.app = Flask('multivac')
        self.api = Api(self.app)

        self.app.config['db'] = JobsDB(redis_host, redis_port)

        for resource,path in resource_map.items():
            self.api.add_resource(resource, path)

        @self.app.route('/logs')
        def logs():
            if 'id' not in request.args:
                return json.dumps({'error':'no id provided'}), 400

            db = self.app.config['db']
            logstream = db.get_log(request.args['id'])

            def stream(gen):
                for l in gen:
                    yield l + '\n'

            return Response(stream_with_context(stream(logstream)))

    def start_server(self, listen_port=8000):
        print(('Starting Multivac API v%s' % version))
        http_server = WSGIServer(('', listen_port), self.app)
        http_server.serve_forever()

if __name__ == "__main__":
    self.app.logger.info('Starting multivac v%s' % version)
    self.app.run(host='localhost', port=8000, debug=True)
