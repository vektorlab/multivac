import json
from flask import current_app
from flask_restful import Resource,Api,reqparse,request,abort

app = current_app

class Hello(Resource):
    def get(self):
        return {},200

    def post(self):
        return {},403

class Jobs(Resource):
    def get(self):
        db = app.config['db']
        return db.get_jobs(),200

    def post(self):
        app.logger.info(json.dumps(request.args))
        args = self._parse()
        db = app.config['db']

        job_id = db.create_job(args['action'],args=args['action_args'])
        if not job_id:
            return { 'error': 'failed to create job' },400

        return { 'id': job_id }

    def _parse(self):
        parser = reqparse.RequestParser()
        parser.add_argument('action', type=str)
        parser.add_argument('action_args', type=str)
        return parser.parse_args()

class Actions(Resource):
    def get(self):
        db = app.config['db']
        return db.get_actions(),200
