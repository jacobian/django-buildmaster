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
                 cloudservers_apikey, imageid, flavorid=1, 
                 insubstantiate_after_build=True, **kwargs):
                 
        AbstractLatentBuildSlave.__init__(self, name, password, **kwargs)

        self.conn = cloudservers.CloudServers(cloudservers_username, cloudservers_apikey)
        self.image = self.conn.images.get(id=imageid)
        self.flavor = self.conn.flavors.get(id=flavorid)
        self.instance = None
        
        # Shut the server down once the build(s) are complete?
        self.insubstantiate_after_build = insubstantiate_after_build
        
    def start_instance(self):
        if self.instance is not None:
            raise ValueError('instance active')
        return threads.deferToThread(self._start_instance)
    
    def _start_instance(self):
        self.instance = self.conn.servers.create(self.slavename, self.image, self.flavor)
        log.msg('%s %s started instance %s' % 
                (self.__class__.__name__, self.slavename, self.instance.id))
        
        duration = 0
        while self.instance.status == 'BUILD':
            time.sleep(5)
            duration += 5
            if duration % 60 == 0:
                log.msg('%s %s has waited %d minutes for instance %s' %
                        (self.__class__.__name__, self.slavename, duration//60, self.instance.id))
            self.instance.get()
            
        if self.instance.status != 'ACTIVE':
            log.msg('%s %s failed to start instance %s (%s)' %
                    (self.__class__.__name__, self.slavename, self.instance.id, self.instance.state))
            raise LatentBuildSlaveFailedToSubstantiate(self.instance.id, self.instance.status)
            
        log.msg('%s %s instance %s started about %d minutes %d seconds' %
                (self.__class__.__name__, self.slavename, self.instance.id, duration//60, duration%60))
        return self.instance.id
        
    def stop_instance(self, fast=False):
        if self.instance is None:
            return defer.succeed(None)
        return threads.deferToThread(self._stop_instance, self.instance)
    
    def _stop_instance(self, instance):
        instance.delete()
        log.msg('%s %s deleted instance %s' % 
                (self.__class__.__name__, self.slavename, instance.id))
        
    def buildFinished(self, *args, **kwargs):
        AbstractLatentBuildSlave.buildFinished(self, *args, **kwargs)
        if self.insubstantiate_after_build:
            log.msg("%s %s got buildFinished notification - attempting to insubstantiate" %
                    (self.__class__.__name__, self.slavename))
            self.insubstantiate()    