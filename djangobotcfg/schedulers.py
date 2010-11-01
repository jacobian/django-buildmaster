from buildbot.schedulers.basic import Scheduler

def get_schedulers(branches, builders):
    """
    Make a build scheduler for each branch.
    """
    return [make_scheduler(branch, builders) for branch in branches]

def make_scheduler(branch, builders):
    return Scheduler(
        name = branch,
        branch = branch,
        treeStableTimer = 10,
        builderNames = [b.name for b in builders if branch in b.name]
    )