""" Provide anicillary objects and features
"""
import config

class Params(object):
    def __init__(self, config_file, **kwargs):
        # user definable database parameters
        self.filename = config_file
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
