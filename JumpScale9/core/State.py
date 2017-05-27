import pytoml
from JumpScale9 import j
import os

# ONLY DEVELOPED NOW FOR CONFIG, REST NEEDS TO BE DONE


class State():

    def __init__(self):
        self.readonly = False
        self._db = None
        self._config = None
        self._config_changed = False
        self.__jslocation__ = "j.core.state"

    @property
    def db(self):
        return None
        if self._db is None and j.clients is not None:
            self._db = j.clients.redis.get4core()
        return self._db

    @property
    def _vardir(self):
        if "VARDIR" in os.environ:
            return os.path.normpath(os.path.join(os.environ["VARDIR"]))
        else:
            raise RuntimeError("Cannot find VARDIR in env")

    @property
    def config(self):
        if self._config is None:
            if not self._exists("cfg"):
                self._config = {}
                self._config_changed = True
            else:
                data = self._get("cfg")
                self._config = pytoml.loads(data)
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
            print("config set %s:%s" % (key, val))
            # print("config changed")
            self._config_changed = True
            if save:
                self.configSave()
            return True
        else:
            if save:
                self.configSave()
            return False

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
                        self._config[key0][key1] = val1
                        self._config_changed = True
                    else:
                        if overwrite:
                            self._config[key0][key1] = val1
                            self._config_changed = True
        self.configSave()

    def configSave(self):
        if self.readonly:
            raise j.exceptions.Input(
                message="cannot write config to '%s', because is readonly" %
                self, level=1, source="", tags="", msgpub="")
        # if not self._config_changed:
        #     return
        data = pytoml.dumps(self.config, sort_keys=True)
        # self.logger.info("config save")
        self._set("cfg", data)
        self._config_changed = False

    def resetConfig(self):
        self._config = {}
        self.configSave()

    def resetState(self):
        from IPython import embed
        print("DEBUG NOW resetState")
        embed()
        raise RuntimeError("stop debug here")

    def resetCache(self):
        from IPython import embed
        print("DEBUG NOW reset cache")
        embed()
        raise RuntimeError("stop debug here")

    def resetAll(self):
        self.resetState()
        self.resetCache()
        self.resetConfig()

    def _getpath(self, cat="cfg", key=None):
        if cat == "cfg":
            path = "%s/cfg/jumpscale9.toml" % self._vardir
            if key is not None:
                raise RuntimeError("key has to be None of cat==cfg")
        elif cat == "cache":
            path = "%s/cache/%s" % (self._vardir, key)
        elif cat == "state":
            path = "%s/state/%s" % (self._vardir, key)
        else:
            raise RuntimeError("only supported categories: cfg,cache,state")
        return path

    def _set(self, cat="cfg", data="", key=None):
        if self.db is not None:
            from IPython import embed
            print("DEBUG NOW sdat")
            embed()
            raise RuntimeError("stop debug here")
        else:
            path = self._getpath(cat=cat, key=key)
            j.sal.fs.createDir(j.sal.fs.getDirName(path))
            j.sal.fs.writeFile(filename=path, contents=data, append=False)

    def _exists(self, cat="cfg", data="", key=None):
        if self.db is not None:
            from IPython import embed
            print("DEBUG NOW wewe")
            embed()
            raise RuntimeError("stop debug here")
        else:
            path = self._getpath(cat=cat, key=key)
            return os.path.exists(path)

    def _get(self, cat="cfg", data="", key=None):
        if self.db is not None:
            from IPython import embed
            print("DEBUG NOW 2323")
            embed()
            raise RuntimeError("stop debug here")
        else:
            path = self._getpath(cat=cat, key=key)
            with open(path, 'r') as f:
                return f.read()
