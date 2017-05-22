from js9 import j

import threading
from .SSHClient import SSHClient
from .AsyncSSHClient import AsyncSSHClient


class SSHClientFactory:

    _lock = threading.Lock()
    cache = {}

    logger = j.logger.get("j.clients.ssh")

    # to not have to duplicate information
    SSHKeysLoad = j.do.SSHKeysLoad
    _addSSHAgentToBashProfile = j.do._addSSHAgentToBashProfile
    _initSSH_ENV = j.do._initSSH_ENV
    _getSSHSocketpath = j.do._getSSHSocketpath
    SSHKeysLoad = j.do.SSHKeysLoad
    SSHKeyGetPathFromAgent = j.do.SSHKeyGetPathFromAgent
    SSHKeyGetFromAgentPub = j.do.SSHKeyGetFromAgentPub
    SSHKeysListFromAgent = j.do.SSHKeysListFromAgent
    SSHEnsureKeyname = j.do.SSHEnsureKeyname
    authorize_user = j.do.authorize_user
    authorize_root = j.do.authorize_root
    SSHAuthorizeKey = j.do.SSHAuthorizeKey
    _loadSSHAgent = j.do._loadSSHAgent
    SSHAgentAvailable = j.do.SSHAgentAvailable

    def __init__(self):
        self.__jslocation__ = "j.clients.ssh"
        self.__imports__ = "paramiko,asyncssh"

    def reset(self):
        with self._lock:
            for key, client in self.cache.items():
                client.close()
            self.cache = {}

    def get(self, addr='', port=22, login="root", passwd=None, stdout=True, forward_agent=True, allow_agent=True,
            look_for_keys=True, timeout=5, key_filename=None, passphrase=None, die=True, usecache=True):
        """
        gets an ssh client.
        @param addr: the server to connect to
        @param port: port to connect to
        @param login: the username to authenticate as
        @param passwd: leave empty if logging in with sshkey
        @param stdout: show output
        @param foward_agent: fowrward all keys to new connection
        @param allow_agent: set to False to disable connecting to the SSH agent
        @param look_for_keys: set to False to disable searching for discoverable private key files in ~/.ssh/
        @param timeout: an optional timeout (in seconds) for the TCP connect
        @param key_filename: the filename to try for authentication
        @param passphrase: a password to use for unlocking a private key
        @param die: die on error
        @param usecache: use cached client. False to get a new connection

        If password is passed, sshclient will try to authenticated with login/passwd.
        If key_filename is passed, it will override look_for_keys and allow_agent and try to connect with this key.
        """
        with self._lock:
            key = "%s_%s_%s_%s_sync" % (
                addr, port, login, j.data.hash.md5_string(str(passwd)))

            if key in self.cache and usecache:
                try:
                    if not self.cache[key].transport.is_active():
                        usecache = False
                except Exception:
                    usecache = False
            if key not in self.cache or usecache is False:
                self.cache[key] = SSHClient(
                    addr,
                    port,
                    login,
                    passwd,
                    stdout=stdout,
                    forward_agent=forward_agent,
                    allow_agent=allow_agent,
                    look_for_keys=look_for_keys,
                    key_filename=key_filename,
                    passphrase=passphrase,
                    timeout=timeout)

            return self.cache[key]

    def getAsync(self, addr='', port=22, login="root", passwd=None, stdout=True, forward_agent=True, allow_agent=True,
                 look_for_keys=True, timeout=5, key_filename=(), passphrase=None, die=True, usecache=True):

        key = "%s_%s_%s_%s_async" % (
            addr, port, login, j.data.hash.md5_string(str(passwd)))

        if key not in self.cache or usecache is False:
            self.cache[key] = AsyncSSHClient(
                addr=addr,
                port=port,
                login=login,
                passwd=passwd,
                forward_agent=forward_agent,
                allow_agent=allow_agent,
                look_for_keys=look_for_keys,
                key_filename=key_filename,
                passphrase=passphrase,
                timeout=timeout)

        return self.cache[key]

    def removeFromCache(self, client):
        with self._lock:
            key = "%s_%s_%s_%s" % (
                client.addr, client.port, client.login, j.data.hash.md5_string(str(client.passwd)))
            if key in self.cache:
                self.cache.pop(key)

    def SSHKeyGetFromAgentPub(self, keyname="", die=True):
        rc, out, err = j.tools.executorLocal.execute("ssh-add -L", die=False)
        if rc > 1:
            err = "Error looking for key in ssh-agent: %s", out
            if die:
                raise j.exceptions.RuntimeError(err)
            else:
                self.logger.error(err)
                return None

        if keyname == "":
            paths = []
            for line in out.splitlines():
                line = line.strip()
                paths.append(line.split(" ")[-1])
            if len(paths) == 0:
                raise j.exceptions.RuntimeError(
                    "could not find loaded ssh-keys")

            path = j.tools.console.askChoice(
                paths, "Select ssh key to push (public part only).")
            keyname = j.do.getBaseName(path)

        for line in out.splitlines():
            delim = (".ssh/%s" % keyname)
            if line.endswith(delim):
                content = line.strip()
                content = content
                return content
        err = "Did not find key with name:%s, check its loaded in ssh-agent with ssh-add -l" % keyname
        if die:
            raise j.exceptions.RuntimeError(err)
        else:
            self.logger.error(err)
        return None

    def close(self):
        with self._lock:
            for key, client in self.cache.items():
                client.close()
