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
from buildbot.process.factory import BuildFactory
from .slaves import slaves
from . import buildsteps

# XXX This is be repeated and should moved elsewhere.
BRANCHES = ['trunk']
    
def generate_builders(branches, slaves):
    """
    Generate a builder for each (slave, branch, python, database) combination.
    
    TODO: be more intellegent about not repeating combinations that exist on
    multiple slaves. The better way would be to gather a list of *all* pythons &
    dbs and then build those on any slave providing that config.
    """
    for slave in slaves:
        configs = itertools.product(BRANCHES, slave.pythons, slave.databases)
        for (branch, python, database) in configs:
            # Skip this combo if the slave can't build it.
            if (python, database) in slave.skip_configs:
                continue
                
            yield {
                'name': '%s-%s-%s' % (branch, python, database),
                'slavename': slave.slavename,
                'workdir': '%s-%s-%s' % (branch, python, database),
                'factory': make_factory(branch, python, database, slave.get_settings(python, database)),
            }

def make_factory(branch, python, database, settings):
    f = BuildFactory()
    f.addSteps([
        buildsteps.DjangoSVN(branch),
        buildsteps.DownloadVirtualenv(),
        buildsteps.UpdateVirtualenv(python, database),
        buildsteps.GenerateSettings(python, database, settings),
        buildsteps.TestDjango(python, database),
    ])
    return f
    
builders = list(generate_builders(BRANCHES, slaves))