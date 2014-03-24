"""    
configuration module
"""

import os
import sys

import models


class ConfigOptions(object):
    """ Options relevant to import and export of basic program configs
    """
    @classmethod
    def customize_parser(cls, parser):
        group = parser.add_argument_group('Config arguments', cls.__doc__)
        group.add_argument('--user', type=str, help='database user', default='skills')
        group.add_argument('--passwd', type=str, help='database passwd', default='skills')
        group.add_argument('--host', type=str, help='database host (blank for sqlite)', default='')
        group.add_argument('--dbtype', type=str, help='database type (sqlite)', default='sqlite')
        
class Config(object):
    """ Configuration main class
    """
    def __init__(self, args):
        """ Instantiate configuration program with arguments from command line
        """
        self.args = args

    def load_config(self):
        """ Initiate database from config file
        """
        pass
        
    def save_config(self):
        """ Export current program options to config file
        """
        pass
        
def main(args):
    """ Configure program session
        Load program settings from a configuration file
        Save program settings to a configiration file
    """
    sys.exit(Config(args))
    

        
