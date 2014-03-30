"""
Test config.py module
"""
import unittest
import os
from copy import deepcopy

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

    def __getitem__(self, key):
        if hasattr(self, key):
            return getattr(self, key)
        
    def __str__(self):
        msg = ""
        for key in config.DEFAULTS:
            msg += "\n%s=%s" % (key, self[key])
        return msg
  

class ConfigTestSetup(unittest.TestCase):
    """ Common methods for tests
    """
    def remove_files(self, paths, add_dir=True):
        """ Delete an interable of file paths.
            Add dir assumes you want to remove a file from the test/data_out
            Directory
        """
        for path in paths:
            try:
                if add_dir:
                    os.unlink(path_to('data_out/' + path))
                else:
                    os.unlink(path)
            except OSError:
                print "No such path:%s" % path


    def path_config_db(self, config):
        """ Given a config file full path, return
            basename of config and its database
        """
        with open(config, 'r') as fh:
            lines = fh.readlines()
            line = [l for l in lines if l.startswith('dbname')][0]
            key, dbname = line.rstrip().split('\t')

        return (os.path.basename(config), dbname)
                
        
class ConfigProgram(ConfigTestSetup):
    """ Set default configs, validate edge case
        command line and file overrides
    """
    def test_set_defaults(self):
        """ All defaults - new config
            skillsdb config -l
        """
        test_params = Params(config_file='all_defaults.cfg', force=True, load=True)
        settings_expect = config.DEFAULTS
        observed = config.Config(test_params)
        self.assertDictEqual(settings_expect, observed.settings)

        self.remove_files(self.path_config_db(observed['filename']))

    def test_set_defaults_dbname_cla(self):
        """ All defaults - CLA override dbname
            skillsdb config -Fl -n fliggle.sqlite

            NB: as this is a new instance, the CLA gets into the config file
        """
        test_params = Params(config_file='defaults_dbname_cla.cfg',
                             dbname='fliggle.sqlite', force=True, load=True)

        settings_expect = config.DEFAULTS
        settings_expect['filename'] = test_params.filename
        
        observed = config.Config(test_params)
        self.assertDictEqual(settings_expect, observed.settings)
        
        self.remove_files(self.path_config_db(observed['filename']))
        
    def test_init_dbase_from_file_with_CLA_mod(self):
        """ Load Test init dbase from config file
            supply CLA dbname name, expected behaviour is that name wont end up in
            config file - this is a session level customization
        
            skillsdb config -Fl --dbname new_db.sqlite file_init_test.cfg 
        """
        # initialize a clean database
        test_params = Params(config_file='file_init_test.cfg',
                             dbname='file_init_test.sqlite',
                             force=True, load=True)
        settings_expect = config.DEFAULTS
        observed1 = config.Config(test_params)
        obs1_settings = deepcopy(observed1.settings)
        self.assertDictEqual(settings_expect, obs1_settings)

        # read settings from file
        test_params.dbname = "new_db.sqlite"
        observed2 = config.Config(test_params)
        obs2_settings = deepcopy(observed2.settings)

        # dbname in config file not equal to dbname observed
        # demonstrate from copied settings dictionaries too
        file_, dbname = self.path_config_db(observed2['filename'])
        self.assertNotEqual(dbname, observed2['dbname'])
        self.assertNotEqual(obs1_settings['dbname'], obs2_settings['dbname'])
        # dbname in config file is original dbname
        self.assertEqual(dbname,'file_init_test.sqlite')
        self.assertEqual(observed2['dbname'],'new_db.sqlite')
        # dbname in config file != settings dbname

        self.remove_files([file_, dbname, observed2['dbname']])

    def test_init_dbase_from_file_with_CLA_mod_saved(self):
        """ Save Test init dbase from config file
            Supply CLA dbname and save changes. Expected behavior is that
            dbname ends up in config file.

            skillsdb config -Fs --dbname new_db.sqlite file_init_test.cfg
        """
        test_params = Params(config_file='file_init_save_test.cfg',
                             dbname='file_init_save_test.sqlite',
                             force=True, save=True)
        settings_expect = config.DEFAULTS
        observed1 = config.Config(test_params)
        obs1_settings = deepcopy(observed1.settings)

        self.assertDictEqual(settings_expect, observed1.settings)

        # read settings from file
        test_params.dbname = "new_save_db.sqlite"
        observed2 = config.Config(test_params)
        obs2_settings = deepcopy(observed2.settings)
        file_, dbname = self.path_config_db(observed2['filename'])

        # dbname in config file NOT equal to original dbname obs1
        self.assertNotEqual(obs1_settings['dbname'], obs2_settings['dbname'])
        # dbname in config file equals updated dbname obs2
        self.assertEqual(obs2_settings['dbname'], dbname)

        self.remove_files([file_, obs1_settings['dbname'],
                           obs2_settings['dbname']])

        
        


