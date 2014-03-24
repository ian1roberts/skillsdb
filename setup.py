from setuptools import setup

setup(
    name='skillsdb',
    version='0.1.0',
    author='Ian Roberts',
    author_email='ian.roberts@cantab.net',
    packages=['skillsdb', 'skillsdb.test'],
    scripts=['bin/skillsdb'],
    url='https://redmine.popgentech.com/projects/getfs',
    license='LICENSE',
    description='Manage people skills in a database',
    long_description=open('README.md').read(),
    requires=[
        "sqlalchemy",
    ],
)
