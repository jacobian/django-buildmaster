"""
How changes get from SVN into the buildbot.
"""

from buildbot.changes.svnpoller import SVNPoller

def get_change_source(svnurl, branches):
    
    # Create a reverse map of branch prefixes to branch names.
    branchmap = dict((v.replace(svnurl, '').lstrip('/'), k)
                     for k,v in branches.items())
    
    # Create a function that'll parse branches as given in the branches dict.
    def split_file(path):
        path = path.lstrip('/')
        for branch_prefix in branchmap:
            if path.startswith(branch_prefix):
                
                # Return (branch_name, path_relative_to_branch) to signify
                # that this is a change we care about.
                return (branchmap[branch_prefix],
                        path.replace(branch_prefix, '').lstrip('/'))
        
        # None sinifies this is a change we don't care about.
        return None
        
    return SVNPoller(
        svnurl = svnurl,
        split_file = split_file,
        
        # Poll for new SVN changes every 5 minutes.
        pollinterval = 5 * 60,
        
        # Only suck down the last 20 commits. If we commit more than that in
        # five minutes (pollinterval) we could lose a build, but if we're 
        # committing *that* often we're seriously in trouble.
        histmax = 20,
        
        # A way of converting a change number to a link.
        # XXX It looks like there's something similar in WebStatus (see
        # status.py); are these two settings redundant?
        revlinktmpl = 'http://code.djangoproject.com/changeset/%s',
    )