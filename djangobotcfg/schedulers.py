from buildbot.schedulers.basic import Scheduler
from .builders import builders

# XXX This is be repeated and should moved elsewhere.
BRANCHES = ['trunk', '1.2.X']

def make_scheduler(branch):
    return Scheduler(
        name = branch,
        branch = branch,
        treeStableTimer = 10,
        builderNames = [b["name"] for b in builders if branch in b['category']]
    )

schedulers = [
    Scheduler(
        name = 'trunk',
        treeStableTimer = 10,
        builderNames = [b["name"] for b in builders],
    )
]