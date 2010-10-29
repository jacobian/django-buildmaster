from buildbot.status import html, words
from buildbot.status.web.authz import Authz
from buildbot.status.web.auth import BasicAuth

authz = Authz(
    forceBuild=True,
    forceAllBuilds=True,
    pingBuilder=True,
    gracefulShutdown=True,
    stopBuild=True,
    stopAllBuilds=True,
    cancelPendingBuild=True,
    cleanShutdown=True,
)

status = [
    html.WebStatus(
        http_port = '8010',
        authz = authz,
        order_console_by_time = True,
        revlink = 'http://code.djangoproject.com/changeset/%s',
        changecommentlink = (
            r'\b#(\d+)\b',
            r'http://code.djangoproject.com/ticket/\1',
            r'Ticket \g<0>'
        )
    ),
    
    words.IRC(
        host = 'irc.freenode.net',
        channels = ['#revsys'],
        nick = 'djangobuilds',
        notify_events = {
            'successToFailure': True,
            'failureToSuccess': True,
        }
    )
]