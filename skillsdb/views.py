"""
Database views
"""
import os
import sys

import models

class ViewOptions(object):
    """ Options to extend view methods
    """
    @classmethod
    def customize_parser(cls, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--parent', action='store_true', help='Work on parent table')
        group.add_argument('--child', action='store_true', help='Work on child table')
        group.add_argument('--skill', action='store_true', help='Work on skill table')
        group.add_argument('--freetime', action='store_true', help='Work on freetime table')
        group.add_argument('--address', action='store_true', help='Work on address table')

class View(object):
    """ Dispatch database command
    """
    def __init__(self, args):
        """ Instantiate view and dispatch database command
        
        Arguments:
        - `args`:
        """
        self.args = args

        def parse_command(self):
            """ Parse command from input
            """
            pass

def main(args):
    """ Parse input command and dispatch
    """
    sys.exit(View(args))
