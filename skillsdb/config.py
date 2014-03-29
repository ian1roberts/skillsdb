"""    
configuration module
"""

import os
import sys
import base64

import logutils
import models

from sqlalchemy.orm.exc import NoResultFound

KNOWN_DBTYPES = ['sqlite', 'mysql']
FNAME = 'config.cfg'

DEFAULTS = {'filename':FNAME, 'dbtype':'sqlite', 'force':False,
            'user':'skills', 'passwd':base64.encodestring('skills').rstrip(),
            'host':'', 'dbname':'skillsdb.sqlite'}

log = logutils.setup_log(__name__)
class ConfigException(Exception):
    pass

class ConfigOptions(object):
    """Command line arguments override settings read from configuration file"""
    @classmethod
    def customize_parser(cls, parser):
        group = parser.add_argument_group('optional database arguments', cls.__doc__)
        group.add_argument('--force', '-F', action='store_true',
                           help='overwrite existing config file')
        group.add_argument('--user', '-u', type=str,
                           help='database user (skills)', default=DEFAULTS['user'])
        group.add_argument('--passwd', '-p', type=str,
                           help='database passwd (skills)', default=DEFAULTS['passwd'])
        group.add_argument('--host', '-o', type=str,
                           help='database host (blank for local)', default=DEFAULTS['host'])
        group.add_argument('--dbtype', '-d', type=str,
                           help='database type (sqlite)', default=DEFAULTS['dbtype'])
        group.add_argument('--dbname', '-n', type=str,
                           help='database name (blank)', default=DEFAULTS['dbname'])
        
