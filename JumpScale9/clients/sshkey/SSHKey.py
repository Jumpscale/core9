
from js9 import j


TEMPLATE = """
pubkey = ""
allow_agent = true
passphrase_ = ""
privkey_ = ""
duration = 86400
path = ""
"""


JSConfigBase = j.tools.configmanager.base_class_config


class SSHKey(JSConfigBase):

    def __init__(self, instance, data={}, parent=None, interactive=True):
        self._connected = None
        JSConfigBase.__init__(self, instance=instance, data=data,
                              parent=parent, template=TEMPLATE, interactive=interactive)

        if "keys" in j.sal.fs.listDirsInDir(j.sal.fs.getcwd(), False, True, False, False):
            # means we are in directory where keys dir is found
            kpath = self.config.data["path"]
            if "/keys/" in kpath:
                # need to change the path to make sure that absolute path gets changed
                self.config.data = {"path": "keys/%s" % kpath.split("keys/")[1]}

        self._pubkey = ""
        self._privkey = ""
        self._agent = None

    @property
    def agent(self):

        def getagent(name):
            for item in j.clients.sshkey.sshagent.get_keys():
                if j.sal.fs.getBaseName(item.keyname) == name:
                    return item
            raise RuntimeError("Could not find agent for key with name:%s" % name)

        if self._agent is None:
            if not j.clients.sshkey.exists(self.instance):
                self.load()
            self._agent = getagent(self.instance)
        return self._agent

    @property
    def duration(self):
        return self.config.data["duration"]

    @duration.setter
    def duration(self, val):
        self.config._data["duration"] = int(val)
        self.config.save()

    @property
    def pubkey(self):
        if not self._pubkey:
            self._pubkey = self.config.data['pubkey']
            if not self._pubkey:
                path = '%s.pub' % (self.path)
                if not j.sal.fs.exists(path):
                    cmd = 'ssh-keygen -f {} -y > {}'.format(self.path, path)
                    j.sal.process.execute(cmd)
                self._pubkey = j.sal.fs.fileGetContents(path)
                self.config.data = {"pubkey": self._pubkey}
                self.config.save()
        return self._pubkey

    @pubkey.setter
    def pubkey(self, val):
        self.config._data["pubkey"] = str(val)
        self.config.save()
        self._pubkey = None

    @property
    def privkey(self):
        _privkey = self.config.data['privkey_']
        if not _privkey:
            _privkey = j.sal.fs.fileGetContents(self.path)
            self.config.data = {"privkey_": _privkey}
            self.config.save()
        return _privkey

    @privkey.setter
    def privkey(self, val):
        self.config.data = {"privkey_": str(val)}
        self.config.save()
        self._pubkey = None

    @property
    def passphrase(self):
        return self.config.data["passphrase_"]

    @passphrase.setter
    def passphrase(self, val):
        self.config.data = {"passphrase_": str(val)}
        self.config.save()

    @property
    def allow_agent(self):
        return self.config.data["allow_agent"]

    @allow_agent.setter
    def allow_agent(self, val):
        self.config._data["allow_agent"] = bool(val)
        self.config.save()

    @property
    def path(self):
        if self.config._data['path']:
            return self.config.data['path']
        else:
            path = j.sal.fs.joinPaths(j.dirs.HOMEDIR, ".ssh", self.instance)
            return path

    def delete(self):
        """
        will delete from ~/.ssh dir as well as from config
        """
        self.logger.debug("delete:%s" % self.instance)
        self.config.delete()
        self.delete_from_sshdir()

    def delete_from_sshdir(self):
        j.sal.fs.remove("%s.pub" % self.path)
        j.sal.fs.remove("%s" % self.path)

    def write_to_sshdir(self):
        j.sal.fs.writeFile(self.path, self.privkey)
        j.sal.fs.writeFile(self.path + ".pub", self.pubkey)

    def generate(self, reset=False):
        self.logger.debug("generate ssh key")
        if reset:
            self.delete_from_sshdir()
        else:
            if not j.sal.fs.exists(self.path):
                if self.config._data["privkey_"] != "":
                    if not self.config._data['pubkey']:
                        self.write_to_sshdir()

        if not j.sal.fs.exists(self.path) or reset:
            cmd = 'ssh-keygen -t rsa -f %s -q -P "%s"' % (self.path, self.passphrase)
            j.sal.process.execute(cmd, timeout=10)

        self.privkey = self.privkey  # will save it in config, looks weird but is correct
        self.pubkey = self.pubkey  # will save it in config
        # self.save()

    def sign_ssh_data(self, data):
        return self.agent.sign_ssh_data(data)

    def load(self, duration=3600 * 24):
        """
        load ssh key in ssh-agent, if no ssh-agent is found, new ssh-agent will be started
        """
        # self.generate()
        self.logger.debug("load sshkey: %s for duration:%s" % (self.instance, duration))
        j.clients.sshkey.key_load(self.path, passphrase=self.passphrase, returnObj=False, duration=duration)

    def unload(self):
        cmd = "ssh-add -d %s " % (self.path)
        j.sal.process.executeInteractive(cmd)

    def is_loaded(self):
        """
        check if key is loaded in the ssh agent
        """
        if self.instance in j.clients.sshkey.listnames():
            self.logger.debug("ssh key: %s loaded", self.instance)
            return True

        self.logger.debug("ssh key: %s is not loaded", self.instance)
        return False
