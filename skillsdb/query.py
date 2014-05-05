""" skillsdb query module
    Queries are table specific

    address queries do startswith and contains

    --address key=value translates to

    line01.startswith ...
    line01.endswith ...
    line01.contains ...

    compound expressions are evaluated with conditionals
    key=value OR key=value

    allowed operators are AND / OR only
"""

import os
import sys
import models
import config


class SkillsQuery(object):
    """ Perform queries on skills_db
        1) generic parser
        2) interpretor
        3) validator
        4) perform lookup
        5) return results
    """

    def __init__(self, **kwargs):
        """
        """
        self.table = kwargs['table']
        self.query_string = kwargs['input']

        self.parse_query()
        self.validate_query()
        self.construct_query()


    def parse_query(self):
        """ extract key value pairs
        """
        pass
        
        
    def validate_query(self):
        """ determine that key value pairs are valid search terms
            determine whether compound operators are valid

            determine that kv pairs and operators are valid for table
        """
        pass

    def construct_query(self):
        """ turn validated query components in to valid sqlorm
        """
        pass
        
        
        
