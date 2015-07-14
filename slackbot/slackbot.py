import logging
import yaml
import os
from uuid import uuid4
from time import sleep
from multiprocessing import Process,Pipe
from threading import Thread
from slacksocket import SlackSocket
from actions import Noop,all_actions

log = logging.getLogger('slackbot')

class Joblet(object):
    """
    A job
    params:
     - action(obj): action object
     - args(tuple): tuple of action args 
     - event(SlackEvent): full slack event that triggered this job creation
    """
    def __init__(self,action,args,event):
        self.id = str(uuid4().hex)
        self.args = args
        self.event = event

        self.action = action()
        if self.action.needs_confirm == True:
            self.status = 'pending'
        else:
            self.status = 'ready'

    def __str__(self):
        return('Joblet-%s, (%s %s) (%s)' % \
               (self.id,self.action,self.args,self.status))

class SlackBot(object):
    config = { 'workers': 5, 'slack_token': None } #defaults

    #actions = slackbot.actions.all_actions
    actions = all_actions

    def __init__(self,config_path='config.yml'):
        log.info('starting slackbot')

        with open(config_path, 'r') as of:
            self.config.update(yaml.load(of.read()))

        self.jobs = []

        self.slacksocket = SlackSocket(self.config['slack_token'])
        self.me = self.slacksocket.user

        log.info('connected to slack as %s' % self.me)

        t = Thread(target=self.watcher)
        t.start()

        self.controller()

    def controller(self):
        while True:
            #spawn ready jobs
            for job in self._get_all_jobs(status='ready'):
                self._start_job(job)

            #collect ended processes/jobs
            for job in self._get_all_jobs(status='running'):
                if not job.process.is_alive():
                    output = job.pipe.recv()
                    self._reply(job.event,output)
                    job.status = 'completed'


    def watcher(self):
        """
        Watch for any mentions, create a job and mark as ready or pending
        """
        log.info('starting watcher')
        for event in self.slacksocket.events():
            log.debug('saw event %s' % event.json)
            if self.me in event.mentions:
                #parse command, create jobs
                self._parse_command(event)

    def _start_job(self,job):
        parent_conn, child_conn = Pipe()
        p = Process(target=self._worker,args=(job,child_conn))

        job.process = p
        job.pipe = parent_conn
        job.status = 'running'

        p.start()

    def _parse_command(self,event):
        words = event.event['text'].split(' ')
        words.pop(0) #remove @mention

        command = words.pop(0)
        args = tuple(words)

        if command == 'confirm':
            job_id = args[0]
            ok,reason = self._confirm_job(job_id)
            self._reply(event,reason)

        elif command == 'status':
            jobs = [ str(j) for j in self._get_all_jobs() ]
            if not jobs:
                msg = 'no jobs found'
            else:
                msg = '\n'.join(jobs)
            self._reply(event, '```' + msg + '```')

        else:
            if command not in self.actions:
                self._reply(event, 'Not a valid bot action: %s' % command)
                return
            
            action = self.actions[command]

            job = Joblet(action,args,event)
            log.info('created %s' % job)
            self.jobs.append(job)

            if job.status == 'pending':
                self._reply(event, '%s needs confirmation' % str(job))

    def _confirm_job(self, job_id):
        job = self._get_job(job_id)

        if not job:
            return (False,'No such job: %s' % job_id)

        if job.status != 'pending':
            return (False,'Job %s not pending' % job_id)

        job.status = 'ready'

        return (True,'Confirmed job: %s' % job_id)

    def _get_job(self, job_id):
        match = [ j for j in self.jobs if j.id == job_id ]

        if not match:
            return None

        return match[0]

    def _get_all_jobs(self, status=None):
        if status:
            return [ j for j in self.jobs if j.status == status ]
        else:
            return [ j for j in self.jobs ]

    def _reply(self,event,msg):
        """
        Reply to a channel or user derived from a slacksocket message
        """
        #skip any empty messages
        if not msg:
            return

        channel = event.event['channel']

        self.slacksocket.send_msg(msg,channel_name=channel)
        log.info('sent "%s" to "%s"' % (msg,channel))

    def _worker(self,job,conn):
        """ Worker to run jobs """
        print('worker spawned for %s' % job)
            
        output = job.action._run()
        conn.send(output)

        return
