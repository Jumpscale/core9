import pytoml
from JumpScale9 import j
import sys
import os


class State():
    """

    """

    def __init__(self, executor):
        self.readonly = False
        self.executor = executor
        # if self.executor==j.tools.executorLocal:
        if self.executor.exists("/etc/") and self.executor.platformtype.isMac == False:
            self.configPath = "/etc/jumpscale9.toml"
        else:
            self.configPath = "%s/js9host/jumpscale9.toml" % self.executor.env["HOME"]

        if self.executor == j.tools.executorLocal:
            if j.sal.fs.exists(self.configPath):
                # print("config load state local:%s"%self.configPath)
                table_open_object = open(self.configPath, 'r')
                self.config = pytoml.load(table_open_object)
            else:
                self.config = {}
        else:
            if self.executor.exists(self.configPath):
                # print("config load state ssh: %s"%self.configPath)
                cc = self.executor.file_read(self.configPath)
                self.config = pytoml.loads(cc)
            else:
                self.config = {}

    @property
    def versions(self):
        versions = {}
        for name, path in self.config.get('plugins', {}).items():
            repo = j.clients.git.get(path)
            _, versions[name] = repo.getBranchOrTag()
        return versions

    @property
    def db(self):
        return None
        if self._db is None and j.clients is not None:
            self._db = j.clients.redis.get4core()
        return self._db


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
                raise j.exceptions.Input(
                    message="could not find config key:%s in executor:%s" %
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
            # print("config set %s:%s" % (key, val))
            # print("config changed")
            self._config_changed = True
            if save:
                self.configSave()
            return True
        else:
            if save:
                self.configSave()
            return False

    def configSetInDict(self, key, dkey, dval):
        """
        will check that the val is a dict, if not set it and put key & val in
        """
        if key in self.config:
            val2 = self.config[key]
        else:
            self.configSet(key, {}, save=True)
            val2 = {}
        if dkey in val2:
            if val2[dkey] != dval:
                self._config_changed = True
        else:
            self._config_changed = True

        val2[dkey] = dval

        self.config[key] = val2
        # print("config set dict %s:%s:%s" % (key, dkey, dval))
        self.configSave()

    def configGetFromDict(self, key, dkey, default=None):
        """
        get val from subdict
        """
        if key not in self.config:
            print(8887)
            from IPython import embed
            embed(colors='Linux')
            self.configSet(key, val={}, save=True)

        if dkey not in self.config[key]:
            if default is not None:
                return default
            raise RuntimeError(
                "Cannot find dkey:%s in state config for dict '%s'" % (dkey, key))

        return self.config[key][dkey]

    def configGetFromDictBool(self, key, dkey, default=None):
        if key not in self.config:
            self.configSet(key, val={}, save=True)

        if dkey not in self.config[key]:
            if default is not None:
                return default
            raise RuntimeError(
                "Cannot find dkey:%s in state config for dict '%s'" % (dkey, key))

        val = self.config[key][dkey]
        if val in [1, True] or val.strip().lower() in ["true", "1", "yes", "y"]:
            return True
        else:
            return False

    def configSetInDictBool(self, key, dkey, dval):
        """
        will check that the val is a dict, if not set it and put key & val in
        """
        if dval in [1, True] or dval.strip().lower() in ["true", "1", "yes", "y"]:
            dval = "1"
        else:
            dval = "0"
        return configSetInDict(key, dkey, dval)

    def configUpdate(self, ddict, overwrite=True):
        """
        will walk over  2 levels deep of dict & update
        """
        for key0, val0 in ddict.items():
            if key0 not in self.config:
                self.configSet(key0, val0, save=False)
            else:
                if not j.data.types.dict.check(val0):
                    raise RuntimeError(
                        "first level in config needs to be a dict ")
                for key1, val1 in val0.items():
                    if key1 not in self.config[key0]:
                        self.config[key0][key1] = val1
                        self._config_changed = True
                    else:
                        if overwrite:
                            self.config[key0][key1] = val1
                            self._config_changed = True
        self.configSave()

    def configSave(self):
        if self.readonly:
            raise j.exceptions.Input(
                message="cannot write config to '%s', because is readonly" %
                self, level=1, source="", tags="", msgpub="")
        if self.executor == j.tools.executorLocal:
            print("configsave state on %s" % self.configPath)
            path = self.configPath
            table_open_object = open(path, 'w')
            data = pytoml.dump(self.config, table_open_object, sort_keys=True)
        else:
            print("configsave state")
            data = pytoml.dumps(self.config)
            if not self.executor.authorizing:
                self.executor.file_write(self.configPath, data)

    def reset(self):
        self.config = {}
        self.configSave()

    def __repr__(self):
        return str(self.config)

    def __str__(self):
        return str(self.config)
