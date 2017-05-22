from js9 import j

from .ExecutorSSH import *
from .ExecutorLocal import *
from .ExecutorAsyncSSH import ExecutorAsyncSSH
from .ExecutorG8Core import ExecutorG8Core
import threading


class ExecutorFactory:
    _lock = threading.Lock()
    _executors = {}
    _executors_async = {}

    def __init__(self):
        self.__jslocation__ = "j.tools.executor"
        self.__imports__ = "g8core"

    def pushkey(self, addr, passwd, keyname="", pubkey="", port=22, login="root"):
        """
        @param keyname is name of key (pub)
        @param pubkey is the content of the pub key
        """
        executor = ExecutorSSH(
            addr,
            port=port,
            login=login,
            passwd=passwd,
            pubkey=pubkey,
            key_filename=keyname,
            look_for_keys=True,
            allow_agent=True)
        executor.pushkey()

    def getSSHViaProxy(self, jumphost, jmphostuser, host, username, port, identityfile, proxycommand=None):
        """
        To get an executor to host through a jumphost *knows about*.

        @param  jumphost is the host we connect through
        @param jmphostuser is the user at the jumphost
        @host is the host we connect to through the jumphost
        @username is the username on host

        local> ssh jmphostuser@jumphost
        jmphostuser@jumphost> ssh user@host
        user@host>

        example:
        In [1]: ex=j.tools.executor.getSSHViaProxy("192.168.21.163", "cloudscalers",
            "192.168.21.156","cloudscalers", 22, "/home/ahmed/.ssh/id_rsa")

        In [2]: ex.prefab.core.run("hostname")
        [Tue06 14:22] - ...mpScale/tools/executor/ExecutorSSH.py:114  - DEBUG    - cmd: hostname
        [Tue06 14:22] - ...mpScale/tools/executor/ExecutorSSH.py:128  - INFO     - EXECUTE :22: hostname
        vm-6

        """
        executor = ExecutorSSH()
        ex = executor.getSSHViaProxy(jumphost, jmphostuser, host, username, port, identityfile, proxycommand)
        with self._lock:
            self._executors[host] = ex
        return ex

    def get(self, executor="localhost"):
        """
        @param executor is an executor object, None or $hostname:$port or $ipaddr:$port or $hostname or $ipaddr
        """
        #  test if it's in cache
        with self._lock:
            if executor in self._executors:
                return self._executors[executor]

            if executor in ["localhost", "", None, "127.0.0.1"]:
                if 'localhost' not in self._executors:
                    local = self.getLocal()
                    self._executors['localhost'] = local
                return self._executors['localhost']

        if j.data.types.string.check(executor):
            if executor.find(":") > 0:
                nbr = executor.count(':')
                login = 'root'
                if nbr == 1:
                    # ssh with port
                    addr, port = executor.split(":")
                if nbr == 2:
                    addr, port, login = executor.split(":")
                return self.getSSHBased(addr=addr.strip(), port=int(port), login=login)
            else:
                return self.getSSHBased(addr=executor.strip())
        else:
            return executor

    def getLocal(self, jumpscale=False, debug=False, checkok=False):
        return ExecutorLocal(debug=debug, checkok=debug)

    def getSSHBased(self, addr="localhost", port=22, login="root", passwd=None, debug=False, allow_agent=True,
                    look_for_keys=True, timeout=5, usecache=True, passphrase=None, key_filename=None):
        """
        returns an ssh-based executor where:
        allow_agent: uses the ssh-agent to connect
        look_for_keys: will iterate over keys loaded on the ssh-agent and try to use them to authenticate
        pushkey: authorizes itself on remote
        pubkey: uses this particular key (path) to connect
        usecache: gets cached executor if available. False to get a new one.
        """
        with self._lock:
            key = '%s:%s:%s' % (addr, port, login)
            if key not in self._executors or usecache is False:
                self._executors[key] = ExecutorSSH(addr=addr,
                                                   port=port,
                                                   login=login,
                                                   passwd=passwd,
                                                   debug=debug,
                                                   allow_agent=allow_agent,
                                                   look_for_keys=look_for_keys,
                                                   timeout=timeout,
                                                   key_filename=key_filename,
                                                   passphrase=passphrase)
            return self._executors[key]

    def getAsyncSSHBased(self, addr="localhost", port=22, login="root", passwd=None, debug=False, allow_agent=True,
                         look_for_keys=True, timeout=5, usecache=True, passphrase=None, key_filename=()):
        """
        returns an asyncssh-based executor where:
        allow_agent: uses the ssh-agent to connect
        look_for_keys: will iterate over keys loaded on the ssh-agent and try to use them to authenticate
        pushkey: authorizes itself on remote
        pubkey: uses this particular key (path) to connect
        usecache: gets cached executor if available. False to get a new one.
        """
        with self._lock:
            key = '%s:%s:%s' % (addr, port, login)
            if key not in self._executors_async or usecache is False:
                self._executors_async[key] = ExecutorAsyncSSH(addr=addr,
                                                              port=port,
                                                              login=login,
                                                              passwd=passwd,
                                                              debug=debug,
                                                              allow_agent=allow_agent,
                                                              look_for_keys=look_for_keys,
                                                              timeout=timeout,
                                                              key_filename=key_filename,
                                                              passphrase=passphrase)

            return self._executors_async[key]

    def getJSAgentBased(self, agentControllerClientKey, debug=False, checkok=False):
        return ExecutorAgent2(addr, debug=debug, checkok=debug)

    def getG8CoreBased(self, host='localhost', port=6379, password=None, container_id=None):
        return ExecutorG8Core(host=host, port=port, password=password, container_id=container_id)

    def reset(self, executor):
        """
        reset remove the executor passed in argument from the cache.
        """
        if j.data.types.string.check(executor):
            key = executor
        elif executor.type == 'ssh':
            key = '%s:%s:%s' % (executor.addr, executor.port, executor.login)
        else:
            raise j.exceptions.Input(message='executor type not recognize.')
        with self._lock:
            if key in self._executors:
                exe = self._executors[key]
                j.tools.prefab.reset(exe.prefab)
                del self._executors[key]
