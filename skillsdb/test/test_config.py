"""
Test config.py module
"""
import unittest
import os

from skillsdb import config, dbase

def drop_db(x, host='', user='skills', passwd='skills', dbtype='sqlite', echo=False):
    engine = dbase.sa.create_engine(
        'sqlite:///' + user + ':' + passwd + '@' + host + '/' + x, poolclass=dbase.NullPool)
    dbase.metadata.drop_all(engine)

def path_to(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

class Params(object):
    def __init__(self, config_file):
        # user definable database parameters
        self.database = 'getfs_test_db'
        self.user = 'skills'
        self.passwd = 'skills'
        self.host = ''
        self.dbtype = 'sqlite'
        self.database_name = 'skilssdb.sqlite'
        self.config_file = config_file
  

class ConfigTestSetup(unittest.TestCase):
    """ Common methods for tests
    """
    def setUp(self):
        if os.path.exists(path_to('data_out/sample_reads')):
            self.remove_files()
  
        database_name = 'my_skillsdb.sqlite'
        config_file = path_to('test_config_file.txt')
        params = Params(config_file)
        
        self.params = params
        
class ConfigProgram(ConfigTestSetup):
    
    def test_parse_params(self):
        """ Test config file parameter parsing
        """
        # Read configuration file
        options = config.import_config(self.params.config_file)

    def test_init_dbase_direct(self):
        """ Test init dbase from CLIs
        """
        pass
        
    def test_init_dbase_indirect(self):
        """ Test init dbase from file
        """
        pass
        


