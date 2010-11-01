"""
A couple random utility functions.
"""

import re
import collections

PackageSpec = collections.namedtuple('PackageSpec', 'name version')

def parse_version_spec(spec, specificity=2):
    """
    Parse a package + version string into a base package name and a
    "less-specific" version.
    
    Ugh, that makes no sense. Examples::
    
        >>> parse_version_spec('python2.6')
        PackageSpec(name='python', version='2.6')
        
        >>> parse_version_spec('postgresql8.4.2', specificity=1)
        PackageSpec(name='postgresql', version='8')

        >>> parse_version_spec('postgresql8.4.2', specificity=2)
        PackageSpec(name='postgresql', version='8.4')
        
        >>> parse_version_spec('postgresql8.4.2', specificity=3)
        PackageSpec(name='postgresql', version='8.4.2')
        
        >>> parse_version_spec('sqlite3')
        PackageSpec(name='sqlite', version='3.X')
        
    """
    m = re.match('([A-Za-z]+)([\d.]+)', spec)
    if not m:
        raise ValueError("%r doesn't look like a version spec.")
        
    base = m.group(1)
    versionbits = m.group(2).split('.')
    versionbits.extend(['X'] * (specificity - len(versionbits)))
    return PackageSpec(base, ".".join(versionbits[:specificity]))