import logging
import yaml
import subprocess
import fcntl
import shlex
import os

from time import sleep
from redis import StrictRedis
from threading import Thread

from util import unix_time
from models import JobsDB

log = logging.getLogger('slackbot')

class Manager(object):
    def __init__(self, redis_host, redis_port, config_path='config.yml'):
        self.config_path = config_path
        self.db = JobsDB(redis_host, redis_port)
        self.procs = {} #dict of job_id:(process obj,process pipe object)

        self._load_actions()
        self.run()

    def run(self):
        log.info('Starting SlackBot Manager')
        while True:
            
            #spawn ready jobs
            for job in self.db.get_jobs(status='ready'):
                self._start_job(job)

            #collect ended processes
            collected = []
            for job_id in self.procs:
                exitcode = self.procs[job_id].returncode
                if exitcode and exitcode == 0:
                    self.db.update_job(job_id, 'status', 'completed')
                    collected.append(job_id)
                if exitcode and exitcode != 0:
                    self.db.update_job(job_id, 'status', 'failed')
                    collected.append(job_id)

            for j in collected:
                log.info('Collected ended job %s' % j)
                del self.procs[j]

            sleep(1)

    def _load_actions(self):
        with open(self.config_path, 'r') as of:
            actions = yaml.load(of.read())['actions']

        self.db.purge_actions()

        for action in actions:
            if 'confirm_required' not in action:
                action['confirm_required'] = False
            if 'args_required' not in action:
                action['args_required'] = None

            self.db.add_action(action)
            log.info('loaded action %s' % (action['name']))

    def _start_job(self, job):
        job_id = job['id']
        self.db.update_job(job_id, 'status', 'running')

        if job['args']:
            cmd = shlex.split(job['cmd'] + ' ' + job['args'])
        else:
            cmd = job['cmd']

        proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)

        self.procs[job_id] = proc

        thread = Thread(
                target=self._log_worker,
                args=[job_id, proc.stdout, proc.stderr])
        thread.daemon = True
        thread.start()
        thread.join(timeout=1)

    def _worker(self, job, conn):
        """ Worker to run jobs """
        log.info('Worker spawned for job %s' % (job['id']))

        #output = job.action._run()
        conn.send('test')
        sleep(5)

        return

    def _log_worker(self, job_id, stdout, stderr):
        while True:
            output = self._read(stdout).strip()
            error = self._read(stderr).strip()
            if output:
                self.db.append_log(job_id, output)
                log.debug('%s-STDOUT: %s' % (job_id,output))
            if error:
                self.db.append_log(job_id, error)
                log.debug('%s-STDOUT: %s' % (job_id,error))

    def _read(self, pipe):
        """
        Non-blocking method for reading fd
        """
        fd = pipe.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        try:
            return pipe.read()
        except:
            return ""
