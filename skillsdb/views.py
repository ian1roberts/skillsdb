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
              'equals':'==', 'like':'.like(', 'not':'!='}

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
            if not (((table == models.Parent or table == models.Address) and self.args.pid) or self.args.rid):
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
        elif operation == self.retrieve_view:
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

            term_part,cond = expr.split(',')
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
        record = self.decorate_create_update('create', session, table_object, params)

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
        results = None
        kwargs['_search_'] = True
        session, table_object, terms = self.parse_objects(**kwargs)
        print terms
        
        table_object = "models." + table_object.classname.capitalize()
        filter_units = []
        qtxt = 'session.query(' + table_object + ').filter('
        cond_units = [qtxt]
        i = 0
        while terms:
            term = terms.pop()
            if type(term) == type(sql.and_):
                cond_units.append('sql.' + term.__name__ + '(' + filter_units[i -1])
                i +=1
                continue
                
            key, value_op = term.items()[0]
            value,op = value_op
            filter_units.append(fmt_term(table_object, key, value, op))

        cond_units.append(filter_units[i])

        xb = ''
        if i:
            xb = ')' * i
        qtxt = cond_units[0]
        if i > 0:
            qtxt += ','.join(cond_units[1:])
        else:
            qtxt += ''.join(cond_units[1])
        qtxt += xb + ').all()'

        print qtxt
        results = eval(qtxt)
        if results:
            for i, result in enumerate(results):
                print "Result:%s\n\tRID:%s\n\t%s\n" % (1+i, result.id, result)
        
    def update_view(self, **kwargs):
        """ Modify a record
        """
        session, table_object, params = self.parse_objects(**kwargs)
        record = self.decorate_create_update('update', session, table_object, params)

        session.merge(record)
        session.commit()
        session.close()

    def decorate_create_update(self, operation, session, table_object, params):
        """ Attach parent and parent.partner to new
            and updated records

            Bit hacky around Address table, and the way
            parent_id --pid and --rid are used for Parent tables
        """
        #print '*Params'
        #print params
        partner = None
        parent = None
        if 'parent_id' in params:
            parent_id = params['parent_id']
            parent = session.query(models.Parent).filter(models.Parent.id == parent_id).one()

        if parent:
            if parent.partner:
                partner = parent.partner
            elif parent.other:
                partner = parent.other

        # Create new record
        if operation == 'create':
            record = table_object(**params)
        else:
            # Process Update requests
            # All updates apart from Address use record_id for lookups
            # Note pid -> record_id 
            if table_object != models.Address:
                record = session.query(table_object).filter(
                    table_object.id==params['record_id']).one()
            else:
                if parent:
                    record = session.query(table_object).filter(
                        table_object.parent_id==params['parent_id']).one()
                else:
                    record = session.query(table_object).filter(
                        table_object.id==params['record_id']).one()
                    
        # Parent table => add partner if present            
        if table_object == models.Parent:
            if parent:
                record.partner = parent
                
        # Child table => add parents
        elif table_object == models.Child:
            if parent and partner:
                record.parents = [parent, partner]
            elif parent:
                record.parents = [parent]
            # debug
            print record.parents

        # Skills and freetime, add owner
        elif table_object in [models.Skill, models.Freetime]:
            if parent:
                record.parents = [parent]
        elif table_object == models.Address:
            pass
        else:
            raise ViewError, "Something gone wrong"

        # Update any other parameters
        for key, value in params.iteritems():
            if key in ['pid', 'record_id', 'parent_id']:
                continue
            setattr(record, key, value)

        print record
        return record

        
    def parse_objects(self, **kwargs):
        """ Post parse key value pair arguments
            Fix up parent ID and record ID if specified

            Note parent tables have a primary id and a parent_id key.
            if table is *NOT* parent, then parent_id == pid

            if updating a parent, user may specif --rid or --pid for parent
        """
        session =  self.session_config.get_session()
        table_object = kwargs['table']
        params = kwargs['input_dict']

        if '_search_' in kwargs:
            del kwargs['_search_']
            return (session, table_object, params)

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

            # Hack for update parent where, where user used --pid
            # rather than --rid
            if (table_object == models.Parent or table_object == models.Address
            ) and 'record_id' not in params:
                params['record_id'] = pid

        if self.args.rid:
            try:
                rid = int(self.args.rid)
            except ValueError, e:
                raise ViewError, "%s is an invalid Record ID" % self.args.rid

            # Hack for update parent view, where user has used --rid
            # rather than --pid (note --pid + --rid is invalid)
            params['record_id'] = rid
            if table_object != models.Parent:
                params['pid'] = rid
                
        return (session, table_object, params)
        
def fmt_term(table_object, key, value, op):
    # equals / not equals
    if op == '==' or op == '!=':
        return table_object + '.' + key + op + '\'' + value + '\''
    # like
    elif op == '.like(':
        return table_object + '.' + key + op + '\'%' + value + '%\')'
    else:
        raise ViewError, "Unsupported query operator"
                
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
  To define a relationship between two parents, use key=value of parent_id=`pid of partner`
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


if __name__ == '__main__':
    from utils import Params
    
    fn = '/home/ian/dev/python/skillsdb/skillsdb/config.cfg'
    p = Params(fn, load=True)
    x = config.Config(p)
    s = x.get_session()

    # Parent child : method 1
    p1 = models.Parent(first_name="Joe", second_name="Blogs")
    p2 = models.Parent(first_name="Jane", second_name="Blogs")
    p1.partner = p2 # use `other` to get related parent
    c1 = models.Child(first_name="Jack", second_name="Blogs")
    c1.parents = [p1, p2]
    s.add(c1)
    s.commit()
    s.close()
    
    # Parent child : method 2
    p3 = models.Parent(first_name="Ian", second_name="Roberts")
    p4 = models.Parent(first_name="Suet-Feung", second_name="Chin")
    p3.partner = p4 # use `other` to get related parent
    c = models.Child(first_name="Matthew", second_name="Roberts")
    p3.children = [c]
    p4.children = [c]
    s.add(p3)
    s.commit()
    s.close()

    # DB introspect
    # method 1
    q = s.query(models.Parent).filter(models.Parent.id==1).one()
    print q
    print q.other

    print q.children[0]
    print q.other.children[0]

    # method 2
    q = s.query(models.Parent).filter(models.Parent.id==3).one()
    print q
    print q.other

    print q.children[0]
    print q.other.children[0]
