import sys
from termcolor import colored

from multivac.version import version
from multivac.models import JobsDB
from multivac.util import format_time

class Console(object):
    def __init__(self):
        self.prompt = colored('multivac> ','cyan',attrs=['bold']) 
        self.db = JobsDB('localhost', 6379)

        self.commands = { 'jobs'    : self.jobs, 
                          'logs'    : self.logs, 
                          'actions' : self.actions,
                          'exit'    : self.exit }
        
        self.run()

    def run(self):
        print('Multivac version %s' % (version))        
        while True:
            cmdline = input(self.prompt).split(' ')
            cmd = cmdline.pop(0)
            args = ' '.join(cmdline)

            if cmd not in self.commands:
                print('invalid command: %s' % (cmd))
            else:
                if args:
                    self.commands[cmd](args)
                else:
                    self.commands[cmd]()

    def jobs(self):
        jobs = self.db.get_jobs()
        for j in jobs:
            created = format_time(j['created'])

            if j['status'] == 'completed':
                status = colored(j['status'], 'green')
            elif j['status'] == 'pending':
                status = colored(j['status'], 'yellow')
            else:
                status = j['status']

            print('%s %s(%s) %s' % (created, j['id'], j['name'], status))

    def logs(self, job_id):
        jobs = self.db.get_jobs()
        if job_id not in [ j['id'] for j in jobs ]:
            print(colored('no such job: %s' % job_id, 'red'))
            return

        print('\n'.join(self.db._get_stored_log(job_id)))


    def actions(self):
        actions = self.db.get_actions()

        output = [ ['Name','Command','Confirm Required'] ]

        for a in actions:
            name = colored(a['name'], 'white', attrs=['bold'])
            output.append([a['name'], a['cmd'], a['confirm_required']])

        self._print_column(output)

    def exit(self):
        sys.exit(0)

    def _print_column(self, data, has_header=True):
        col_width = max(len(word) for row in data for word in row) + 2
        for row in data:
            print(''.join(word.ljust(col_width) for word in row))

if __name__ == '__main__':
    c = Console()
