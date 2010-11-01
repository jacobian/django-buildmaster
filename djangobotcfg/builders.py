"""
Actual build definitions.

This is kinda complex, so here's a high-level overview of exactly how the build
process works:

The main point is to assume as little as possible about the build slave (and
thus transfer as much smartsfrom the master to the slave as possible). The slave
just needs to assure that Python is installed, a database is accessible (according
to the slave config), and whatever headers needed to build database modules exist.

The steps, then, are:

    * Make the SVN checkout of Django.
    
    * Transfer virtualenv.py from the master to the slave.
    
    * Create a virtualenv sandbox and install any extra prereqs (database
      modules, really).
      
    * Generate a Django settings file from the slave config.
    
    * Run Django's test suite using that settings file.

This sandbox is shared for each (python, database) combination; this prevents
needing to build the database wrappers each time.

However, this *does* mean that we can't test installing Django (via setup.py
install or friends) and that the tests pass against the *installed* files (which
hasn't always been true in the past). If we did, and if a buildslave wanted
to run multuple builds in parallel, we'd get conflicts. Also, if we install
the recommended way (setup.py install), then we can't uninstall easily.

So that's a big FIXME for later. Perhaps there's a clever way to have a new
virtualenv for each build but still avoid re-building database bindings...
"""

import itertools
from buildbot.config import BuilderConfig
from buildbot.process.factory import BuildFactory
from . import buildsteps
from .utils import parse_version_spec
    
def get_builders(branches, slaves):
    """
    Gets a list of builders for entry in BuildmasterConfig['builders']
    
    Creates a builder for each (branch, python, database) combination.
    """
    builders = []
    
    # Figure out the superset of pythons and databases to test against. Since DB
    # entries are as specific as possible ('postgresql8.3.1') there's some munging
    # that needs to happen get the exact correct subset.

    all_dbs = set()
    all_pythons = set()
    for slave in slaves:
        all_dbs.update(parse_version_spec(db) for db in slave.databases)
        all_pythons.update(k for k in slave.pythons if slave.pythons[k])
    
    # Now create a builder for each (branch, python, database) combo.
    combos = itertools.product(branches, all_pythons, all_dbs)
    for (branch, python, database) in combos:
        # Figure out which slaves can run this combo by asking the slave.
        builder_slaves = [slave for slave in slaves if slave.can_build(python, database)]
        
        # If none can we have to skip this combo.
        if not builder_slaves:
            continue
        
        # Make a builder config for this combo.
        builders.append(BuilderConfig(
            name = '%s-%s-%s%s' % (branch, python, database.name, database.version),
            factory = make_factory(branch, python, database),
            slavenames = [s.slavename for s in builder_slaves],
        ))
        
    return builders

def make_factory(branch, python, database):
    """
    Generates the BuildFactory (e.g. set of build steps) for this (branch,
    python, database) combo. The series of steps is described in the module
    docstring, above.
    """
    f = BuildFactory()
    f.addSteps([
        buildsteps.DjangoSVN(branch=branch),
        buildsteps.DownloadVirtualenv(),
        buildsteps.UpdateVirtualenv(python=python, db=database),
        buildsteps.GenerateSettings(python=python, db=database),
        buildsteps.TestDjango(python=python, db=database),
    ])
    return f
