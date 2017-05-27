from js9 import j
import re
from io import StringIO
import os


class Profile:
    env_pattern = re.compile(r'^([^=\n]+)="([^"\n]+)"$', re.MULTILINE)
    include_pattern = re.compile(r'^source (.*)$', re.MULTILINE)

    def __init__(self, bash, profilePath=""):
        """
        X="value"
        Y="value"
        PATH="p1:p2:p3"

        export X
        export Y
        """
        self.bash = bash
        if profilePath == "":
            self.pathProfile = j.sal.fs.joinPaths(self.home, ".profile_js")
        else:
            self.pathProfile = profilePath

        self.load()

    def load(self):
        self.home = self.bash.home
        self.prefab = self.bash.prefab
        self._env = {}
        self._path = []
        self._includes = []

        content = self.prefab.core.file_read(self.pathProfile)

        for match in Profile.env_pattern.finditer(content):
            self._env[match.group(1)] = match.group(2)
        for match in Profile.include_pattern.finditer(content):
            self._includes.append(match.group(1))

        # load path
        if 'PATH' in self._env:
            path = self._env['PATH']
            _path = set(path.split(':'))
        else:
            _path = set()
        # make sure to add the js bin dir to the path
        if "SSHKEYNAME" not in self._env:
            self._env['SSHKEYNAME'] = os.environ.get('SSHKEYNAME', 'id_rsa')
        if "HOMEDIR" not in self._env:
            self._env['HOMEDIR'] = os.environ.get('HOMEDIR', os.environ.get('HOME', '/root'))
        _path.add(self.prefab.core.dir_paths['BINDIR'])

        for item in _path:
            if item.strip() == "":
                continue
            if item.find("{PATH}") != -1:
                continue
            self.addPath(item)

        self._env.pop('PATH', None)

    def addPath(self, path):
        path = path.strip()
        path = path.replace("//", "/")
        path = path.replace("//", "/")
        path = path.rstrip("/")
        if path not in self._path:
            self._path.append(path)

    def addInclude(self, path):
        path = path.strip()
        path = path.replace("//", "/")
        path = path.replace("//", "/")
        path = path.rstrip("/")
        if path not in self._includes:
            self._includes.append(path)

    @property
    def paths(self):
        return list(self._path)

    def envSet(self, key, value):
        self._env[key] = value

    def envGet(self, key):
        return self._env[key]

    def envExists(self, key):
        return key in self._env

    def envDelete(self, key):
        del self._env[key]

    def envDeleteAll(self, key):
        """
        dangerous function will look for env argument which has been set in the profile
        if found will delete
        and will do this multiple times to make sure all instances are found
        """
        while self.envExists(key):
            self.envDelete(key)

    def deleteAll(self, key):
        while self.envExists(key):
            path = self.envGet(key)
            if path in self.paths:
                self._path.pop(self._path.index(path))
            self.envDelete(key)

    def pathDelete(self, filter):
        """
        @param filter e.g. /go/
        """
        for path in self.paths:
            if path.find(filter) != -1:
                self._path.pop(self._path.index(path))

    def deletePathFromEnv(self, key):
        """
        dangerous function will look for env argument which has been set in the profile
        if found will delete
        and will do this multiple times to make sure all instances are found
        """
        while self.envExists(key):
            path = self.envGet(key)
            self.prefab.core.dir_remove(path)
            self.envDelete(key)

    def __str__(self):
        self._env['PATH'] = ':'.join(set(self.paths)) + ":${PATH}"

        content = StringIO()
        content.write('# environment variables\n')
        for key, value in self._env.items():
            content.write('%s="%s"\n' % (key, value))
            content.write('export %s\n\n' % key)

        content.write('# includes\n')
        for path in self._includes:
            content.write('source %s\n' % path)

        self._env.pop('PATH')

        return content.getvalue()

    __repr__ = __str__

    @property
    def env(self):
        return self._env

    def replace(self, text):
        """
        will look for $ENVNAME 's and replace them in text
        """
        for key, val in self.env.items():
            text = text.replace("$%s" % key, val)
        return text

    def save(self, includeInDefaultProfile=True):
        """
        save to disk
        @param includeInDefaultProfile, if True then will include in the default profile
        """

        self.prefab.core.file_write(self.pathProfile, str(self), showout=True)

        # make sure we include our custom profile in the default
        if includeInDefaultProfile is True:
            if self.pathProfile != self.bash.profileDefault.pathProfile:
                print("INCLUDE IN DEFAULT PROFILE:%s" % self.pathProfile)
                out = ""
                inProfile = self.prefab.core.file_read(self.bash.profileDefault.pathProfile)
                for line in inProfile.split("\n"):
                    if line.find(self.pathProfile) != -1:
                        continue
                    out += "%s\n" % line

                out += "\nsource %s\n" % self.pathProfile
                if out.replace("\n", "") != inProfile.replace("\n", ""):
                    self.prefab.core.file_write(self.bash.profileDefault.pathProfile, out)
                    self.bash.profileDefault.load()

        self.bash.reset()  # do not remove !

    def getLocaleItems(self, force=False, showout=False):
        out = self.prefab.core.run("locale -a")[1]
        return out.split("\n")

    def fixlocale(self):
        items = self.getLocaleItems()
        if "en_US.UTF-8" in items or "en_US.utf8" in items:
            self.envSet("LC_ALL", "en_US.UTF-8")
            self.envSet("LANG", "en_US.UTF-8")
            return
        elif "C.UTF-8" in items or "c.utf8" in items:
            self.envSet("LC_ALL", "C.UTF-8")
            self.envSet("LANG", "C.UTF-8")
            return

        raise j.exceptions.Input("Cannot find C.UTF-8, cannot fix locale's")


