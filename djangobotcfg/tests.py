"""
Yes, I'm trying to unit test my buildbot config.

It's a bit of an exercise in futility.
"""

from . import slaves
from . import utils

def test_buildslave_can_build():
    bs1 = slaves.DjangoBuildSlave('BS1',
        pythons = {'2.6': True, '2.7': '/usr/local/bin/python2.7'},
        databases = ['sqlite3', 'postgresql8.4.1'],
        skip_configs = [('2.7', 'postgresql8.4.1')],
    )
    
    v = utils.parse_version_spec
    assert bs1.can_build('2.6', v('sqlite3'))
    assert bs1.can_build('2.6', v('postgresql8.4'))
    assert bs1.can_build('2.7', v('sqlite3'))
    assert not bs1.can_build('2.7', v('postgresql8.4'))
