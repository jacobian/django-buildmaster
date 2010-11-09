from buildbot.status import html, words
from buildbot.status.web.authz import Authz
from .djangoauth import DjangoAuth

authz = Authz(
    auth = DjangoAuth(),
    gracefulShutdown = 'auth',
    forceBuild = 'auth',
    forceAllBuilds = 'auth',
    pingBuilder = 'auth',
    stopBuild = 'auth',
    stopAllBuilds = 'auth',
    cancelPendingBuild = 'auth',
    stopChange = 'auth',
    cleanShutdown = 'auth',
)

def get_status(secrets):
    return [
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
            channels = ['#django-dev'],
            nick = 'djbuilds',
            password = str(secrets['irc']['password']),
            notify_events = {
                'successToFailure': True,
                'failureToSuccess': True,
            }
        ),
    ]