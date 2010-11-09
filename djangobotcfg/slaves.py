"""
Defines slaves and their capabilities.

Some of the ideas here come from Buildbot's buildbot:
http://github.com/buildbot/metabbotcfg/blob/master/slaves.py.
"""

import json
from buildbot.buildslave import BuildSlave
from unipath import FSPath as Path
from .utils import parse_version_spec
from .rsc_slave import CloudserversLatentBuildslave

def get_slaves():
    """
    Get the list of slaves to insert into BuildmasterConfig['slaves'].
    """
    # Load Rackspace credentials.
    credfile = Path(__file__).ancestor(2).child("passwords", "cloudservers.json")
    creds = json.loads(credfile.read_file())
    
    return [
        DjangoCloudserversBuildSlave('bs1.jacobian.org',
            os = 'ubuntu-9.10',
            pythons = {'2.4': True, '2.5': True, '2.6': True},
            databases = ['sqlite3'],
            max_builds = 1,
            image = 'bs-ubuntu910-py24-py25-py26-sqlite',
            flavor = '256 server',
            cloudservers_username = creds['username'],
            cloudservers_apikey = creds['apikey'],
        ),
        DjangoCloudserversBuildSlave('bs2.jacobian.org',
            os = 'ubuntu-10.04',
            pythons = {'2.6': True},
            databases = ['postgresql8.4.5'],
            max_builds = 1,
            image = 'bs-ubuntu1004-py26-postgres845',
            flavor = '256 server',
            cloudservers_username = creds['username'],
            cloudservers_apikey = creds['apikey'],
        ),
    ]

class BaseDjangoBuildSlave(object):
    """
    Encapsulates the settings for a single slave (e.g. node).
    
    This is a mixin because it could be mixed into both the base BuildSlave and
    the a latent build slave (AWS or Cloudservers).
    """
    
    # Which OS this slave runs. This is just for human descriptions, but should 
    # be fairly descriptive: "osx-10.6", "ubuntu-10.04", etc.
    os = None
    
    # A dict showing which Python versions this slave supports. Keys should be
    # MAJOR.MINOR versions (e.g. "2.6", "2.5", etc.). Values may simply be True
    # to indicate that a binary named ``pythonX.Y`` is available, or may be
    # a string like ``python`` or ``/usr/local/bin/python2.7`` to indicate
    # what the Python binary of that name is called.
    #
    # For example::
    #
    #   pythons = {'2.6': True, '2.5': '/usr/local/bin/python2.5'}
    #
    pythons = {}
    
    # A list of databases this slave supports. Entries should be of the form
    # "postgres8.1", "mysql6.0", "sqlite3", etc. Use as many bits of the version
    # specifier as possible.
    databases = []
    
    # By default, this slave will test against each (python, db) combination.
    # To skip one, stuff it in the skip list (as that (python, db) tuple).
    # 
    # For example::
    #
    #       # We've Python 2.5, 2.6, and 2.7 available.
    #       pythons = {'2.5': True, '2.6': True, '2.7': True}
    #
    #       # And SQLite, and PostgreSQL...
    #       databases = ['sqlite3', 'postgresql8.4.1']
    #       
    #       # But we don't want to test the Python 2.5 / SQLite combo.
    #       skip_configs = [('2.5', 'sqlite3')]
    #
    # 
    skip_configs = []
    
    def extract_attrs(self, name, **kwargs):
        """
        Sets attrs on self from **kwargs, leaving behind any kwargs to pass on
        to the base BuildSlave.
        """
        for k in kwargs.keys():
            if hasattr(self, k):
                setattr(self, k, kwargs.pop(k))
        return kwargs
        
    def get_properties(self):
        """
        Get some build properties for this slave.

        This returns build properties for each Python version. This lets the
        actual build steps find the correct path for each Python binary.
        """
        properties = {}
        for pyversion, pypath in self.pythons.items():
            if isinstance(pypath, bool):
                pypath = "python%s" % pyversion
            properties['python%s' % pyversion] = pypath
        return properties
    
    def get_password(self, name):
        """
        Look up a password for the slave.
        
        This reads a password out of a file, and if it doesn't exist returns a
        poorly-obfuscated password instead. Really, how secure does this need to
        be?
        """
        passwordfile = Path(__file__).ancestor(2).child("passwords", name)
        if passwordfile.exists():
            return passwordfile.read_file().strip()
        else:
            return name.encode('rot13')
    
    def can_build(self, python, db):
        """
        Returns True if this slave can build the given python/db combo.
        
        This parses self.databases in the same way as
        `builders.generate_builders` does (using `utils.parse_version_spec`))
        """
        found_db = self.find_database(db)
        return python in self.pythons and found_db and (python, found_db) not in self.skip_configs
                
    def find_database(self, dbspec):
        """
        Find the netry in self.databases that most closely matches the
        given version spec.
        """
        for db in self.databases:
            if parse_version_spec(db) == dbspec:
                return db
        return None

#
# FIXME: this is ugly. Any way to fix it?
#

class DjangoBuildSlave(BaseDjangoBuildSlave, BuildSlave):
    def __init__(self, name, **kwargs):
        kwargs = self.extract_attrs(name, **kwargs)
        password = self.get_password(name)
        kwargs.setdefault('properties', {}).update(self.get_properties())
        BuildSlave.__init__(self, name, password, **kwargs)
        
class DjangoCloudserversBuildSlave(BaseDjangoBuildSlave, CloudserversLatentBuildslave):
    def __init__(self, name, **kwargs):
        kwargs = self.extract_attrs(name, **kwargs)
        password = self.get_password(name)
        kwargs.setdefault('properties', {}).update(self.get_properties())
        
        # The slave's set up to read hostname and password from the slave's
        # "info" directory, which is cool beaause it means we can re-use
        # the same image for multiple slaves. But we need a different name
        # for each, so do a bit of magic with the API here.
        kwargs.setdefault('files', {}).update({
                '/home/buildslave/slave/buildslave/info/host': '%s\n' % name,
                '/home/buildslave/slave/buildslave/info/password': '%s\n' % password,
        })
        
        CloudserversLatentBuildslave.__init__(self, name, password, **kwargs)
