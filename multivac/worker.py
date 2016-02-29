import os
import socket
import logging
import yaml
import subprocess
import fcntl
import shlex
import names

from time import time, sleep
from redis import StrictRedis
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor

from multivac.util import unix_time
from multivac.db import JobsDB

log = logging.getLogger('multivac')

pending_job_timeout = 300

action_defaults = { 'allow_groups': 'all',
                    'chatbot_stream': True,
                    'confirm_required': False }

class JobWorker(object):
    """
    Multivac worker process. Spawns jobs, streams job stdout/stderr,
    and creates actions and groups in redis from config file.
    """
    def __init__(self, redis_host, redis_port, config_path):
        self.pids = {}  # dict of job_id:subprocess object
        self.db = JobsDB(redis_host, redis_port)

        self.config_path = config_path
        self.read_config(self.config_path)
        self.name = self._get_name()

        self.executor = ThreadPoolExecutor(max_workers=10)

        self.run()

    def run(self):
        print('Starting Multivac Job Worker %s' % self.name)
        while True:
            self.db.register_worker(self.name, socket.getfqdn())

            # spawn ready jobs
            for job in self.db.get_jobs(status='ready'):
                self.executor.submit(self._job_worker, job)

            # collect ended processes
            pids = deepcopy(self.pids)
            for job_id, pid in pids.items():
                if not self._is_running(pid):
                    self.db.cleanup_job(job_id)
                    del self.pids[job_id]
                    print('completed job %s' % job['id'])

            # re-read config if modified
            if os.stat(self.config_path).st_mtime != self.config_mtime:
                log.warn('re-reading modified config %s' % self.config_path)
                self.read_config(self.config_path)

            # cancel pending jobs exceeding timeout
            now = time()
            for job in self.db.get_jobs(status='pending'):
                if (now - int(job['created'])) > pending_job_timeout:
                    print('canceling unconfirmed job %s' % job['id'])
                    self.db.cancel_job(job['id'])

            sleep(1)

    def read_config(self, path):
        with open(path, 'r') as of:
            config = yaml.load(of.read())

        self.config_mtime = os.stat(path).st_mtime

        if 'groups' in config:
            self._read_groups(config['groups'])
        self._read_actions(config['actions'])

    def _read_groups(self, groups):
        self.db.purge_groups()
        for group,members in groups.items():
            self.db.add_group(group, members)
            log.info('loaded group %s' % (group))

    def _read_actions(self, actions):
        self.db.purge_actions()
        for a in actions:

            if 'allow_groups' in a.keys():
                a['allow_groups'] = self._read_action_groups(a['allow_groups'])

            new_action = deepcopy(action_defaults)
            new_action.update(a)

            self.db.add_action(new_action)
            log.info('loaded action %s' % (new_action['name']))

    def _read_action_groups(self, groups):
        if not isinstance(groups, list):
            log.warn('unable to parse allow_groups, defaulting to "all"')
            return 'all'

        defined_groups = self.db.get_groups().keys()
        for g in groups:
            if g not in defined_groups:
                log.warn('no such user group defined: %s' % g)

        return ','.join(groups)

    def _get_name(self):
        """
        Randomly generate a unique name for this worker
        """
        name = names.get_first_name()
        if name in self.db.get_workers():
            self._get_name()
        else:
            return name

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

        print(cmdline)
        proc = subprocess.Popen(
            cmdline,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        print('end popne')

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
                log.debug('%s-STDOUT: %s' % (job_id, output))
            if error:
                error = self._sanitize(error)
                self.db.append_job_log(job_id, error)
                log.debug('%s-STDOUT: %s' % (job_id, error))

            #TODO: do final read of stdout/stderr streams before exiting
            # exit when job has been collected
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
