"""
Test config.py module
"""
import unittest
import os

from skillsdb import (config, models)

def drop_db(x, host='', user='skills', passwd='skills', dbtype='sqlite', echo=False):
    engine = models.sa.create_engine(
        'sqlite:///' + user + ':' + passwd + '@' + host + '/' + x, poolclass=models.NullPool)
    models.metadata.drop_all(engine)

def path_to(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

class Params(object):
    def __init__(self, config_file=config.FNAME, **kwargs):
        # user definable database parameters
        self.filename = path_to('data_out/' + config_file)
        self.user = 'skills'
        self.passwd = 'skills'
        self.host = ''
        self.dbtype = 'sqlite'
        self.dbname = 'skillsdb.sqlite'
        self.force = False
        self.set = False
        self.load = False
        self.save = False

        for k,v in kwargs.iteritems():
            setattr(self, k, v)
  

class ConfigTestSetup(unittest.TestCase):
    """ Common methods for tests
    """
    def setUp(self):
        if os.path.exists(path_to('data_out/config.txt')):
            self.remove_files()
        config_file = path_to('test_config_file.txt')
        self.params_custom = Params(config_file)
        self.params_default = Params(load=True)


    def remove_files(self):
        os.unlink(path_to('data_out/config.txt'))
        
class ConfigProgram(ConfigTestSetup):
    
    def test_set_defaults(self):
        """ Set default configs when no settings provided
        """
        settings_expect = config.DEFAULTS
        options = config.Config(self.params_default)
        self.assertDictEqual(settings_expect, options.settings)

    def test_init_dbase_direct(self):
        """ Test init dbase from CLIs
        """
        pass
        
    def test_init_dbase_indirect(self):
        """ Test init dbase from file
        """
        pass
        


