"""
Object relational mapping configuration - Declarative
=====================================================
"""
import base64
import datetime


from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy import (Table, Column, Integer, String, ForeignKey,
                        DateTime, Time)
from sqlalchemy.pool import NullPool
import sqlalchemy as sa

metadata = sa.MetaData()
Base = declarative_base(metadata=metadata)
TODAY = datetime.datetime.today().date()
TIME_AM_START = datetime.datetime.combine(TODAY, datetime.time(9, 0))
TIME_AM_END = datetime.datetime.combine(TODAY, datetime.time(12, 0))
TIME_PM_START = datetime.datetime.combine(TODAY, datetime.time(13, 0))
TIME_PM_END = datetime.datetime.combine(TODAY, datetime.time(17, 0))

# parent <--> skill :: many to many relationship  interim table
parent_skill = Table('parent_skill', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('parent_id', Integer, ForeignKey('parent.id')),
        Column('skill_id', Integer, ForeignKey('skill.id'))
)

# parent <--> freetime :: many to many relationship  interim table
parent_freetime = Table('parent_freetime', Base.metadata,
        Column('id', Integer, primary_key=True),               
        Column('parent_id', Integer, ForeignKey('parent.id')),
        Column('freetime_id', Integer, ForeignKey('freetime.id'))
)

# parent <--> child :: many to many relationship  interim table
parent_child = Table('parent_child', Base.metadata,
        Column('id', Integer, primary_key=True),            
        Column('parent_id', Integer, ForeignKey('parent.id')),
        Column('child_id', Integer, ForeignKey('child.id'))
)

# Generic objects
#================
class DbMixin(object):
    """ Generic declarative model object properties
    """
    @declared_attr
    def __tablename__(cls):
        """ Derive lowercase tablename from class name
        """
        return cls.__name__.lower()

    __table_args__ = {'mysql_engine': 'InnoDB'}
    __mapper_args__= {'always_refresh': True}

    created = Column(DateTime, default=datetime.datetime.now())

    def __repr__(self):
        return "%s" % self.__class__

    def __str__(self):
        return "%r, (%s)" % (self, self.id)
        
    def get_attrs(self):
        item = sa.inspect(self)
        return item.attrs.keys()
        
    @declared_attr
    def classname(cls):
        return cls.__name__.lower()

class PersonMixin(object):
    """ Attributes for a generic person object (parent / child)
    """
    first_name = Column(String(50))
    second_name = Column(String(50))

    def __str__(self):
        return "%r %s" % (self, self.full_name)

    @property
    def full_name(self):
        return self.first_name + ' ' + self.second_name

class RefParentMixin(object):
    """ All classes need a parent ID for relationship refs.
    """
    @declared_attr
    def parent_id(cls):
        return Column('parent_id', ForeignKey('parent.id'))

   
#===========================
# Application defined models
#===========================
class Params(DbMixin, Base):
    """ Store database parameters in database
    """
    id = Column(Integer, primary_key=True)
    user = Column(String(50))
    passwd = Column(String(50))

class Skill(DbMixin, RefParentMixin, Base):
    """ Skill of parent
    """
    id =  Column(Integer, primary_key=True)
    name = Column(String(100))
    parents = relationship('Parent', secondary=parent_skill, backref='skills')
    
class Freetime(DbMixin, RefParentMixin, Base):
    """ Time when parent is available
    """
    id =  Column(Integer, primary_key=True)
    day = Column(String(12))
    am_start = Column(DateTime, default=TIME_AM_START)
    am_end = Column(DateTime, default=TIME_AM_END)
    pm_start = Column(DateTime, default=TIME_PM_START)
    pm_end = Column(DateTime, default=TIME_PM_END)
    parents = relationship('Parent', secondary=parent_freetime, backref='freetimes')

    def get_duration(self, start, end):
        """ Return am, pm, day availability as determined by
        """
        if start and end and end > start:
            return end - start

        return 0
            
    @property
    def get_period(self):
        am = self.get_duration(self.am_start, self.am_end)
        pm = self.get_duration(self.pm_start, self.pm_end)

        if am and pm:
            return 'Day'
        if am:
            return 'AM'
        if pm:
            return 'PM'
        return 'NA'
        
