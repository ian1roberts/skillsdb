"""
skillsdb is a simplate database driven program for managing people
and their associated skills

Ian Roberts

ian.roberts@cantab.net

March 2014

GPL V2.0 
"""

import argparse
import sys

import config
import view

parser = argparse.ArgumentParser(prog='skillsdb', description=sys.modules[__name__].__doc__)
parser.add_argument('--verbose', '-v', action='count', help='verbosity (use -vv for debug)')

subparsers = parser.add_subparsers(help='sub-command help')

# config
parser_group = subparsers.add_parser('config', description=config.main.__doc__, help="configure databse and general options")
parser_group.add_argument('--file', type=str, help="configuration filename", default="config.txt")
parser_group.add_argument('--user', type=str, help='database user', default='skills')
parser_group.add_argument('--passwd', type=str, help='database passwd', default='skills')
parser_group.add_argument('--host', type=str, help='database host (blank for sqlite)', default='')
parser_group.add_argument('--dbtype', type=str, help='database type (sqlite)', default='sqlite')
parser_group.add_argument('database', type=str, help='Database name to use',default='skills.sqlite')

config.ConfigOptions.customize_parser(parser_group)
# views
parser_group.subparsers.add_parser('manage', description=view.main._doc__, help="Manage database")
parser_group.add_argument('skill', type=str, help="operation on skills table")
parser_group.add_argument('person', type=str, help="operation on persons table")
parser_group.add_argument('search', type=str, help="search for skill or person")
view.ViewOptions.customize_parser(parser_group)
