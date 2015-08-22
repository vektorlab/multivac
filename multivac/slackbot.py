import logging
import yaml
import json
import os

from uuid import uuid4
from time import sleep
from threading import Thread
from slacksocket import SlackSocket

from multivac.models import JobsDB
from multivac.util import format_time

log = logging.getLogger('multivac')

class SlackBot(object):
    """
    params:
     - slack_token(str): 
    """
    def __init__(self, slack_token, redis_host, redis_port, concurrency=5):
        print('Starting Slackbot')

        self.db  = JobsDB(redis_host, redis_port)

        self.slacksocket = SlackSocket(slack_token)
        self.me = self.slacksocket.user

        log.info('connected to slack as %s' % self.me)

        t = Thread(target=self._message_worker)
        t.daemon = True
        t.start()

    def _message_worker(self):
        """
        Watch for any mentions, create a job and mark as ready or pending
        """
        for event in self.slacksocket.events():
            log.debug('saw event %s' % event.json)
            if self.me in event.mentions:
                #parse command, create jobs
                self._parse_command(event)

    def _parse_command(self, event):
        words = event.event['text'].split(' ')
        words.pop(0) #remove @mention

        command = words.pop(0)
        args = ' '.join(words)

        if command == 'confirm':
            job_id = args
            ok,reason = self._confirm_job(job_id)
            self._reply(event, reason)

        elif command == 'workers':
            workers = self.db.get_workers()
            if not workers:
                self._reply(event, 'no registered workers')
            else:
                msg = [ k + ':' + v for k,v in workers.items() ]
                self._reply(event, '\n'.join(msg), code=True)

        elif command == 'jobs':
            subcommands = [ 'pending', 'running', 'completed', 'all' ]
            if args not in subcommands:
                self._reply(event, 'argument must be one of %s' % \
                            ','.join(subcommands))
                return

            jobs = self.db.get_jobs(status=args)

            if not jobs:
                self._reply(event, 'no ' + args + ' jobs found', code=True)
            else:
                msg = []
                for j in jobs:
                    created = format_time(j['created'])
                    msg.append('%s %s(%s) %s' % \
                            (created, j['id'], j['name'], j['status']))

                self._reply(event, '\n'.join(msg), codeblock=True)

        else:
            ok,result = self.db.create_job(command, args=args)
            if not ok:
                self._reply(event, 'failed to create job: %s' % result)
                return
            else:
                job_id = result

            log.info('Created job %s' % job_id)

            if self.db.get_job(job_id)['status'] == 'pending':
                self._reply(event, '%s needs confirmation' % str(job_id))

            t = Thread(target=self._output_handler,args=(event, job_id))
            t.daemon = True
            t.start()

    def _output_handler(self, event, job_id, stream=True):
        """
        Worker to post the output of a given job_id to Slack
        params:
         - stream(bool): Toggle streaming output as it comes in
           vs posting when a job finishes. Default False.
        """
        active = False
        completed = False
        prefix = '[%s]' % job_id

        #sleep on jobs awaiting confirmation
        while not active:
            job = self.db.get_job(job_id)
            if job['status'] != 'pending':
                active = True
            else:
                sleep(1)

        self._reply(event, '%s running' % str(job_id), code=True)

        if stream:
            for line in self.db.get_log(job_id):
                self._reply(event, prefix + line, code=True)
        else:
            msg = ''
            for line in self.db.get_log(job_id):
                msg += prefix + line + '\n'

            self._reply(event, msg, code=True)

        self._reply(event, prefix + ' Done', code=True)

    def _confirm_job(self, job_id):
        job = self.db.get_job(job_id)
        if not job:
            return (False, 'no such job id')
        if job['status'] != 'pending':
            return (False, 'job not awaiting confirm')

        self.db.update_job(job_id, 'status', 'ready')

        return (True,'confirmed job: %s' % job_id)

    def _reply(self, event, msg, code=False, codeblock=False):
        """
        Reply to a channel or user derived from a slacksocket message
        """
        #skip any empty messages
        if not msg:
            return

        if code:
            msg = '`' + msg + '`'

        if codeblock:
            msg = '```' + msg + '```'

        channel = event.event['channel']

        self.slacksocket.send_msg(msg, channel_name=channel, confirm=False)
        log.debug('sent "%s" to "%s"' % (msg, channel))
