import os
import socket
import logging
import yaml
import subprocess
import fcntl
import shlex
import names

from time import sleep
from redis import StrictRedis
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor

from multivac.util import unix_time
from multivac.db import JobsDB

log = logging.getLogger('multivac')

class JobWorker(object):
    def __init__(self, redis_host, redis_port, config_path):
        self.pids = {} #dict of job_id:subprocess object
        self.config_path = config_path
        self.db = JobsDB(redis_host, redis_port)

        self._load_actions()
        self.name = self._get_name()

        self.executor = ThreadPoolExecutor(max_workers=10)

        self.run()

    def run(self):
        print('Starting Multivac Job Worker %s' % self.name)
        while True:
            
            self.db.register_worker(self.name, socket.getfqdn())

            #spawn ready jobs
            for job in self.db.get_jobs(status='ready'):
                self.executor.submit(self._job_worker, job)

            #collect ended processes
            pids = deepcopy(self.pids)
            for job_id,pid in pids.items():
                if not self._is_running(pid):
                    self.db.cleanup_job(job_id)
                    del self.pids[job_id]
                    print('completed job %s' % job['id'])

            sleep(2)

    def _get_name(self):
        name = names.get_first_name()
        if name in self.db.get_workers():
            self._get_name()
        else:
            return name

    def _load_actions(self):
        with open(self.config_path, 'r') as of:
            actions = yaml.load(of.read())['actions']

        self.db.purge_actions()

        for action in actions:
            if 'confirm_required' not in action:
                action['confirm_required'] = False

            self.db.add_action(action)
            log.info('loaded action %s' % (action['name']))

    def _is_running(self, pid):
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def _job_worker(self, job):
        print('running job %s' % job['id'])
        self.db.update_job(job['id'], 'status', 'running')

        if job['args']:
            cmdline = shlex.split(job['cmd'] + ' ' + job['args'])
        else:
            cmdline = job['cmd']

        proc = subprocess.Popen(
                cmdline,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)

        self.pids[job['id']] = proc.pid

        self.executor.submit(self._log_worker,
                             job['id'],
                             proc.stdout,
                             proc.stderr)

        proc.wait()

    def _log_worker(self, job_id, stdout, stderr):
        log.debug('Log handler started for job %s' % job_id)
        while True:
            output = self._read(stdout)
            error = self._read(stderr)
            if output:
                output = self._sanitize(output)
                self.db.append_job_log(job_id, output)
                log.debug('%s-STDOUT: %s' % (job_id,output))
            if error:
                error = self._sanitize(error)
                self.db.append_job_log(job_id, error)
                log.debug('%s-STDOUT: %s' % (job_id,error))

            #exit when job has been collected
            if job_id not in self.pids:
                log.debug('Log handler stopped for job %s' % job_id)
                return

    def _sanitize(self, line):
        line = line.decode('utf-8')
        line = line.replace('\n', '')

        return line

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
