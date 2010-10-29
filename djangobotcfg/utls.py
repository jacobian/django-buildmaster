"""
A couple random utility functions.
"""

import re

def parse_version_spec(spec, specificity=2):
    """
    Parse a package + version string into a base package name and a
    "less-specific" version.
    
    Ugh, that makes no sense. Examples::
    
        >>> parse_version_spec('python2.6')
        ('python', '2.6')
        
        >>> parse_version_spec('postgresql8.4.2', specificity=1)
        ('postgresql', '8')

        >>> parse_version_spec('postgresql8.4.2', specificity=2)
        ('postgresql', '8.4')
        
        >>> parse_version_spec('postgresql8.4.2', specificity=3)
        ('postgresql', '8.4.2')
        
        >>> parse_version_spec('sqlite3')
        ('sqlite', '3.X')
        
    """
    m = re.match('([A-Za-z]+)([\d.]+)', spec)
    if not m:
        raise ValueError("%r doesn't look like a version spec.")
        
    base = m.group(1)
    versionbits = m.group(2).split('.')
    versionbits.extend(['X'] * (specificity - len(versionbits)))
    return (base, ".".join(versionbits[:specificity]))
    
