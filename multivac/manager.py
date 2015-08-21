import logging
import yaml
import subprocess
import fcntl
import shlex
import os

from time import sleep
from redis import StrictRedis
from threading import Thread
from copy import deepcopy

from multivac.util import unix_time
from multivac.models import JobsDB

log = logging.getLogger('multivac')

class Manager(object):
    def __init__(self, redis_host, redis_port, config_path='config.yml'):
        self.config_path = config_path
        self.db = JobsDB(redis_host, redis_port)
        self.pids = {} #dict of job_id:subprocess object

        self._load_actions()
        self.run()

    def run(self):
        print('Starting Multivac Manager')
        while True:
            
            #spawn ready jobs
            for job in self.db.get_jobs(status='ready'):
                self._start_job(job)

            #collect ended processes
            pids = deepcopy(self.pids)
            for job_id,pid in pids.items():
                if not self._is_running(pid):
                    self.db.update_job(job_id, 'status', 'completed')
                    log.info('Collected ended job %s' % job_id)
                    del self.pids[job_id]

            sleep(1)

    def _load_actions(self):
        with open(self.config_path, 'r') as of:
            actions = yaml.load(of.read())['actions']

        self.db.purge_actions()

        for action in actions:
            if 'confirm_required' not in action:
                action['confirm_required'] = False

            self.db.add_action(action)
            log.info('loaded action %s' % (action['name']))

    def _start_job(self, job):
        worker = Thread(target=self._job_worker,args=[job])
        worker.daemon = True
        worker.start()

        #thread.join(timeout=1)

    def _is_running(self, pid):
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def _job_worker(self, job):
        log.debug('Worker spawned for job %s' % job['id'])
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

        logger = Thread(
                target=self._log_worker,
                args=[job['id'], proc.stdout, proc.stderr])
        logger.daemon = True
        logger.start()

        proc.wait()
        logger.join(timeout=1)

    def _log_worker(self, job_id, stdout, stderr):
        log.debug('Log handler started for job %s' % job_id)
        while True:
            output = self._read(stdout).strip()
            error = self._read(stderr).strip()
            if output:
                self.db.append_job_log(job_id, output)
                log.debug('%s-STDOUT: %s' % (job_id,output))
            if error:
                self.db.append_job_log(job_id, error)
                log.debug('%s-STDOUT: %s' % (job_id,error))
            if job_id not in self.pids:
                #exit when job has been collected
                self.db.end_job_log(job_id)
                log.debug('Log handler stopped for job %s' % job_id)
                return

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
