"""
Individual custom build steps for the Django tests.

See the docstring in builders.py for an overview of how these all fit together.

I'm using subclasses (instead of just passing arguments) since it makes the
overall build factor easier to read.
"""

import textwrap
from buildbot.steps.source import SVN
from buildbot.steps.shell import Test, ShellCommand
from buildbot.steps.transfer import FileDownload, StringDownload

class DjangoSVN(SVN):
    """
    Checks Django out of SVN.
    
    Django uses a slightly weird branch scheme; this calculates the rght branch
    URL from a simple branch name.
    """
    name = 'svn checkout'
    
    def __init__(self, branch):
        if branch == 'trunk':
            svnurl = 'http://code.djangoproject.com/svn/django/trunk'
        else:
            svnurl = 'http://code.djangoproject.com/svn/django/branches/releases/%s' % branch
        SVN.__init__(self, svnurl)
        
class DownloadVirtualenv(FileDownload):
    """
    Downloads virtualenv from the master to the slave.
    """
    name = 'virtualenv download'
    
    def __init__(self):
        FileDownload.__init__(self,
            mastersrc = 'virtualenv.py',
            slavedest = 'virtualenv.py',
            flunkOnFailure = True,
        )

class UpdateVirtualenv(ShellCommand):
    """
    Updates (or creates) the virtualenv, installing dependencies as needed.
    """
    
    name = 'virtualenv setup'
    flunkOnFailure = True
    haltOnFailure = True
    
    def __init__(self, python, db):
        commands = [
            r'PYTHON=%s;' % python,
            r'VENV=../venv-%s-%s;' % (python, db),
            
            # Create or update the virtualenv
            r'$PYTHON virtualenv.py --distribute --no-site-packages $VENV || exit 1;',

            # Reset $PYTHON and $PIP to the venv python
            r'$PYTHON=$PWD/$VENV/bin/python;',
            r'$PIP=$PWD/$VENV/bin/pip;',
        ]
        
        # Commands to install database dependencies if needed.
        if db.startswith('sqlite'):
            commands.extend([
                r"$PYTHON -c 'import sqlite3, sys; assert sys.version_info >= (2,6)' 2>/dev/null || ",
                r"$PYTHON -c 'import pysqlite2.dbapi2' ||",
                r"$PIP install pysqlite || exit 1;",
            ])
        elif db.startswith('postgres'):
            commands.append("$PYTHON -c 'import psycopg2' 2>/dev/null || $PIP install psycopg2==2.2.2 || exit 1")
        elif db.startswith('mysql'):
            commands.append("$PYTHON -c 'import MySQLdb' 2>/dev/null || $PIP install MySQL-python==1.2.3 || exit 1")
        else:
            raise ValueError("Bad DB: %r" % db)
            
        ShellCommand.__init__(self, command="\n".join(commands))
        
class GenerateSettings(StringDownload):
    """
    Generates a testsettings.py on the server.
    """
    name = 'generate settings'
    
    def __init__(self, python, db, settings):
        if settings is None:
            if db.startswith('sqlite'):
                settings = self.get_sqlite_settings()
            elif db.startswith('postgres'):
                settings = self.get_postgres_settings()
            elif db.startswith('mysql'):
                settings = self.get_mysql_settings()
            else:
                raise ValueError("Bad DB: %r")
        
        StringDownload.__init__(self, s=settings, slavedest='testsettings.py')
    
    def get_sqlite_settings(self):
        return textwrap.dedent('''
            import os
            DATABASES = {
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3'
                },
                'other': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'TEST_NAME': 'other_db_%s' % os.getpid(),
                }
            }
        ''')
        
    def get_postgres_settings(self):
        return textwrap.dedent('''
            import os
            DATABASES = {
                'default': {
                    'ENGINE': 'django.db.backends.postgresql_psycopg2',
                    'NAME': 'django_buildslave',
                    'HOST': 'localhost',
                    'USER': 'django_buildslave',
                    'PASSWORD': 'django_buildslave',
                    'TEST_NAME': 'django_buildslave_%s' % os.getpid(),
                },
                'other': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'TEST_NAME': 'other_db_%s' % os.getpid(),
                }
            }
        ''')
    
    def get_mysql_settings(self):
        return textwrap.dedent('''
            import os
            DATABASES = {
                'default': {
                    'ENGINE': 'django.db.backends.mysql',
                    'NAME': 'django_buildslave',
                    'HOST': 'localhost',
                    'USER': 'django_buildslave',
                    'PASSWORD': 'django_buildslave',
                    'TEST_NAME': 'django_buildslave_%s' % os.getpid(),
                },
                'other': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'TEST_NAME': 'other_db_%s' % os.getpid(),
                }
            }
        ''')
    
class TestDjango(Test):
    """
    Runs Django's tests.
    """
    name = 'test'
    
    def __init__(self, python, db, verbosity=2):
        Test.__init__(self,
            command = [
                '$PWD/../venv-%s-%s/bin/python' % (python, db),
                'tests/runtests.py',
                '--settings=testsettings',
                '--verbosity=%s' % verbosity
            ],
            env = {
                'PYTHONPATH': '$PWD:$PWD/tests'
            }
        )