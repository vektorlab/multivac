import yaml
import sys
from argparse import ArgumentParser

from multivac.version import version
from multivac.slackbot import SlackBot
from multivac.manager import Manager
from multivac.api import MultivacApi

#defaults
config = { 'api' : {}, 'slackbot' : {} }

def main():
    common_parser = ArgumentParser(add_help=False)
    common_parser.add_argument('--config',
                        dest='config_path',
                        help='path to config file (/etc/multivac.conf)',
                        default='/etc/multivac.conf')
    common_parser.add_argument('--redis',
                        dest='redis',
                        help='redis host to connect to (127.0.0.1:6379)',
                        default='127.0.0.1:6379')

    parser = ArgumentParser(description='multivac v%s' % (version))
    subparsers = parser.add_subparsers(description='multivac subcommands',
                                       dest='subcommand')

    #worker
    parser_worker = subparsers.add_parser('worker',parents=[common_parser])

    #slackbot
    parser_slackbot = subparsers.add_parser('slackbot',parents=[common_parser])

    #api
    parser_api = subparsers.add_parser('api',parents=[common_parser])

    args = parser.parse_args()

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
        api = MultivacApi(redis_host,redis_port)

        if 'listen_port' in config['api']:
            api.start_server(listen_port=config['api']['listen_port'])
        else:
            api.start_server()

    if args.subcommand == 'worker':
        m = Manager(redis_host, redis_port)

    if args.subcommand == 'slackbot':
        if 'slack_token' not in config['slackbot']:
            print('no slack token defined, exiting') 
            sys.exit(1)

        s = SlackBot(config['slackbot']['slack_token'], redis_host, redis_port)

if __name__ == '__main__':
    main()