class Parent(PersonMixin, RefParentMixin, DbMixin, Base):
    """ Parent object
    """
    id =  Column(Integer, primary_key=True)
    partner = relationship('Parent', uselist=False, remote_side=[id],
                           backref=backref('other', uselist=False))

class Address(DbMixin, RefParentMixin, Base):
    """ Resedential address of a Parent
    """
    id =  Column(Integer, primary_key=True)
    line01 = Column(String(50))
    line02 = Column(String(50))
    village = Column(String(50))
    city = Column(String(50))
    postcode = Column(String(50))
    country = Column(String(50), default='UK')

    home_telephone = Column(String(50))
    mobile_telephone = Column(String(50))
    other_telephone = Column(String(50))
    home_email = Column(String(100))
    work_email = Column(String(100))
    other_email = Column(String(100))

    parent = relationship('Parent', uselist=False, backref=backref('address', uselist=False))

    def __str__(self,):
        return '\n'.join(map(str,[self.line01, self.line02, self.village,
                          self.city, self.postcode, self.country]))

class Child(PersonMixin, RefParentMixin, DbMixin, Base):
    """ Child object
    """
    id =  Column(Integer, primary_key=True)
    
    parents = relationship('Parent', secondary=parent_child, backref='children')
    
##===================
## Database functions
##===================
CONNECTORS = {'mysql':'mysql://', 'sqlite':'sqlite:///'}
def init(uri, **kwargs):
    """ Initialize connection to database or create new
        Determine appropriate interpreters given input
        Defaults to local sqlite database
    """
    path = kwargs['path']
    dbtype = kwargs['dbtype']
    user = kwargs['user']

    passwd =  kwargs['passwd']
    host = kwargs['host']
    if dbtype == 'mysql':
        passwd =  base64.decodestring(kwargs['passwd']).rstrip()
        if not host:
            host = 'localhost'
            
    midstring = user + ':' + passwd + '@' + host
    
    if type(uri) != type('string'):
        engine = sa.create_engine(uri.db_con_string, poolclass=NullPool)
        
    else:
        begstring = CONNECTORS[dbtype]
        dburl = begstring + midstring
        
        if dbtype == 'sqlite':
            dburl = begstring + path + '/' + uri
        else:
            dburl = dburl + '/' + uri

    engine = sa.create_engine(dburl, echo=False, poolclass=NullPool)
    metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def drop_db(x, host='beast', user='ir210', passwd='', dbtype='mysql', echo=False):
    """ Drop the database and start again
    """
    if dbtype == "mysql":
        engine = sa.create_engine('mysql://' + user + ':' + passwd + '@' + host + '/' + x, poolclass=NullPool)
        metadata.drop_all(engine)   

##===============================
## Pre unit-test build behaviour
##===============================
if __name__ == '__main__':

    session = init('skillsdb.sqlite')

    a = Address(line01='1, Rock House', line02='The Trees', village='Balsham',
    city='Cambridge', postcode='CB21 4EE')
    
    p1 = Parent(first_name='Fred', second_name='Flintstone')
    p2 = Parent(first_name='Wilma', second_name='Flintstone')
    p1.partner = p2
    p1.address = a
    c = Child(first_name='Tiny', second_name='Flintstone')
    c.parents = [p1, p2]
    session.add(c)
    session.commit()

    print 'parent 1 -->', p1
    print 'parent 2 -->', p2

    print 'parent 1 - partner (wilma) -->', p1.partner
    print 'parent 2 - partner (fred) -->', p2.other
    print 'parent 1 - partner other (none -->', p1.other
    print 'parent 2 - partner other (none) -->', p2.partner
""" When p1.partner is set to p2, p1.partner is forced to be wilma
    This implies that p1.other is nothing, as only one partner is allowed
    This implies that p2.other is fred, as this 'other is the inverse of partner, the backref'
    
"""

