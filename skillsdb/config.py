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

DEFAULTS = {'filename':FNAME, 'dbtype':'sqlite', 'force':'',
            'user':'skills', 'passwd':'skills',
            'host':'', 'dbname':'skillsdb.sqlite'}

log = logutils.setup_log(__name__)
class ConfigException(Exception):
    pass

class ConfigOptions(object):
    """Command line arguments override settings read from configuration file if forced with -F"""
    @classmethod
    def customize_parser(cls, parser):
        group = parser.add_argument_group('optional database arguments', cls.__doc__)
        group.add_argument('--force', '-F', action='store_true',
                           help="""save:overwrite existing.
                           load:command line overrules file value""")
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
        args.filename = os.path.join(args.dname, args.bname)
        self.args = args
        self.settings = {}
        self.validate_args()

        log.info('skillsdb configuration:%s' % args.filename)

        if args.load:
            self.settings = self.load_config()
        if args.save:
            self.settings = self.load_config()
            self.save_config()

        if not self.settings:
            log.error('Failed to create session settings')
            sys.exit(-1)
            
        # Return if performing user / passwd update of database params
        if update:
            log.info("Attempt to update database credentials")
            return
            
        session = self.get_session()
        log.info("Database session to <%s> established" % self['dbname'])

        # Simple database authentication (simply check current user / passwd hash
        # against stored credentials)
        try:
            params = session.query(models.Params).one()
        except NoResultFound:
            params =None
            
        if not params:
            param = models.Params(user=self.user, passwd=self.passwd_hash)
            session.add(param)
            session.commit()
            log.info('Registerd database owner <%s>' % self['user'])
        else:
            existing_user = params.user
            existing_pass = params.passwd

            current_user = self.user
            current_pass = self.passwd_hash
            #print '*Debug: %s :: %s == %s :: %s' % (
            #      existing_user, existing_pass, current_user, current_pass)

            if not (existing_user == current_user and existing_pass == current_pass):
                    log.error('Incorrect user (%s) or Password hash (%s) not valid' % (
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
        
    def get_session(self):
        """ Return a database session according to config values
        """
        return models.init(uri=self['dbname'], host=self['host'], user=self.user, passwd=self.passwd_hash, dbtype=self['dbtype'], path=self.args.dname)

    def load_config(self):
        """ Initialise database from config file.
            Create config file if it doesn't exist
        """
        if not os.path.exists(self.args.filename):
            log.info('No previous config file <%s>. Set all to default.' % self.args.bname)
            local_defaults = self.create_default_config()
            self.save_config(local_defaults)
            
        local_defaults = DEFAULTS
        with open(self.args.filename, 'r') as fh:
            for line in fh:
                src = '<%s> file' % self.args.bname

                # Skip config file comments
                if line.startswith('#'):
                    continue

                # Parse key value pair: return string blank if value is nothin
                try:
                    key, value = line.strip().split('\t')
                    key = key.lower().strip()
                except ValueError:
                    key = line.strip()
                    value = ""

                # Type bool switches read from file
                if key in ['set', 'force']:
                    value = True if value.lower() == 'true' else False
                    
                try:
                    # Return command line arg for key.  It will override file value.
                    cli_arg = self.parse_arg(key)
                    # If key is passwd, encode the command line value
                    if key == 'passwd' and cli_arg:
                        cli_arg = self.passwd_encode
                        
                    # print '*key:%s\tfile:%s\tcli:%s' % (key, value, cli_arg)
                    if cli_arg and self.args.force and value != cli_arg:
                        src = 'command line'
                        value = cli_arg
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
                # not allowed to save override param as True
                if key == 'force':
                    value = False
                    
                line = '\t'.join([key, str(value)]) + '\n'
                if self.args.save:
                    log.info("Update <%s> config file: %s = %s" %(self.args.bname, key, value))
                fh.write(line)

    def validate_args(self):
        """ Ensure session args are valid
            1) filename exists
            2) database access credentials are sensible
        """
        if self.args.load and not self.args.force:
            if not self.args.bname == FNAME and not os.path.exists(self.args.filename):
                raise OSError, (
                    "%s custom config file could not be found. Check path names" % self.args.filename)

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
            if key == 'passwd':
                cli_arg = self.passwd_encode

            if DEFAULTS[key] != cli_arg:
                txt,src = cli_arg if cli_arg else "<nothing>", "command line"
                local_defaults[key] = cli_arg
            else:
                txt,src = DEFAULTS[key] if DEFAULTS[key] else "<nothing>", "defaults"
            log.info("Initialized %s with %s from %s" % (key, txt, src))

        return local_defaults

    @property
    def passwd_encode(self):
        """ Encode string password
        """
        return base64.encodestring(self.parse_arg('passwd')).rstrip()

    @property
    def passwd_decode(self):
        """ Decode hashed password
        """
        return base64.decodestring(self['passwd'])

    @property
    def user(self):
        """ Return current user
        """
        return self['user']

    @property
    def passwd_hash(self):
        """ Return passwd hash
        """
        return self['passwd']


def get_file_paths(fname):
    dname = os.path.dirname(fname)
    bname = os.path.basename(fname)
    if not dname:
        dname = os.getcwd()
    return dname, bname

def setuser(args):
    """ Update database user and password access credentials
    """
    if not os.path.exists(args.filename):
        raise ConfigException, "%s config file not found" % args.filename

    print args
    
    args.load = True
    args.force = True
    args.save = False
    args.dbtype = None
    args.passwd = None
    args.host = None
    args.user = None
    args.dbname = None
    config = Config(args, True)

    if args.update_user:
        if config['user'] == args.oldvalue:
            session = config.get_session()
            params = session.query(models.Params).one()
            params.user = args.newvalue
            session.commit()
            session.close()
            
            log.info('Database username changed from %s to %s' % (config['user'], args.newvalue))
            config.settings['user'] = args.newvalue
            config.save_config(config.settings)
        else:
            log.error('Existing user names do not match.')
            
    if args.update_passwd:
        existing_pass = config.passwd_hash
        old_pass = base64.encodestring(args.oldvalue).rstrip()
        new_pass = base64.encodestring(args.newvalue).rstrip()

        if existing_pass == old_pass:
            session = config.get_session()
            params = session.query(models.Params).one()
            params.passwd = new_pass
            session.commit()
            session.close()

            log.info('Database password successfully updated')
            config.settings['passwd'] = new_pass
            config.save_config(config.settings)
        else:
            log.error('Existing passwords do not match.')
        
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
