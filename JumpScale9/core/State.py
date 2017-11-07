import pytoml
from JumpScale9 import j
import sys
import os


class State():
    """

    """

    def __init__(self, executor, configPath=""):
        self.readonly = False
        self.executor = executor
        self.load()

    def load(self, reset=False):
        if reset:
            self.executor.reset()
        self.configJSPath = self.executor.stateOnSystem["path_jscfg"] + \
            "/jumpscale9.toml"
        self.configStatePath = self.executor.stateOnSystem["path_jscfg"] + "/state.toml"
        self.configMePath = self.executor.stateOnSystem["path_jscfg"] + "/me.toml"
        self._configState = self.executor.stateOnSystem["cfg_state"]
        self._configJS = self.executor.stateOnSystem["cfg_js9"]
        self.configMe = self.executor.stateOnSystem["cfg_me"]

    @property
    def cfgPath(self):
        return self.executor.stateOnSystem["path_jscfg"]

    @property
    def versions(self):
        versions = {}
        for name, path in self.config.get('plugins', {}).items():
            repo = j.clients.git.get(path)
            _, versions[name] = repo.getBranchOrTag()
        return versions

    def stateSet(self, key, val, save=True):
        return self._set(key=key, val=val, save=save, config=self._configState, path=self.configStatePath)


    def stateGet(self, key, defval=None, set=False):
        return self._get(key=key, defval=defval, set=set, config=self._configState, path=self.configStatePath)

    def configGet(self, key, defval=None, set=False):
        return self._get(key=key, defval=defval, set=set, config=self._configJS, path=self.configJSPath)

    def configSet(self, key, val, save=True):
        return self._set(key=key, val=val, save=save, config=self._configJS, path=self.configJSPath)

    @property
    def mascot(self):
        mascotpath = "%s/.mascot.txt" % os.environ["HOME"]
        if not j.sal.fs.exists(mascotpath):
            print("env has not been installed properly (missing mascot), please follow init instructions on https://github.com/Jumpscale/core9")
            sys.exit(1)
        return j.sal.fs.readFile(mascotpath)

    @property
    def db(self):
        return None
        if self._db is None and j.clients is not None:
            self._db = j.clients.redis.get4core()
        return self._db

    def _get(self, key, defval=None, set=False, config=None, path=""):
        """
        """
        if key in config:
            return config[key]
        else:
            if defval is not None:
                if set:
                    self._set(key, defval, config=config, path=path)
                return defval
            else:
                raise j.exceptions.Input(
                    message="could not find config key:%s in executor:%s" %
                    (key, self), level=1, source="", tags="", msgpub="")

    def _set(self, key, val, save=True, config=None, path=""):
        """
        @return True if changed
        """
        if key in config:
            val2 = config[key]
        else:
            val2 = None
        if val != val2:
            config[key] = val
            # print("config set %s:%s" % (key, val))
            # print("config changed")
            self._config_changed = True
            if save:
                self.configSave(path)
            return True
        else:
            if save:
                self.configSave(path)
            return False
    def configSetInDict(self, key, dkey, dval):
        self._setInDict(key=key, dkey=dkey, dval=dval, config=self._configJS, path=self.configJSPath)

    def stateSetInDict(self, key, dkey, dval):
        self._setInDict(key=key, dkey=dkey, dval=dval, config=self._configState, path=self.configStatePath)

    def _setInDict(self, key, dkey, dval, config, path=""):
        """
        will check that the val is a dict, if not set it and put key & val in
        """
        if key in config:
            val2 = config[key]
        else:
            self._set(key, {}, save=True, config=config, path=path)
            val2 = {}
        if dkey in val2:
            if val2[dkey] != dval:
                self._config_changed = True
        else:
            self._config_changed = True

        val2[dkey] = dval

        config[key] = val2
        # print("config set dict %s:%s:%s" % (key, dkey, dval))
        self.configSave(path)

    def configGetFromDict(self, key, dkey, default=None):
        return self._getFromDict(key=key, dkey=dkey, default=default, config=self._configJS, path=self.configJSPath)

    def stateGetFromDict(self, key, dkey, default=None):
        return self._getFromDict(key=key, dkey=dkey, default=default, config=self._configState, path=self.configStatePath)

    def _getFromDict(self, key, dkey, default=None, config=None, path=""):
        """
        get val from subdict
        """
        if key not in config:
            self._set(key, val={}, save=True, config=config, path=path)

        if dkey not in config[key]:
            if default is not None:
                return default
            raise RuntimeError(
                "Cannot find dkey:%s in state config for dict '%s'" % (dkey, key))

        return config[key][dkey]

    def configGetFromDictBool(self, key, dkey, default=None):
        self._getFromDictBool(key=key, dkey=dkey, default=default, config=self._configJS)

    def stateGetFromDictBool(self, key, dkey, default=None):
        self._getFromDictBool(key=key, dkey=dkey, default=default, config=self._configState)

    def _getFromDictBool(self, key, dkey, default=None, config=None, path=""):
        if key not in config:
            self._set(key, val={}, save=True, config=config, path=path)

        if dkey not in config[key]:
            if default is not None:
                return default
            raise RuntimeError(
                "Cannot find dkey:%s in state config for dict '%s'" % (dkey, key))

        val = config[key][dkey]
        if val in [1, True] or val.strip().lower() in ["true", "1", "yes", "y"]:
            return True
        else:
            return False

    def configSetInDictBool(self, key, dkey, dval):
        self._setInDictBool(key=key, dkey=dkey, dval=dval, config=self._configJS, path=self.configJSPath)

    def stateSetInDictBool(self, key, dkey, dval):
        self._setInDictBool(key=key, dkey=dkey, dval=dval, config=self._configState, path=self.configStatePath)

    def _setInDictBool(self, key, dkey, dval, config, path):
        """
        will check that the val is a dict, if not set it and put key & val in
        """
        if dval in [1, True] or str(dval).strip().lower() in ["true", "1", "yes", "y"]:
            dval = "1"
        else:
            dval = "0"
        return self._setInDict(key, dkey, dval, config, path)

    def configUpdate(self, ddict, overwrite=True):
        """
        will walk over  2 levels deep of dict & update
        """
        for key0, val0 in ddict.items():
            if key0 not in self._configJS:
                self.configSet(key0, val0, save=False)
            else:
                if not j.data.types.dict.check(val0):
                    raise RuntimeError(
                        "first level in config needs to be a dict ")
                for key1, val1 in val0.items():
                    if key1 not in self._configJS[key0]:
                        self._configJS[key0][key1] = val1
                        self._config_changed = True
                    else:
                        if overwrite:
                            self._configJS[key0][key1] = val1
                            self._config_changed = True
        self.configSave()

    def configSave(self, config=None, path=""):
        """
        if in container write: /hostcfg/me.toml
        if in host write: ~/js9host/cfg/me.toml
        """
        print("configsave")
        if self.readonly:
            raise j.exceptions.Input(
                message="cannot write config to '%s', because is readonly" %
                self, level=1, source="", tags="", msgpub="")
        if config and path:
            data = pytoml.dumps(config)
            self.executor.file_write(path, data)
            return
        data = pytoml.dumps(self._configJS)
        self.executor.file_write(self.configJSPath, data)
        data = pytoml.dumps(self.configMe)
        self.executor.file_write(self.configMePath, data)
        data = pytoml.dumps(self._configState)
        self.executor.file_write(self.configStatePath, data)

    def reset(self):
        self._configJS = {}
        self._configState = {}
        self.configSave()

    def __repr__(self):
        return str(self._configJS)

    def __str__(self):
        return str(self._configJS)
