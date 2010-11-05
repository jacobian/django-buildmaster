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
                 cloudservers_apikey, image, flavor=1,
                 insubstantiate_after_build=True, **kwargs):
                 
        AbstractLatentBuildSlave.__init__(self, name, password, **kwargs)

        self.conn = cloudservers.CloudServers(cloudservers_username, cloudservers_apikey)
        self.image = self.get_image(image)
        self.flavor = self.get_flavor(flavor)
        self.instance = None
        self.instance_lock = defer.DeferredLock()
        
        # Shut the server down once the build(s) are complete?
        self.insubstantiate_after_build = insubstantiate_after_build
    
    def get_image(self, image):
        """
        Look up an image by name or by ID.
        """
        try:
            return self.conn.images.get(id=int(image))
        except ValueError:
            return self.conn.images.find(name=image)
            
    def get_flavor(self, flavor):
        """
        Look up a flavor by name or by ID.
        """
        try:
            return self.conn.flavors.get(id=int(flavor))
        except ValueError:
            return self.conn.flavors.find(name=flavor)
            
    def start_instance(self):
        # Prevent starting a new instance while an old one is shutting down.
        self.instance_lock.acquire()
        return threads.deferToThread(self._start_instance)
    
    def _start_instance(self):
        self.instance = self.conn.servers.create(self.slavename, self.image, self.flavor)
        log.msg('%s %s started instance %s' % 
                (self.__class__.__name__, self.slavename, self.instance.id))
        
        duration = 0
        while self.instance.status == 'BUILD':
            self.instance.get()
            time.sleep(5)
            duration += 5
            if duration % 60 == 0:
                log.msg('%s %s has waited %d seconds for instance %s' %
                        (self.__class__.__name__, self.slavename, duration, self.instance.id))
        
        # Sometimes status goes BUILD -> UNKNOWN briefly before coming ACTIVE.
        # So we'll wait for it in the UNKNOWN state for a bit.
        duration = 0
        while self.instance.status == 'UNKNOWN':
            self.instance.get()
            time.sleep(5)
            duration += 5
            if duration % 60 == 0:
                log.msg('%s %s instance %s has been UNKNOWN for %d seconds' % 
                        (self.__class__.__name__, self.slavename, duration, self.instance.id))
            if duration == 600:
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
                (self.__class__.__name__, self.slavename, self.instance.id, duration))
        return self.instance.id
        
    def stop_instance(self, fast=False):
        if self.instance is None:
            return defer.succeed(None)
            
        instance, self.instance = self.instance, None
        d = threads.deferToThread(self._stop_instance, instance)
    
        # Release the lock when _stop_instance succeeds.
        @d.addCallback
        def _done(res):
            return self.instance_lock.release()
            
        # XXX Is this needed? Coppied from http://buildbot.net/trac/ticket/1001
        @d.addCallback
        def _released(res):
            return True
            
        return d
        
        # XXX It seems like this might work, too:
        # return threads.deferToThread(self._stop_instance, instance).addCallback(self.instance_lock.release)
    
    def _stop_instance(self, instance):
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
                            (self.__class__.__name__, self.slavename, duration, self.instance.id))
                    # Try to delete it again, just for funsies.
                    instance.delete()
        except cloudservers.NotFound:
            # We expect this NotFound - it's what happens when the slave dies.
            pass
            
        
        log.msg('%s %s deleted instance %s' % 
                (self.__class__.__name__, self.slavename, instance.id))
                
    def buildFinished(self, *args, **kwargs):
        # FIXME: any way to keep the slave up if there are still pending builds for it?
        AbstractLatentBuildSlave.buildFinished(self, *args, **kwargs)
        if self.insubstantiate_after_build:
            log.msg("%s %s got buildFinished notification - attempting to insubstantiate" %
                    (self.__class__.__name__, self.slavename))
            self.insubstantiate()    