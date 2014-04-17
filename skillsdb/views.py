"""
Database views
"""
import sys
import os

import utils
import config
import models

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

        Support CRUD views, operating on given table (XOR)
        --child
        --freetime
        --parent
        --skill

        Operations are XOR
        --delete, --modify require a parent ID
        --add, --search do not require a parent ID

        Freetext input parsing is context specific
        --add -> split remainder on space and `=`, no parent ID on parent table
        --delete -> Delete table on parent ID
        --search -> search `table` on input, no parent ID
        --modify -> Modify `table` on parent ID, free text

        Addition of a parent is the only create not requiring a parent ID
        """
        self.args = args

        table = self.get_table_object()
        operation = self.get_operation()
        input_dict = self.get_input(table)

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
            if table == models.Parent and self.args.id:
                raise ViewError, "Parent ID shouldn't be given when creating Parent"
            elif not self.args.id and (table == models.Skill or table == models.Freetime or table == models.Child or table == models.Address):
                raise ViewError, "Parent ID is required when creating %s %s record" % (do_proc_name(table.classname))

        if operation == self.retrieve_view:
            if self.args.id:
                raise ViewError, "Parent ID shouldn't be given when doing a lookup"
        if operation == self.update_view or operation == self.delete_view:
            if not self.args.id:
                raise ViewError, "parent ID required to update records"

        if not os.path.exists(self.args.config):
            raise ViewError, "%s configuration file not found" % os.path.basename(self.args.config)


    def load_session(self, config_fname):
        params = utils.Params(config_fname, load=True)
        return config.Config(params)
        
    def get_input(self, table):
        """ Parse free text input.
            Context specific

        """
        valid_keys = table().get_attrs()
        if not self.args.input:
            raise ViewError, "No input data to parse"

        key_dict = {}
        for kvpair in self.args.input:
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

            key_dict[key]=value

        return key_dict
        
    def create_view(self, **kwargs):
        """ Create a new record
        """
        print kwargs
        session =  self.session_config.get_session()
        table_object = kwargs['table']
        params = kwargs['input_dict']
        record = table_object(**params)
        session.add(record)
        session.commit()
        session.close()
        
    def delete_view(self, **kwargs):
        """ Delete a record by parent_id
        """
        print kwargs

    def retrieve_view(self, **kwargs):
        """ Perform a lookup
        """
        print kwargs
        
    def update_view(self, **kwargs):
        """ Modify a record
        """
        print kwargs


def main(args):
    """ Parse input command and dispatch
    """
    sys.exit(View(args))