class Config(object):
    """ Configure program session
        Load config from filename or from CLI.
        CLI options take precendence over file settings

        Options fallback to defaults if not specified
    """

    def __init__(self, args, update=False):
        """ Provide some basic validation when options are read
        """
        args.dname, args.bname = get_file_paths(args.filename)
        if not args.dname:
            args.dname = os.getcwd()
        self.args = args
        self.settings = {}

        self.validate_args()

        if args.load:
            self.settings = self.load_config()
        if args.save:
            self.settings = self.load_config(chkfile=False)
            self.save_config()

        if not self.settings:
            log.error('Failed to create session settings')
            sys.exit(-1)

        session = models.init(uri=self['dbname'], host=self['host'], user=self['user'],
                                   passwd=self['passwd'], dbtype=self['dbtype'], path=args.dname)
        log.info("Database session to <%s> established" % self['dbname'])

        if update:
            return session

        try:
            params = session.query(models.Params).one()
        except NoResultFound:
            params =None
            
        if not params:
            param = models.Params(user=self['user'], passwd=self['passwd'])
            session.add(param)
            session.commit()
            log.info('Registerd database owner <%s>' % self['user'])
        else:
            existing_user = params.user
            existing_pass = base64.decodestring(params.passwd)

            current_user = self['user']
            current_pass = base64.decodestring(self['passwd'])

            #print '*Debug: %s :: %s == %s :: %s' % (existing_user, existing_pass, current_user, current_pass)

            if not (existing_user == current_user and existing_pass == current_pass):
                    log.error('Incorrect user (%s) or Password (%s) not valid' % (
                        current_user, current_pass))
                    log.error('Have you changed your password?')
                    log.error('Use the <skillsdb setuser> command to update password tokens')
                    log.error('You will need <user> <prev passwd> <current passwd> to reset')
                    sys.exit(-1)
            log.info('User <%s> with password <hidden> successfully authenticated' % current_user)

    def __repr__(self):
        return "skillsdb Config: %s" % self.__class__

    def __str__(self):
        if not self.settings:
            return "%r, No validated settings" % self
        msg = ""
        for key in DEFAULTS:
            msg += "\n%s=%s" % (key, self[key])
        return msg

    def __getitem__(self, key):
        if key in DEFAULTS:
            return self.settings.get(key, None)
        raise ConfigException, "% is not a known parameter key" % key

    def load_config(self, chkfile=True):
        """ Initialise database from config file.
            Create config file if it doesn't exist
        """
        if chkfile and self.args.bname == FNAME and not os.path.exists(self.args.filename):
            log.info('No previous config file. Setting all defaults in <%s>.' % self.args.bname)
            local_defaults = self.create_default_config()
            self.save_config(local_defaults)

        if not os.path.exists(self.args.filename) and self.args.bname == FNAME:
            log.warning('No config file, probably trying to save uninitialized parameters.\nApply a reinitialization fix.')
            self.load_config()
            
        local_defaults = DEFAULTS
        with open(self.args.filename, 'r') as fh:
            for line in fh:
                src = '<%s> file' % self.args.bname
                if line.startswith('#'):
                    continue
                try:
                    key, value = line.strip().split('\t')
                except ValueError:
                    key = line.strip()
                    value = ""
                    
                key = key.lower().strip()
                
                if key in ['set', 'force']:
                    value = True if value.lower() == 'true' else False
                    
                try:
                    cli_arg = self.parse_arg(key)
                    if DEFAULTS[key] != cli_arg:
                        src = 'command line'
                        value = cli_arg
                        if key == 'passwd':
                            value = base64.encodestring(value).rstrip()
                    local_defaults[key] = value
                    if self.args.load:
                        log.info('Loaded parameter from %s: %s = %s' % (src, key, value))
                except KeyError:
                    log.error("%s is not a valid configuration key. Cannot continue" % key)
                    raise ConfigException, "%s is not a known configuration keyword" % key
                    
        return local_defaults
        
    def save_config(self, local_defaults=None):
        """ Export current program options to config file
        """
        if not local_defaults:
            local_defaults = self.create_default_config()
            
        with open(local_defaults['filename'], 'w') as fh:
            for key, value in local_defaults.iteritems():
                line = '\t'.join([key, str(value)]) + '\n'
                if self.args.save:
                    log.info("Update <%s> config file: %s = %s" %(self.args.bname, key, value))
                fh.write(line)

    def validate_args(self):
        """ Ensure session args are valid
            1) filename exists
            2) database access credentials are sensible
        """
        if self.args.load:
            if not self.args.bname == FNAME and not os.path.exists(self.args.filename):
                raise OSError, (
                    "%s config file could not be found. Check path names" % self.args.filename)

        if self.args.save:
            if os.path.exists(self.args.filename) and not self.args.force:
                raise OSError, (
                    '%s config file exists, specify --force to overwrite' % self.args.filename)

        if self.args.dbtype and self.args.dbtype not in KNOWN_DBTYPES:
            raise ConfigException, '%s is not a known database type. Choose from %s' % (
                self.args.dbtype, ', '.join(KNOWN_DBTYPES)
                )
            
            
    def parse_arg(self, key):
        """ Accessor to return argparse arg via dictionary keyword
        """
        return vars(self.args)[key]

    def create_default_config(self):
        """ Merge CLI args with default program settings
        """
        local_defaults = DEFAULTS
        for key in DEFAULTS:
            cli_arg = self.parse_arg(key)

            if DEFAULTS[key] != cli_arg:
                txt,src = cli_arg if cli_arg else "<nothing>", "command line"
                if key == 'passwd':
                    cli_arg = base64.encodestring(cli_arg).rstrip()
                local_defaults[key] = cli_arg
            else:
                txt,src = DEFAULTS[key] if DEFAULTS[key] else "<nothing>", "defaults"
            log.info("Initialized %s with %s from %s" % (key, txt, src))

        return local_defaults
       

def get_file_paths(fname):
    dname = os.path.dirname(fname)
    bname = os.path.basename(fname)
    return dname, bname

def setuser(args):
    """ Update database user and password access credentials
    """
    print args
        
def main(args):
    """Configure the current program session
    
  A note about database arguments:
  These options overide configuration settings if duplicated in session loading.
  The default database is an SQLite filestore in the current directory.
  If not already present, a new database filestore will be created with the listed defaults.

  If --set [-S] is specified in conjunction with either --user [-u] and/or --passwd [-p]
  an attempt to update credentials will be made.

  Action choices:   
  Load program settings from a configuration file ... fileaname
  Save program settings to a configiration file ... filename
    """
    Config(args)
    

        
if __name__ == '__main__':
    from test.test_config import Params
    p = Params(load=True)
    x = Config(p)

    print x
