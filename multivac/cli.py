import sys
import yaml
import logging
from argparse import ArgumentParser

from multivac.version import version

#defaults
config = { 'api' : {}, 'slackbot' : {} }
subcommands = [ 'worker', 'slackbot', 'api' ]

def main():
    parser = ArgumentParser(description='multivac v%s' % (version))
    parser.add_argument('-c',
                        dest='config_path',
                        help='path to config file (default: %(default)s)',
                        default='/etc/multivac.conf')
    parser.add_argument('-r',
                        dest='redis',
                        help='redis host to connect to (127.0.0.1:6379)',
                        default='127.0.0.1:6379')
    parser.add_argument('-d',
                        action='store_true',
                        help='enable debug output')
    parser.add_argument('subcommand',
                        choices=subcommands)

    args = parser.parse_args()

    if args.d:
        log = logging.getLogger('multivac')
        logging.basicConfig(level=logging.DEBUG)
        log.debug('Debug logging enabled')
    else:
        log = logging.getLogger('multivac')
        logging.basicConfig(level=logging.WARN)

    try:
        with open(args.config_path, 'r') as of:
            config.update(yaml.load(of.read()))
    except IOError:
        print(('error reading config %s' % args.config_path))
        sys.exit(1)

    if ':' in args.redis:
        redis_host,redis_port = args.redis.split(':')
    else:
        redis_host = args.redis
        redis_port = 6379

    if args.subcommand == 'api':
        from multivac.api import MultivacApi
        api = MultivacApi(redis_host,redis_port)

        if 'listen_port' in config['api']:
            api.start_server(listen_port=config['api']['listen_port'])
        else:
            api.start_server()

    if args.subcommand == 'worker':
        from multivac.manager import Manager
        m = Manager(redis_host, redis_port)

    if args.subcommand == 'slackbot':
        if 'slack_token' not in config['slackbot']:
            print('no slack token defined, exiting') 
            sys.exit(1)

        from multivac.slackbot import SlackBot
        s = SlackBot(config['slackbot']['slack_token'], redis_host, redis_port)

if __name__ == '__main__':
    main()
