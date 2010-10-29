"""
Defines slaves and their capabilities.

Some of the ideas here come from Buildbot's buildbot:
http://github.com/buildbot/metabbotcfg/blob/master/slaves.py.
"""

from buildbot.buildslave import BuildSlave
from unipath import FSPath as Path

class DjangoBuildSlave(BuildSlave):
    """
    Encapsulates the settings for a single slave (e.g. node).
    """
    
    # Which OS this slave runs. This is just for human descriptions, but should 
    # be fairly descriptive: "osx-10.6", "ubuntu-10.04", etc.
    os = None
    
    # A list of Python versions this slave supports. Entries in this list should
    # be the actual name (or even path to) the pythonX.Y binary. For example:
    # pythons = ['python2.5', '/usr/local/bin/python2.6']
    pythons = []
    
    # A list of databases this slave supports. Entries should be of the form
    # "postgres8.1", "mysql6.0", "sqlite3", etc. The exact format isn't a big
    # deal: these names are descriptive and just need to be human-readable.
    databases = []
    
    # By default, this slave will test against each (python, db) combination.
    # To skip one, stuff it in the skip list (as that (python, db) tuple).
    skip_configs = []
    
    # Django settings will be auto-generated with resonable defaults for each
    # combination. If they don't work, they can be overridden in this dict. Keys
    # in the dict are keys matching entries self.python, or matching entries in
    # self.databases, or (python, db) keys. The values should be a complete
    # settings file as a string.
    settings_overrides = {}
    
    def __init__(self, name, **kwargs):
        # Set attrs on self from **kwargs, leaving behind any kwargs to pass on
        # to the base BuildSlave.
        for k in kwargs.keys():
            if hasattr(self, k):
                setattr(self, k, kwargs.pop(k))

        # Load a password based on the name.
        # XXX Read this from a DB?
        passwordfile = Path(__file__).ancestor(2).child("passwords", "%s.pass" % name)
        password = passwordfile.read_file().strip()
        BuildSlave.__init__(self, name, password, **kwargs)
    
    def get_settings(self, python, database):
        """
        Return overriden settings if given, or None to use the defaults.
        
        XXX Move settings generation in here perhaps?
        """
        if (python, database) in self.settings_overrides:
            return self.settings_overrides[(python, database)]
        elif database in self.settings_overrides:
            return self.settings_overrides[database]
        elif python in self.settings_overrides:
            return self.settings_overrides[python]
        else:
            return None
    
slaves = [
    DjangoBuildSlave('local',
        os = 'osx-10.6',
        pythons = ['python2.4', 'python2.5', 'python2.6'],
        databases = ['sqlite3.6.12', 'postgresql9.0.0'],
        max_builds = 1,
    ),
    # DjangoBuildSlave('bs1.jacobian.org',
    #     os = 'ubuntu-9.10',
    #     pythons = ['python2.4', 'python2.5', 'python2.6'],
    #     databases = ['sqlite3'],
    #     max_builds = 1,
    # ),
    # DjangoBuildSlave('bs2.jacobian.org',
    #     os = 'ubuntu-10.04',
    #     pythons = ['python2.6'],
    #     databases = ['postgresql8.4']
    #     max_builds = 1,
    # )
]