class BashFactory:

    def __init__(self):
        self.__jslocation__ = "j.tools.bash"

    def get(self, executor=None):
        """
        if executor==None then will be local
        """
        b = Bash(executor=executor)
        return b


class Bash:

    def __init__(self, executor=None):
        if executor is not None:
            self.executor = executor
        else:
            self.executor = j.tools.executorLocal

        self.prefab = self.executor.prefab
        self.reset()

    def reset(self):
        self._profile = None
        self._profileDefault = None

    @property
    def env(self):
        return self.executor.env

    @property
    def home(self):
        return self.executor.prefab.core.dir_paths["HOMEDIR"]

    def cmdGetPath(self, cmd, die=True):
        """
        checks cmd Exists and returns the path
        """
        rc, out, err = self.prefab.core.run("which %s" % cmd, die=False, showout=False, profile=True)
        if rc > 0:
            if die:
                raise j.exceptions.RuntimeError("Did not find command: %s" % cmd)
            else:
                return False
        return out.split("\n")[-1]

    def profileGet(self, path="~/.profile_js"):
        path = path.replace("~", self.home)
        if not self.prefab.core.file_exists(path):
            self.prefab.core.file_write(path, "")
        return Profile(self, path)

    @property
    def profileJS(self):
        """
        profile which we write for jumpscale std in ~/.profile_js
        """
        if self._profile is None:
            self._profile = self.profileGet()
        return self._profile

    @property
    def profileDefault(self):
        if self._profileDefault is None:
            path = ""
            for attempt in [".profile", ".bash_profile"]:
                ppath = j.sal.fs.joinPaths(self.home, attempt)
                if self.prefab.core.file_exists(ppath):
                    path = ppath
            if path == "":
                path = "~/.bash_profile"
            self._profileDefault = self.profileGet(path)
        return self._profileDefault

    @property
    def profilePath(self):
        return self.profileDefault.pathProfile

    def fixlocale(self):
        self.prefab.bash.profileJS.fixlocale()
        self.prefab.bash.profileJS.save(True)  # will make sure it gets in default profile

    def envSet(self, key, val):
        self.prefab.bash.profileJS.envSet(key, val)
        self.prefab.bash.profileJS.save(True)

    def envGet(self, key):
        return self.prefab.bash.profileJS.envGet(key)

    def envDelete(self, key):
        return self.prefab.bash.profileJS.envDelete(key)
