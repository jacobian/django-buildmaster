"""
A latent build slave that runs on Rackspace Cloud.
"""

import time
import cloudservers
from buildbot.buildslave import AbstractLatentBuildSlave
from buildbot.interfaces import LatentBuildSlaveFailedToSubstantiate
from twisted.internet import defer, threads
from twisted.python import log

class CloudserversLatentBuildslave(AbstractLatentBuildSlave):
    
    def __init__(self, name, password, cloudservers_username,
                 cloudservers_apikey, image, flavor=1, files=None, **kwargs):
                 
        AbstractLatentBuildSlave.__init__(self, name, password, **kwargs)

        self.conn = cloudservers.CloudServers(cloudservers_username, cloudservers_apikey)
        self.image = self.get_image(image)
        self.flavor = self.get_flavor(flavor)
        self.files = files
        self.instance = None

    def get_image(self, image):
        """
        Look up an image by name or by ID.
        """
        try:
            return self.conn.images.get(int(image))
        except ValueError:
            return self.conn.images.find(name=image)
            
    def get_flavor(self, flavor):
        """
        Look up a flavor by name or by ID.
        """
        try:
            return self.conn.flavors.get(int(flavor))
        except ValueError:
            return self.conn.flavors.find(name=flavor)
    
    def start_instance(self):
        if self.instance is not None:
            raise ValueError('instance active')
        return threads.deferToThread(self._start_instance)

    def _start_instance(self,):
        self.instance = self.conn.servers.create(self.slavename, 
                                                 image=self.image,
                                                 flavor=self.flavor,
                                                 files=self.files)
        log.msg('%s %s started instance %s' % 
                (self.__class__.__name__, self.slavename, self.instance.id))
        
        # Wait for the server to boot.
        d1 = 0
        while self.instance.status == 'BUILD':
            self.instance.get()
            time.sleep(5)
            d1 += 5
            if d1 % 60 == 0:
                log.msg('%s %s has waited %d seconds for instance %s' %
                        (self.__class__.__name__, self.slavename, d1, self.instance.id))
        
        # Sometimes status goes BUILD -> UNKNOWN briefly before coming ACTIVE.
        # So we'll wait for it in the UNKNOWN state for a bit.
        d2 = 0
        while self.instance.status == 'UNKNOWN':
            self.instance.get()
            time.sleep(5)
            d2 += 5
            if d2 % 60 == 0:
                log.msg('%s %s instance %s has been UNKNOWN for %d seconds' % 
                        (self.__class__.__name__, self.slavename, d2, self.instance.id))
            if d2 == 600:
                log.msg('%s %s giving up on instance %s after UNKNOWN for 10 minutes.' % 
                        (self.__class__.__name__, self.slavename, self.instance.id))
                raise LatentBuildSlaveFailedToSubstantiate(self.instance.id, self.instance.status)
            
        # XXX Sometimes booting just... fails. When that happens the slave
        # basically becomes "stuck" and Buildbot won't do anything more with it.
        # So should we re-try here? Or set self.instance to None? Or...?
        if self.instance.status != 'ACTIVE':
            log.msg('%s %s failed to start instance %s (status became %s)' %
                    (self.__class__.__name__, self.slavename, self.instance.id, self.instance.status))
            raise LatentBuildSlaveFailedToSubstantiate(self.instance.id, self.instance.status)
        
        # Also, sometimes the slave boots but just doesn't actually come up
        # (it's alive but networking is broken?) A hard reboot fixes it most
        # of the time, so ideally we'd expect to hear from the slave within
        # some minutes and issue a hard reboot (or kill it and try again?)
        # Is that possible from here?
        
        # FIXME: this message prints the wrong number of seconds.
        log.msg('%s %s instance %s started in about %d seconds' %
                (self.__class__.__name__, self.slavename, self.instance.id, d1+d2))
        
        return self.instance.id
        
    def stop_instance(self, fast=False):
        if self.instance is None:
            return defer.succeed(None)
            
        instance = self.instance
        self.instance = None
        return threads.deferToThread(self._stop_instance, instance)

    def _stop_instance(self, instance):
        log.msg('%s %s deleting instance %s' % (
                self.__class__.__name__, self.slavename, instance.id))
        instance.delete()
        
        # Wait for the instance to go away. We can't just wait for a deleted
        # state, unfortunately -- the resource just goes away and we get a 404.
        try:
            duration = 0
            while instance.status == 'ACTIVE':
                instance.get()
                time.sleep(5)
                duration += 5
                if duration % 60 == 0:
                    log.msg('%s %s has waited %s for instance %s to die' % 
                            (self.__class__.__name__, self.slavename, duration, instance.id))
                    # Try to delete it again, just for funsies.
                    instance.delete()
        except cloudservers.NotFound:
            # We expect this NotFound - it's what happens when the slave dies.
            pass
        
        log.msg('%s %s deleted instance %s' % 
                (self.__class__.__name__, self.slavename, instance.id))
                
