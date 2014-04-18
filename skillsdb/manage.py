"""
skillsdb is a simple database driven program for managing people
and their associated skills

Ian Roberts

ian.roberts@cantab.net

March 2014

GPL V2.0 
"""

import argparse
from argparse import RawDescriptionHelpFormatter

import sys
import textwrap

import config
import views

parser = argparse.ArgumentParser(prog='skillsdb', description=textwrap.dedent(sys.modules[__name__].__doc__), formatter_class=RawDescriptionHelpFormatter)
parser.add_argument('--verbose', '-v', action='count', help='verbosity (use -vv for debug)')

subparsers = parser.add_subparsers(help='sub-command help')

# config
parser_group = subparsers.add_parser('config', description=config.main.__doc__, help="configure databse and general options", formatter_class=RawDescriptionHelpFormatter)
parser_group.set_defaults(func=config.main)

parser_group._optionals.title = 'action'

group = parser_group.add_mutually_exclusive_group(required=True)
group.add_argument('--load', '-l', action='store_true', help="Load a configuration file")
group.add_argument('--save', '-s', action='store_true', help="Save a configuration file")
parser_group.add_argument('filename', nargs="?", type=str, help="Configuration filename",
                          default=config.FNAME)

config.ConfigOptions.customize_parser(parser_group)

# views
parser_group = subparsers.add_parser('manage', description=views.main.__doc__, help="Manage database")
parser_group.set_defaults(func=views.main)
parser_group.add_argument('--pid', type=int, help="Parent record ID", default=None)
parser_group.add_argument('--config', '-C', type=str, help="config filename (config.cfg)", default=config.FNAME)

parser_group.add_argument('input', nargs=argparse.REMAINDER, help="Field data string")
group = parser_group.add_mutually_exclusive_group(required=True)
group.add_argument('--add','-A', action='store_true', help="Add a record")
group.add_argument('--delete','-D', action='store_true', help="Delete a record")
group.add_argument('--modify','-M', action='store_true', help="Modify a record")
group.add_argument('--search', '-S', action='store_true', help="Search for a record")

views.ViewOptions.customize_parser(parser_group)


# setuser
parser_group = subparsers.add_parser('setuser', description=config.setuser.__doc__, help="Change databse user or reset password")
parser_group.set_defaults(func=config.setuser)
parser_group.add_argument('oldvalue', type=str, help='Previous value')
parser_group.add_argument('newvalue', type=str, help='New value')
parser_group.add_argument('filename', type=str, help='config file name')

group = parser_group.add_mutually_exclusive_group(required=True)
group.add_argument('--update-user', '-U', action='store_true', help='database user (skills)')
group.add_argument('--update-passwd', '-P', action='store_true', help='database passwd (skills)')

