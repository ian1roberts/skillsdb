"""
Database views
"""
import sys
import os
import sqlalchemy as sql
import datetime

import utils
import config
import models

CONDITIONS = {'OR':sql.or_, 'AND':sql.and_, 'NOT':sql.not_,
              'startswith':'startswith', 'equals':'equals', 'contains':'contains',
              'like':'like'}

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

class ViewError(Exception):pass
        
class View(object):
    """ Dispatch database command
    """
    def __init__(self, args):
        """ Instantiate view and dispatch database command

        Support CRUD views, operating on given table
        --child
        --freetime
        --parent
        --skill
        --address

        --add, require PID except parent
        --delete, modify, require RID
        --search, special syntax

        operations: get table, get operation, parse input, execute

        """
        self.args = args

        table = self.get_table_object()
        operation = self.get_operation()
        input_dict = self.get_input(table, operation)

        self.validate_cla(table, operation, input_dict)
        self.session_config = self.load_session(self.args.config)
        
        operation(table=table, input_dict=input_dict)

    def get_table_object(self,):
        """
        Return working table
        """
        if self.args.parent:
            table =  "parent"
        elif self.args.child:
            table = "child"
        elif self.args.freetime:
            table = "freetime"
        elif self.args.skill:
            table = "skill"
        elif self.args.address:
            table = "address"
        else:
            raise ViewError, "Table not found"

        return {"parent":models.Parent, "child":models.Child,
                "freetime":models.Freetime, "skill":models.Skill,
                "address":models.Address}[table]

    def get_operation(self):
        """
        Return current operation
        """
        if self.args.add:
            op = 'create'
        elif self.args.delete:
            op = 'delete'
        elif self.args.search:
            op = 'retrieve'
        elif self.args.modify:
            op = 'update'
        else:
            raise ViewError, "Operation not recognized"

        return {"create":self.create_view, "delete":self.delete_view,
                "retrieve":self.retrieve_view,
                "update":self.update_view}[op]

    def validate_cla(self, table, operation, input_dict):
        """ Check input for consistency
        """
        # create record requires parent_id, except when creating parent
        def do_proc_name(table_name):
            if table_name.startswith("a"):
                return ("an", table_name)
            else:
                return ("a", table_name)
                
        if operation == self.create_view:
            if table == models.Parent and self.args.pid:
                raise ViewError, "Parent ID shouldn't be given when creating Parent"
            if not self.args.pid and not table == models.Parent:
                raise ViewError, "Parent ID is required when creating %s %s record" % (
                    do_proc_name(table.classname))
        if operation == self.retrieve_view:
            if self.args.pid or self.args.rid:
                raise ViewError, "Parent and record IDs shouldn't be given when doing a lookup"
        if operation == self.update_view or operation == self.delete_view:
            if not ((table == models.Parent and self.args.pid) or self.args.rid):
                raise ViewError, "Record ID (or parent ID for parents) required to update or delete records"
        if operation == self.delete_view:
            if table == models.Parent and not self.args.pid:
                raise ViewError, "Parent ID required to delete parent record"
            if table != models.Parent and self.args.pid:
                raise ViewError, "Parent ID irrelevent for deletion of %s records" % table.classname

        if self.args.pid and self.args.rid:
            raise ValueError, "Inconsistent command line arguments. --pid and --rid jointly specified."

        if not os.path.exists(self.args.config):
            raise ViewError, "%s configuration file not found" % os.path.basename(self.args.config)


    def load_session(self, config_fname):
        params = utils.Params(config_fname, load=True)
        return config.Config(params)
        
    def get_input(self, table, operation):
        """ Parse free text input.
            Context specific
        """
        # Delete mode shouldn't have input string
        if operation == self.delete_view:
            if self.args.input:
                raise ViewError, "Input is invalid for delete mode. use --rid to specify a record"
            return {}

        # Build list of valid key names
        valid_keys = table().get_attrs()

        print 'valid_keys'
        print valid_keys
        print 'input'
        print self.args.input
        
        if not self.args.input:
            raise ViewError, "No input data to parse"

        # retrieve: key dict --> key=value,op COND
        # others: key dict --> key=value
        if operation in [self.create_view, self.update_view]:
            return self.get_input_general(self.args.input, valid_keys, table)
        elif operation.viewref == 'retrieve':
            return self.get_input_retrieve(self.args.input, valid_keys, table)
        else:
            raise ViewError, 'Something gone wrong table:%s, operation:%, input:%s' % (
                table, operation, self.args.input)

    def get_input_general(self, txt, valid_keys, table):
        """ Parse input for add,update
        """
        key_dict = {}

        for kvpair in txt:
            if "=" not in kvpair:
                raise ViewError, "Incorrect format:%s. Use key=value for data entry." % kvpair
            sepcount = sum([1 for i in kvpair if i =='='])
            if sepcount != 1:
                raise ViewError, "Multiple separators:%s, can not resolve key value pair." % kvpair

            key, value = kvpair.split('=')
            if key not in valid_keys:
                raise ViewError, "'%s' is not a valid key for table '%s'" % (
                    key, table.classname
                )

            if key == 'record':
                try:
                    value = int(value)
                except ValueError:
                    print "%s is not a valid record ID" % value

            if key in ['am_start', 'am_end', 'pm_start', 'pm_end']:
                value = format_time(value)
                    
            key_dict[key]=value

        return key_dict
        
    def get_input_retrieve(self, txt, valid_keys, table):
        """ Parse input for query mode
        """
        query_builder = []
        while txt:
            expr = txt.pop()

            if expr in CONDITIONS:
                query_builder.append(CONDITIONS[expr])
                continue

            if not ('=' in expr and ',' in expr):
                raise ViewError, "%s is not a valid query expression" % expr
            term_count = sum(1 for i in expr if i=="=")
            cond_count = sum(1 for i in expr if i==',')

            if not (term_count == 1 and cond_count == 1):
                raise ViewError, "%s is not a valid query expression. Specify key=term,operation." % expr

            cond,term_part = expr.split(',')
            key,value = term_part.split('=')

            if cond not in CONDITIONS:
                raise ViewError, "%s is not a valid query expression. %s is not a recognized operator.  Choose from %" % (expr, cond, CONDITIONS)

            if key not in valid_keys:
                raise ViewError, "'%s' is not a valid key for table '%s'" % (
                    key, table.classname
                )     
                
            if key in ['am_start', 'am_end', 'pm_start', 'pm_end']:
                value = format_time(value)
                    
            query_builder.append({key:(value, CONDITIONS[cond])})

        return query_builder

    def create_view(self, **kwargs):
        """ Create a new record
        """        
        session, table_object, params = self.parse_objects(**kwargs)
        print '**PARAMS'
        print params
        
        record = table_object(**params)
        session.add(record)
        session.commit()
        session.close()
        
    def delete_view(self, **kwargs):
        """ Delete a record by parent_id and record id
        """        
        session, table_object, params = self.parse_objects(**kwargs)
        if not table_object == models.Parent:
            q = session.query(table_object).filter(
                table_object.id == params['record_id']).one()
        else:
            q = session.query(models.Parent).filter(
                models.Parent.id == params['parent_id']).one()

        session.delete(q)
        session.commit()
        session.close()
        

    def retrieve_view(self, **kwargs):
        """ Perform a lookup
        """
        print kwargs
        
    def update_view(self, **kwargs):
        """ Modify a record
        """
        session, table_object, params = self.parse_objects(**kwargs)
        print '*PARAMS:'
        print params
        
        if not table_object == models.Parent:
            q = session.query(table_object).filter(
                table_object.id == params['record_id']).one()
        else:
            q = session.query(models.Parent).filter(
                models.Parent.id == params['pid']).one()

        for k,v in params.iteritems():
            if k == 'pid':
                continue
            setattr(q, k, v)

        session.commit()
        session.close()
        
    def parse_objects(self, **kwargs):
        """ Post parse key value pair arguments
            Fix up parent ID and record ID if specified

            Note parent tables have a primary id and a parent_id key.
            if table is *NOT* parent, then parent_id == pid
        """
        session =  self.session_config.get_session()
        table_object = kwargs['table']
        params = kwargs['input_dict']

        if self.args.pid:
            try:
                pid = int(self.args.pid)
            except ValueError, e:
                print e
                print 'Incorrectly formatted parent id:%s' % self.args.pid

            if ('parent_id' in params) or table_object == models.Parent:
                params['pid'] = pid
            else:
                params['parent_id'] = pid

        if self.args.rid:
            try:
                rid = int(self.args.rid)
            except ValueError, e:
                raise ViewError, "%s is an invalid Record ID" % self.args.rid

            if table_object != models.Parent:
                params['record_id'] = rid
            else:
                params['pid'] = rid
                
        return (session, table_object, params)

