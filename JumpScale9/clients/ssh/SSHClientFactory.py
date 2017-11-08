from js9 import j

import os
import threading
from .SSHClient import SSHClient
from .AsyncSSHClient import AsyncSSHClient


class SSHClientFactory:

    _lock = threading.Lock()
    cache = {}

    logger = j.logger.get("j.clients.ssh")

    def __init__(self):
        self.__jslocation__ = "j.clients.ssh"
        self.__imports__ = "paramiko,asyncssh"
        self.loadSSHAgent = self._loadSSHAgent

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
            keyname = j.sal.fs.getBaseName(path)

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

    def _addSSHAgentToBashProfile(self, path=None):

        bashprofile_path = os.path.expanduser("~/.bash_profile")
        if not j.sal.fs.exists(bashprofile_path):
            j.do.execute('touch %s' % bashprofile_path)

        content = j.sal.fs.readFile(bashprofile_path)
        out = ""
        for line in content.split("\n"):
            if line.find("#JSSSHAGENT") != -1:
                continue
            if line.find("SSH_AUTH_SOCK") != -1:
                continue

            out += "%s\n" % line

        if "SSH_AUTH_SOCK" in os.environ:
            self.logger.info("NO NEED TO ADD SSH_AUTH_SOCK to env")
            j.sal.fs.writeFile(bashprofile_path, out)
            return

        out += "export SSH_AUTH_SOCK=%s" % self._getSSHSocketpath()
        out = out.replace("\n\n\n", "\n\n")
        out = out.replace("\n\n\n", "\n\n")
        j.sal.fs.writeFile(bashprofile_path, out)

    def _initSSH_ENV(self, force=False):
        if force or "SSH_AUTH_SOCK" not in os.environ:
            os.putenv("SSH_AUTH_SOCK", self._getSSHSocketpath())
            os.environ["SSH_AUTH_SOCK"] = self._getSSHSocketpath()

    def _getSSHSocketpath(self):

        if "SSH_AUTH_SOCK" in os.environ:
            return(os.environ["SSH_AUTH_SOCK"])

        socketpath = "%s/sshagent_socket" % os.environ.get("HOME", '/root')
        os.environ['SSH_AUTH_SOCK'] = socketpath
        return socketpath

    def SSHAgentCheck(self):
        """
        will check that agent started if not will start it.
        """
        if "SSH_AUTH_SOCK" not in os.environ:
            self._initSSH_ENV(True)
            self._addSSHAgentToBashProfile()
        if not self.SSHAgentAvailable():
            self.logger.info('Will start agent')
            self._loadSSHAgent()

    def SSHKeyLoad(self, path, duration=3600 * 24):
        """
        @param path is name or full path
        """
        self.SSHAgentCheck()
        if self.SSHAgentCheckKeyIsLoaded(path):
            return
        self.logger.info("load ssh key:%s" % path)
        j.do.chmod(path, 0o600)
        cmd = "ssh-add -t %s %s " % (duration, path)
        j.do.executeInteractive(cmd)

    def SSHAgentCheckKeyIsLoaded(self, keyNamePath):
        keysloaded = [j.sal.fs.getBaseName(item)
                      for item in self.SSHKeysListFromAgent()]
        if j.sal.fs.getBaseName(keyNamePath) in keysloaded:
            self.logger.info("ssh key:%s loaded" % keyNamePath)
            return True
        else:
            self.logger.info("ssh key:%s NOT loaded" % keyNamePath)
            return False

    def askItemsFromList(self, items, msg=""):
        if len(items) == 0:
            return []
        if msg != "":
            print(msg)
        nr = 0
        for item in items:
            nr += 1
            print(" - %s: %s" % (nr, item))
        print("select item(s) from list (nr or comma separated list of nr, * is all)")
        item = input()
        if item.strip() == "*":
            return items
        elif item.find(",") != -1:
            res = []
            itemsselected = [item.strip() for item in item.split(",") if item.strip() != ""]
            for item in itemsselected:
                item = int(item) - 1
                res.append(items[item])
            return res
        else:
            item = int(item) - 1
            return [items[item]]

    def SSHKeysLoad(self, path=None, duration=3600 * 24, die=False):
        """
        will see if ssh-agent has been started
        will check keys in home dir
        will ask which keys to load
        will adjust .profile file to make sure that env param is set to allow ssh-agent to find the keys
        """
        self.SSHAgentCheck()

        if path is None:
            path = os.path.expanduser("~/.ssh")
        j.do.createDir(path)

        if "SSH_AUTH_SOCK" not in os.environ:
            self._initSSH_ENV(True)

        self._loadSSHAgent()

        keysloaded = [j.sal.fs.getBaseName(item)
                      for item in self.SSHKeysListFromAgent()]

        if j.do.isDir(path):
            keysinfs = [j.sal.fs.getBaseName(item).replace(".pub", "") for item in j.sal.fs.listFilesInDir(
                path, filter="*.pub") if j.sal.fs.exists(item.replace(".pub", ""))]
            keysinfs = [item for item in keysinfs if item not in keysloaded]

            res = j.tools.console.askChoiceMultiple(
                keysinfs,
                "select ssh keys to load, use comma separated list e.g. 1,4,3 and press enter.")
        else:
            res = [j.sal.fs.getBaseName(path).replace(".pub", "")]
            path = j.do.getParent(path)

        for item in res:
            pathkey = "%s/%s" % (path, item)
            # timeout after 24 h
            self.logger.info("load sshkey: %s" % pathkey)
            cmd = "ssh-add -t %s %s " % (duration, pathkey)
            j.do.executeInteractive(cmd)

    def SSHKeyGetPathFromAgent(self, keyname, die=True):
        """
        Returns Path of public key that is loaded in the agent
        @param keyname: name of key loaded to agent to get its path
        """
        self.SSHAgentCheck()
        for item in j.clients.ssh.SSHKeysListFromAgent():
            if item.endswith(keyname):
                return item
        if die:
            raise RuntimeError(
                "Did not find key with name:%s, check its loaded in ssh-agent with ssh-add -l" %
                keyname)

    def SSHKeyGetFromAgentPub(self, keyname, die=True):
        """
        Returns Content of public key that is loaded in the agent
        @param keyname: name of key loaded to agent to get content from 
        """
        self.SSHAgentCheck()
        for item in j.clients.ssh.SSHKeysListFromAgent():
            if item.endswith(keyname):
                return j.sal.fs.readFile(item + ".pub")
        if die:
            raise RuntimeError(
                "Did not find key with name:%s, check its loaded in ssh-agent with ssh-add -l" %
                keyname)

    def SSHKeysListFromAgent(self, keyIncluded=False):
        """
        list ssh keys from the agent
        :param key_included:
        :return: list of paths
        """
        if "SSH_AUTH_SOCK" not in os.environ:
            self._initSSH_ENV(True)
        self._loadSSHAgent()
        cmd = "ssh-add -L"
        rc, out, err = j.do.execute(cmd, False, False, die=False)
        if rc:
            if rc == 1 and out.find("The agent has no identities") != -1:
                return []
            raise RuntimeError("error during listing of keys :%s" % err)
        keys = [line.split()
                for line in out.splitlines() if len(line.split()) == 3]
        if keyIncluded:
            return list(map(lambda key: key[2:0:-1], keys))
        else:
            return list(map(lambda key: key[2], keys))

    def SSHEnsureKeyname(self, keyname="", username="root"):
        if not j.sal.fs.exists(keyname):
            rootpath = "/root/.ssh/" if username == "root" else "/home/%s/.ssh/"
            fullpath = j.do.joinPaths(rootpath, keyname)
            if j.sal.fs.exists(fullpath):
                return fullpath
        return keyname

    def authorize_user(self, sftp_client, ip_address, keyname, username):
        basename = j.sal.fs.getBaseName(keyname)
        tmpfile = "/home/%s/.ssh/%s" % (username, basename)
        self.logger.info("push key to /home/%s/.ssh/%s" % (username, basename))
        sftp_client.put(keyname, tmpfile)

        # cannot upload directly to root dir
        auth_key_path = "/home/%s/.ssh/authorized_keys" % username
        cmd = "ssh %s@%s 'cat %s | sudo tee -a %s '" % username, ip_address, tmpfile, auth_key_path
        self.logger.info(
            "do the following on the console\nsudo -s\ncat %s >> %s" %
            (tmpfile, auth_key_path))
        self.logger.info(cmd)
        j.do.executeInteractive(cmd)

    def authorize_root(self, sftp_client, ip_address, keyname):
        tmppath = '/tmp/authorized_keys'
        auth_key_path = "/root/.ssh/authorized_keys"
        j.do.delete(tmppath)
        try:
            sftp_client.get(auth_key_path, tmppath)
        except Exception as e:
            if str(e).find("No such file") != -1:
                try:
                    auth_key_path += "2"
                    sftp_client.get(auth_key_path, tmppath)
                except Exception as e:
                    if str(e).find("No such file") != -1:
                        j.sal.fs.writeFile(tmppath, "")
                    else:
                        raise RuntimeError(
                            "Could not get authorized key,%s" % e)

            C = j.sal.fs.readFile(tmppath)
            Cnew = j.sal.fs.readFile(keyname)
            key = Cnew.split(" ")[1]
            if C.find(key) == -1:
                C2 = "%s\n%s\n" % (C.strip(), Cnew)
                C2 = C2.strip() + "\n"
                j.sal.fs.writeFile(tmppath, C2)
                self.logger.info("sshauthorized adjusted")
                sftp_client.put(tmppath, auth_key_path)
            else:
                self.logger.info("ssh key was already authorized")

    def SSHAuthorizeKey(
            self,
            remoteipaddr,
            keyname,
            login="root",
            passwd=None,
            sshport=22,
            removeothers=False):
        """
        this required ssh-agent to be loaded !!!
        the keyname is the name of the key as loaded in ssh-agent

        if remoteothers==True: then other keys will be removed
        """
        keyname = self.SSHEnsureKeyname(keyname=keyname, username=login)
        import paramiko
        paramiko.util.log_to_file("/tmp/paramiko.log")
        ssh = paramiko.SSHClient()

        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.logger.info("ssh connect:%s %s" % (remoteipaddr, login))

        if not self.SSHKeysListFromAgent(j.sal.fs.getBaseName(keyname)):
            self.SSHKeysLoad(self.getParent(keyname))
        ssh.connect(
            remoteipaddr,
            username=login,
            password=passwd,
            allow_agent=True,
            look_for_keys=False)
        self.logger.info("ok")

        ftp = ssh.open_sftp()

        if login != "root":
            self.authorize_user(
                sftp_client=ftp,
                ip_address=remoteipaddr,
                keyname=keyname,
                username=login)
        else:
            self.authorize_root(
                sftp_client=ftp,
                ip_address=remoteipaddr,
                keyname=keyname)

    def _loadSSHAgent(self, path=None, create_keys=False, kill_first=False):
        """
        check if ssh-agent is available & there is key loaded

        @param path: is path to private ssh key

        the primary key is 'id_rsa' and will be used as default e.g. if authorizing another node then this key will be used

        """
        # check if more than 1 agent
        socketpath = self._getSSHSocketpath()
        res = [
            item for item in j.do.execute(
                "ps aux|grep ssh-agent",
                False,
                False)[1].split("\n") if item.find("grep ssh-agent") == -
            1]
        res = [item for item in res if item.strip() != ""]
        res = [item for item in res if item[-2:] != "-l"]

        if len(res) > 1:
            self.logger.info("more than 1 ssh-agent, will kill all")
            kill_first = True
        if len(res) == 0 and j.sal.fs.exists(socketpath):
            j.do.delete(socketpath)

        if kill_first:
            cmd = "killall ssh-agent"
            # self.logger.info(cmd)
            j.do.execute(cmd, showout=False, outputStderr=False, die=False)
            # remove previous socketpath
            j.do.delete(socketpath)
            j.do.delete(j.do.joinPaths('/tmp', "ssh-agent-pid"))

        if not j.sal.fs.exists(socketpath):
            j.do.createDir(j.do.getParent(socketpath))
            # ssh-agent not loaded
            self.logger.info("load ssh agent")
            rc, result, err = j.do.execute(
                "ssh-agent -a %s" %
                socketpath, die=False, showout=False, outputStderr=False)

            if rc > 0:
                # could not start ssh-agent
                raise RuntimeError(
                    "Could not start ssh-agent, something went wrong,\nstdout:%s\nstderr:%s\n" %
                    (result, err))
            else:
                # get pid from result of ssh-agent being started
                if not j.sal.fs.exists(socketpath):
                    raise RuntimeError(
                        "Serious bug, ssh-agent not started while there was no error, should never get here")
                piditems = [item for item in result.split(
                    "\n") if item.find("pid") != -1]
                # print(piditems)
                if len(piditems) < 1:
                    print("results was:")
                    print(result)
                    print("END")
                    raise RuntimeError("Cannot find items in ssh-add -l")
                self._initSSH_ENV(True)
                pid = int(piditems[-1].split(" ")[-1].strip("; "))
                j.sal.fs.writeFile(
                    j.do.joinPaths(
                        '/tmp',
                        "ssh-agent-pid"),
                    str(pid))
                self._addSSHAgentToBashProfile()

            # ssh agent should be loaded because ssh-agent socket has been
            # found
            if os.environ.get("SSH_AUTH_SOCK") != socketpath:
                self._initSSH_ENV(True)
            rc, result, err = j.do.execute(
                "ssh-add -l", die=False, showout=False, outputStderr=False)
            if rc == 2:
                # no ssh-agent found
                print(result)
                raise RuntimeError(
                    "Could not connect to ssh-agent, this is bug, ssh-agent should be loaded by now")
            elif rc == 1:
                # no keys but agent loaded
                result = ""
            elif rc > 0:
                raise RuntimeError(
                    "Could not start ssh-agent, something went wrong,\nstdout:%s\nstderr:%s\n" %
                    (result, err))
        if path:
            path_found = j.sal.fs.exists(path)
            if not path_found and not create_keys:
                raise RuntimeError("key %s is not found" % path)

            if not path_found and create_keys:
                self.logger.info("Generating new key %s" % path)
                return_code, out, err = j.do.execute("ssh-keygen -t rsa -f %s -N \"\"" % path,
                                                    die=False,
                                                    showout=False,
                                                    outputStderr=False)
                if return_code != 0:
                    raise RuntimeError(
                        "Could not add key to the ssh-agent, \nstdout:%s\nstderr:%s\n" % (out, err))
            self.SSHKeyLoad(path)

        if path:
            path_found = j.sal.fs.exists(path)
            if not path_found and not createkeys:
                raise RuntimeError("key %s is not found" % path)

            if not path_found and createkeys:
                self.logger.info("Generating new key %s" % path)
                return_code, out, err = j.do.execute("ssh-keygen -t rsa -f %s -N \"\"" % path,
                                                    die=False,
                                                    showout=True,
                                                    outputStderr=True)
                if return_code != 0:
                    raise RuntimeError(
                        "Could not add key to the ssh-agent, \nstdout:%s\nstderr:%s\n" % (out, err))
            self.SSHKeyLoad(path)

    def SSHAgentAvailable(self):
        if not j.sal.fs.exists(self._getSSHSocketpath()):
            return False
        if "SSH_AUTH_SOCK" not in os.environ:
            self._initSSH_ENV(True)
        rc, out, err = j.do.execute(
            "ssh-add -l", showout=False, outputStderr=False, die=False)
        if 'The agent has no identities.' in out:
            return True
        if rc != 0:
            return False
        else:
            return True
