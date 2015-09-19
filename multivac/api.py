import os
import json
from flask import Flask, Response, redirect, request, render_template
from flask_restful import Api, abort
from gevent.wsgi import WSGIServer
from redis import StrictRedis

from multivac.version import version
from multivac.db import JobsDB
import multivac.resources as mvresources

resource_map = { mvresources.Jobs    : '/jobs',
                 mvresources.Groups  : '/groups',
                 mvresources.Actions : '/actions',
                 mvresources.Workers : '/workers',
                 mvresources.Version : '/version',
                 mvresources.Job     : '/jobs/<string:job_id>',
                 mvresources.Logs    : '/logs/<string:job_id>',
                 mvresources.Cancel  : '/cancel/<string:job_id>',
                 mvresources.Group   : '/groups/<string:group_name>',
                 mvresources.Confirm : '/confirm/<string:job_id>',
                 mvresources.Action  : '/actions/<string:action_name>' }

class MultivacApi(object):

    def __init__(self, redis_host, redis_port, debug=False):
        app_dir = os.path.dirname(os.path.realpath(__file__))
        static_dir = app_dir + '/static'
        template_dir = app_dir + '/templates'

        self.app = Flask('multivac',
                         template_folder=template_dir,
                         static_folder=static_dir)
        self.api = Api(self.app)

        self.app.config['DEBUG'] = debug
        self.app.config['db'] = JobsDB(redis_host, redis_port)

        for resource, path in resource_map.items():
            self.api.add_resource(resource, path)

        @self.app.route('/', methods=['GET'])
        def main():
            db = self.app.config['db']

            return render_template('index.html',
                                   actions=db.get_actions(),
                                   version=version)

    def start_server(self, listen_port=8000):
        print('Starting Multivac API v%s' % version)
        http_server = WSGIServer(('', listen_port), self.app)
        http_server.serve_forever()