def format_time(timestr):
    if ':' not in timestr or 4 < len(timestr) > 5:
        raise ValueError, 'Input times must be hh:mm format'

    #datetime.datetime.combine(datetime.datetime.today().date(), datetime.time(9,0))
    today = datetime.datetime.today().date()
    
    h,m = timestr.split(':')
    try:
        return datetime.datetime.combine(today, datetime.time(int(h), int(m)))
    except ValueError, e:
        print "%s\n%s hours, %s mins incorrectly formatted" % (e, h, m)
    
def main(args):
    """
Add, delete, modify or search skills database.
    
  Select one of parent, child, skill, freetime or address tables.
  Record creation requires a parent identifier (--pid) with the exception of "add parent".
  Record deletion and modification requires a record identifier (--rid), which may be
  discovered via searching, if not already known.
    
  A configuration file is required.  If not explicitly given (--config), a default config.cfg will
  be assumed in the current working directory.

  For addition and update operations, Input should be specified in the form of key=value.
  Multiple inputs are parsed on whitespace.

  Search operations should be specified in key=value,operator=term, where terms may be one
  of equals, startswith, contains or like. Queries may be built using conditional operators:
  AND, OR and NOT 

  skillsdb manage --add --parent first_name=Ian second_name=Roberts
  skillsdb manage --modify --parent --pid 1 first_name=Bob
  skillsdb manage --search --parent first_name=Ian,op=startswith AND second_name=Roberts,op=equals
  skillsdb manage --delete --parent --pid 1
    """
    sys.exit(View(args))
