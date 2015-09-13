import sys
import yaml
import logging
from argparse import ArgumentParser

from multivac.version import version

log = logging.getLogger('multivac')

subcommands = ['worker', 'slackbot', 'api', 'console']
# defaults
config = {'api_listen_port': 8000,
          'slack_token': None,
          'redis': '127.0.0.1:6379'}


def main():
    parser = ArgumentParser(description='multivac v%s' % (version))
    parser.add_argument('-c',
                        dest='config_path',
                        help='path to config file (default: %(default)s)',
                        default='/etc/multivac.yml')
    parser.add_argument('-d',
                        action='store_true',
                        help='enable debug output')
    parser.add_argument('subcommand',
                        choices=subcommands)

    args = parser.parse_args()

    if args.d:
        debug = True
        logging.basicConfig(level=logging.DEBUG)
        log.debug('Debug logging enabled')
    else:
        debug = False
        logging.basicConfig(level=logging.WARN)

    try:
        with open(args.config_path, 'r') as of:
            config.update(yaml.load(of.read()))
    except IOError:
        print(('error reading config %s' % args.config_path))
        sys.exit(1)

    if ':' in config['redis']:
        redis_host, redis_port = config['redis'].split(':')
    else:
        redis_host = config['redis']
        redis_port = 6379

    if args.subcommand == 'api':
        from multivac.api import MultivacApi
        api = MultivacApi(redis_host, redis_port, debug=debug)
        api.start_server(listen_port=config['api_listen_port'])

    if args.subcommand == 'console':
        from multivac.console import ConsoleBot
        c = ConsoleBot(redis_host, redis_port)

    if args.subcommand == 'worker':
        from multivac.worker import JobWorker
        w = JobWorker(redis_host, redis_port, args.config_path)

    if args.subcommand == 'slackbot':
        if not config['slack_token']:
            print('no slack token defined, exiting')
            sys.exit(1)

        from multivac.slackbot import SlackBot
        s = SlackBot(config['slack_token'], redis_host, redis_port)


if __name__ == '__main__':
    main()
