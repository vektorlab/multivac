import json
import operator
from flask import Response, current_app, stream_with_context
from flask_restful import Resource, Api, reqparse, request, abort

from multivac.version import version

app = current_app

def make_response(msg=None):
    response_msg = {'ok': True}
    if msg:
        response_msg['message'] = msg

    response = Response(json.dumps(response_msg))
    response.status_code = 200

    return response

def make_error(status_code, msg):
    error_msg = {'status': status_code, 'message': msg, 'ok': False}
    response = Response(json.dumps(error_msg))
    response.status_code = status_code

    return response

def invalid_resource():
    return make_error(410, 'a resource with that id does not exist')

class Version(Resource):
    def get(self):
        return {'version': 'v%s' % version}, 200

class Confirm(Resource):
    def post(self, job_id):
        db = app.config['db']

        job = db.get_job(job_id)
        if not job:
            return invalid_resource()
        if job['status'] != 'pending':
            return make_error(400, 'job not awaiting confirm')

        db.update_job(job_id, 'status', 'ready')

        return {'ok': True}

class Cancel(Resource):
    def post(self, job_id):
        db = app.config['db']

        job = db.get_job(job_id)
        if not job:
            return invalid_resource()

        ok,result = db.cancel_job(job_id)
        if not ok:
            return make_error(400, result)

        return { 'ok': True }

class Job(Resource):
    def get(self, job_id):
        job = app.config['db'].get_job(job_id)
        if not job:
            return invalid_resource()

        return job, 200

class Jobs(Resource):
    def get(self):
        db = app.config['db']
        jobs = db.get_jobs()
        jobs.sort(key=operator.itemgetter('created'), reverse=True)

        return jobs, 200

    def post(self):
        args = self._parse()
        db = app.config['db']

        if not args['action']:
            return make_error('missing required parameter "action"', 400)

        ok,result = db.create_job(args['action'],
                                  args=args['action_args'],
                                  initiator='api_user')
        if not ok:
            return make_error(400, result)

        return {'id': result}, 200

    def _parse(self):
        parser = reqparse.RequestParser()
        parser.add_argument('action', type=str)
        parser.add_argument('action_args', type=str)
        return parser.parse_args()

class Logs(Resource):
    def get(self, job_id):
        args = self._parse()
        db = app.config['db']

        def stream(gen):
            for l in gen:
                yield l + '\n'

        if args['json']:
            return [l for l in db.get_stored_log(job_id)], 200

        logstream = db.get_log(job_id)
        return Response(stream_with_context(stream(logstream)))

    def _parse(self):
        parser = reqparse.RequestParser()
        parser.add_argument('json', type=bool)
        return parser.parse_args()

class Action(Resource):
    def get(self, action_name):
        action = app.config['db'].get_action(action_name)
        if not action:
            return invalid_resource()

        return action, 200

class Actions(Resource):
    def get(self):
        return app.config['db'].get_actions(), 200

class Group(Resource):
    def get(self, group_name):
        group = app.config['db'].get_group(group_name)
        if not group:
            return invalid_resource()

        return group, 200

class Groups(Resource):
    def get(self):
        return app.config['db'].get_groups(), 200

class Workers(Resource):
    def get(self):
        return app.config['db'].get_workers(), 200
