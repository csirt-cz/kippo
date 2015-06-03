from zope.interface import implements

import os

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet, service
from twisted.cred import portal
from twisted.conch.ssh import keys

from cowrie.core.config import config
import cowrie.core.ssh
from cowrie import core

class Options(usage.Options):
    optParameters = [
        ["port", "p", 2222, "The port number to listen on."],
        ["config", "c", 'cowrie.cfg', "The configuration file to use."]
        ]

class CowrieServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "cowrie"
    description = "She sells sea shells by the sea shore."
    options = Options

    def makeService(self, options):
        """
        Construct a TCPServer from a factory defined in myproject.
        """

        if os.name == 'posix' and os.getuid() == 0:
            print 'ERROR: You must not run cowrie as root!'
            sys.exit(1)

        factory = core.ssh.HoneyPotSSHFactory()
        factory.portal = portal.Portal(core.ssh.HoneyPotRealm())
        factory.portal.registerChecker(core.auth.HoneypotPublicKeyChecker())
        factory.portal.registerChecker(core.auth.HoneypotPasswordChecker())

        rsa_pubKeyString, rsa_privKeyString = core.ssh.getRSAKeys()
        dsa_pubKeyString, dsa_privKeyString = core.ssh.getDSAKeys()
        factory.publicKeys = {'ssh-rsa': keys.Key.fromString(data=rsa_pubKeyString),
                              'ssh-dss': keys.Key.fromString(data=dsa_pubKeyString)}
        factory.privateKeys = {'ssh-rsa': keys.Key.fromString(data=rsa_privKeyString),
                               'ssh-dss': keys.Key.fromString(data=dsa_privKeyString)}

        cfg = config()

        if cfg.has_option('honeypot', 'listen_addr'):
            listen_addr = cfg.get('honeypot', 'listen_addr')
        elif cfg.has_option('honeypot', 'ssh_addr'):
            # ssh_addr for backwards compatibility
            listen_addr = cfg.get('honeypot', 'ssh_addr')
        else:
            listen_addr = '0.0.0.0'
               
        if cfg.has_option('honeypot', 'listen_port'):
            listen_port = int(cfg.get('honeypot', 'listen_port'))
        elif cfg.has_option('honeypot', 'ssh_port'):
            # ssh_port for backwards compatibility
            listen_port = int(cfg.get('honeypot', 'ssh_port'))
        else:
            listen_port = 2222

        application = service.Application('honeypot')

        for i in listen_addr.split():
            svc = internet.TCPServer( listen_port, factory, interface=i)
            svc.setServiceParent(application)

        if cfg.has_option('honeypot', 'interact_enabled') and \
                 cfg.get('honeypot', 'interact_enabled').lower() in \
                 ('yes', 'true', 'on'):
            iport = int(cfg.get('honeypot', 'interact_port'))
            from cowrie.core import interact
            svc = internet.TCPServer(iport, interact.makeInteractFactory(factory))
            svc.setServiceParent(application)

        return svc
        #return internet.TCPServer(int(options["port"]), MyFactory())


# Now construct an object which *provides* the relevant interfaces
# The name of this variable is irrelevant, as long as there is *some*
# name bound to a provider of IPlugin and IServiceMaker.

serviceMaker = CowrieServiceMaker()
