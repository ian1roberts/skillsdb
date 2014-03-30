skillsdb
========
A simple database driven program to manage people and their skills

Specification
-------------
Provide a database program that stores parent's skill sets and freetime so that
schools may identify helpers to support school activities.  Database
should store parent details such as home address, child relationship,
free times and skills.  Program should have a simple query interface,
portable and be readily customizable.

Design
------
Split in 3 parts

1. configuration subsystem
2. database models
3. user interface

Configuration
-------------
Provide simple unified interface for generic
configuration. Configurations may be loaded from / saved to a  config
file.  Command line options override settings loaded from file when
*--force'ed*.  Overridden loaded settings _do not_ persist unless a
*--save* is selected.

Supports sqlite and mysql through SQLalchemy connectors::

        (pytest) skillsdb config -h
        usage: skillsdb config [-h] (--load | --save) [--force] [--user USER]
                       [--passwd PASSWD] [--host HOST] [--dbtype DBTYPE]
                       [--dbname DBNAME]
                       [filename]
                       
Records may be created, retrieved, updated and deleted according to
usual expectations.

Typical innvocation::

        usage: skillsdb manage [-h] [--id ID] (--add | --delete | --modify | --search)
                       [--parent | --child | --skill | --freetime | --address]
                       ...

        Parse input command and dispatch

        positional arguments:
          input         Field data string

        optional arguments:
          --id ID       Record ID
          --add, -A     Add a record
          --delete, -D  Delete a record
          --modify, -M  Modify a record
          --search, -S  Search for a record
          --parent      Work on parent table
          --child       Work on child table
          --skill       Work on skill table
          --freetime    Work on freetime table
          --address     Work on address table

Of course, none of this is wired up yet!
