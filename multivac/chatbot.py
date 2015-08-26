from multivac.models import JobsDB
from multivac.util import format_time

class ChatBot(object):
    """
    Generic interface for chatbots 
    """
    def __init__(self, redis_host, redis_port):
        self.db  = JobsDB(redis_host, redis_port)

    def read_msg(self, text, user=None, channel=None):
        """
        """
        command,args = self._parse_command(text)

        if command == 'confirm':
            ok,reason = self._confirm_job(args)
            return reason

        elif command == 'workers':
            return self._get_workers()

        elif command == 'jobs':
            return self._get_jobs()

        else:
            ok,result = self.db.create_job(command, args=args, initiator=user)
            if not ok:
                return result

            job_id = result
            log.info('Created job %s' % job_id)

            if self.db.get_job(job_id)['status'] == 'pending':
                self._reply(event, '%s needs confirmation' % str(job_id))

            t = Thread(target=self._output_handler,args=(event, job_id))
            t.daemon = True
            t.start()


    def send_msg(self, text):
        pass

    @staticmethod
    def _parse_command(text):
        """
        Parse message text; return command and arguments
        """
        words = text.split(' ')
        cmd = words.pop(0)
        args = ' '.join(words)

        return cmd, args

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

    def _get_workers(self):
        workers = self.db.get_workers()
        if not workers:
            return 'no registered workers'
        else:
            return [ ('%s(%s)' % (w['name'],w['host'])) for w in workers ]

    def _get_jobs(self, arg):
        subcommands = [ 'pending', 'running', 'completed', 'all' ]
        if arg not in subcommands:
            return 'argument must be one of %s' % ','.join(subcommands)

        jobs = self.db.get_jobs(status=arg)

        if not jobs:
            return 'no matching jobs found'

        formatted = []
        for j in jobs:
            created = format_time(j['created'])
            formatted.append('%s %s(%s) %s' % \
                        (created, j['id'], j['name'], j['status']))

            return formatted
