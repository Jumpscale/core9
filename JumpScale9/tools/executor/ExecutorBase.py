from JumpScale9 import j
try:
    import ujson as json
except ImportError:
    import json


class ExecutorBase:

    def __init__(self, debug=False, checkok=False):

        self.type = None
        self._id = None

        self.CURDIR = ""

        self.debug = debug
        self.checkok = checkok

        self._prefab = None
        self._config = None
        self._config_changed = False
        self._env = None
        self._logger = None

        self.readonly = False

    @property
    def logger(self):
        if self._logger is None:
            self._logger = j.logger.get("unknown")
        return self._logger

    @property
    def id(self):
        if self._id is None:
            raise j.exceptions.Input(message="self._id cannot be None", level=1, source="", tags="", msgpub="")
        return self._id

    @property
    def config(self):
        """
        is dict which is stored on node itself in json format in /tmp/jsexecutor.json
        """
        if self._config is None:
            if self.exists("$VARDIR/jsexecutor.json") == False:
                self._config = {}
            else:
                data = self.prefab.core.file_read("$VARDIR/jsexecutor.json")
                self._config = json.loads(data)

        return self._config

    def configGet(self, key, defval=None, set=False):
        """
        """
        if key in self.config:
            return self.config[key]
        else:
            if defval is not None:
                if set:
                    self.configSet(key, defval)
                return defval
            else:
                raise j.exceptions.Input(message="could not find config key:%s in executor:%s" %
                                         (key, self), level=1, source="", tags="", msgpub="")

    def configSet(self, key, val, save=True):
        """
        @return True if changed
        """
        if key in self.config:
            val2 = self.config[key]
        else:
            val2 = None
        if val != val2:
            self.config[key] = val
            # print("config changed")
            self._config_changed = True
            if save:
                self.configSave()
            return True
        else:
            return False

    def configSave(self):
        if self.readonly:
            raise j.exceptions.Input(message="cannot write config to '%s', because is readonly" %
                                     self, level=1, source="", tags="", msgpub="")
        if not self._config_changed:
            return
        data = json.dumps(self.config, sort_keys=True, indent=True)
        self.logger.info("config save")
        self.prefab.core.file_write("$VARDIR/jsexecutor.json", data, showout=False)
        self._config_changed = False

    def configReset(self):
        self._config = {}
        self.configSave()

    def cacheReset(self):
        self._config = None
        self._env = None

    def reset(self):
        self.configReset()
        self.cacheReset()

    @property
    def env(self):
        if self._env is None:
            res = {}
            _, out, _ = self.execute("printenv", showout=False)

            for line in out.splitlines():
                if '=' in line:
                    name, val = line.split("=", 1)
                    name = name.strip()
                    val = val.strip().strip("'").strip("\"")
                    res[name] = val
            self._env = res
        return self._env

    def docheckok(self, cmd, out):
        out = out.rstrip("\n")
        lastline = out.split("\n")[-1]
        if lastline.find("**OK**") == -1:
            raise j.exceptions.RuntimeError("Error in:\n%s\n***\n%s" % (cmd, out))
        out = "\n".join(out.split("\n")[:-1]).rstrip() + "\n"
        return out

    def _transformCmds(self, cmds, die=True, checkok=None, env={}):
        # print ("TRANSF:%s"%cmds)
        if cmds.find("\n") == -1:
            separator = ";"
        else:
            separator = "\n"

        pre = ""

        if checkok is None:
            checkok = self.checkok

        if die:
            if self.debug:
                pre += "set -ex\n"
            else:
                pre += "set -e\n"

        if self.CURDIR != "":
            pre += "cd %s\n" % (self.CURDIR)

        # need to do this cause by default sshd doesn't allow client to set
        # environment variable from the ssh session.
        if env != {}:
            for key, val in env.items():
                pre += "export %s='%s'\n" % (key, val)

        cmds = "%s\n%s" % (pre, cmds)

        if checkok:
            cmds += "\necho '**OK**'"

        cmds = cmds.replace("\n", separator).replace(";;", ";").strip(";")

        return cmds

    @property
    def prefab(self):
        if self._prefab is None:
            from js9 import j
            self._prefab = j.tools.prefab.get(self)
            self._prefab.executor = self
            try:
                self._prefab.sshclient = self.sshclient
            except BaseException:
                pass
        return self._prefab

    def exists(self, path):
        return self.prefab.core.exists(path)

    # interface to implement by child classes
    def execute(self, cmds, die=True, checkok=None, showout=True, timeout=0, env={}):
        raise NotImplementedError()

    def executeRaw(self, cmd, die=True, showout=False):
        raise NotImplementedError()
