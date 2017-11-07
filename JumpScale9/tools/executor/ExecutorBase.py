from JumpScale9 import j
try:
    import ujson as json
except ImportError:
    import json

import pytoml
import pystache
import hashlib
import base64


class ExecutorBase:

    def __init__(self, debug=False, checkok=True):

        # print ("*****************")

        self.debug = debug
        self.checkok = checkok
        self.type = None
        self._id = None
        self.readonly = False
        self.CURDIR = ""
        self._logger = None
        self.reset()

    def reset(self):
        self._iscontainer = None
        self._state = None
        self._stateOnSystem = None
        self._prefab = None

    @property
    def state(self):
        if self._state is None:
            from JumpScale9.core.State import State
            self._state = State(self)
        return self._state

    @property
    def logger(self):
        if self._logger is None:
            self._logger = j.logger.get("executor")
        return self._logger

    @property
    def id(self):
        if self._id is None:
            raise RuntimeError("self._id cannot be None")
        return self._id

    @property
    def env(self):
        return self.stateOnSystem["env"]

    def docheckok(self, cmd, out):
        out = out.rstrip("\n")
        lastline = out.split("\n")[-1]
        if lastline.find("**OK**") == -1:
            raise RuntimeError("Error in:\n%s\n***\n%s" % (cmd, out))
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

        if env != {}:
            for key, val in env.items():
                pre += "%s=%s%s" % (key, val, separator)

        cmds = "%s\n%s" % (pre, cmds)

        if checkok:
            cmds += "\necho '**OK**'"

        cmds = cmds.replace("\n", separator).replace(";;", ";").strip(";")

        return cmds

    @property
    def prefab(self):
        if self._prefab is None:
            # from js9 import j
            self._prefab = j.tools.prefab.get(self)
            # self._prefab.executor = self
            # try:
            #     self._prefab.sshclient = self.sshclient
            # except BaseException:
            #     pass
        return self._prefab

    def exists(self, path):
        if path == "/env.sh":
            raise RuntimeError("SS")

        def check():
            rc, _, _ = self.execute('test -e %s' %
                                    path, die=False, showout=False)
            if rc > 0:
                return False
            else:
                return True
        return self.cache.get("exists:%s" % path, check)

    def configSave(self):
        """
        Config Save
        """
        if self.type == "local":
            j.core.state = self._state
        self.state.configSave()

    # interface to implement by child classes
    def execute(self, cmds, die=True, checkok=None, showout=True, timeout=0, env={}):
        raise NotImplementedError()

    def executeRaw(self, cmd, die=True, showout=False):
        raise NotImplementedError()

    @property
    def isDebug(self):
        return self.state.configGetFromDict("system", "debug") == "1" or self.state.configGetFromDict("system", "debug") == 1 or self.state.configGetFromDict("system", "debug") == True or self.state.configGetFromDict("system", "debug") == "true"

    @property
    def isContainer(self):
        """
        means we don't work with ssh-agent ...
        """
        return self.stateOnSystem["iscontainer"]

    @property
    def stateOnSystem(self):
        """
        is dict of all relevant param's on system
        """
        if self._stateOnSystem is None:
            C = """
            set +ex
            ls "/root/.iscontainer"  > /dev/null 2>&1 && echo 'ISCONTAINER = 1' || echo 'ISCONTAINER = 0'
            echo UNAME = \""$(uname -mnprs)"\"


            if [ "$(uname)" == "Darwin" ]; then
                export PATH_JSCFG="$HOME/js9host/cfg"
            elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
                export PATH_JSCFG="$HOME/js9host/cfg"
            else
                die "platform not supported"
            fi
            echo PATH_JSCFG = \"$PATH_JSCFG\"

            echo "PATH_HOME = $HOME"
            echo HOSTNAME = "$(hostname)"

            lsmod > /dev/null 2>&1|grep vboxdrv |grep -v grep  > /dev/null 2>&1 && echo 'VBOXDRV=1' || echo 'VBOXDRV=0'


            #OS
            apt-get -v > /dev/null 2>&1 && echo 'OS_TYPE="ubuntu"'
            test -f /etc/arch-release > /dev/null 2>&1 && echo 'OS_TYPE="arch"'
            test -f /etc/redhat-release > /dev/null 2>&1 && echo 'OS_TYPE="redhat"'
            apk -v > /dev/null 2>&1 && echo 'OS_TYPE="alpine"'
            brew -v > /dev/null 2>&1 && echo 'OS_TYPE="darwin"'
            cat /etc/os-release | grep "VERSION_ID"

            echo "CFG_ME = --TEXT--"
            cat $PATH_JSCFG/me.toml 2>/dev/null || echo ""
            echo --TEXT--

            echo "CFG_JS9 = --TEXT--"
            cat $PATH_JSCFG/jumpscale9.toml 2>/dev/null || echo ""
            echo --TEXT--

            echo "CFG_STATE = --TEXT--"
            cat $PATH_JSCFG/state.toml 2> /dev/null || echo ""
            echo --TEXT--

            echo "BASHPROFILE = --TEXT--"
            cat $HOME/.profile_js 2>/dev/null || echo ""
            echo --TEXT--

            echo "ENV = --TEXT--"
            export
            echo --TEXT--

            """
            C = j.data.text.strip(C)
            rc, out, err = self.execute(C, showout=False, hide=True)

            res = {}
            state = ""
            for line in out.split("\n"):
                if line.find("--TEXT--") != -1 and line.find("=") != -1:
                    varname = line.split("=")[0].strip().lower()
                    state = "TEXT"
                    txt = ""
                    continue

                if state == "TEXT":
                    if line.strip() == "--TEXT--":
                        res[varname] = txt
                        state = ""
                        continue
                    else:
                        txt += line + "\n"
                        continue

                if "=" in line:
                    varname, val = line.split("=", 1)
                    varname = varname.strip().lower()
                    val = str(val).strip().strip("\"")
                    if val.lower() in ["1", "true"]:
                        val = True
                    elif val.lower() in ["0", "false"]:
                        val = False
                    else:
                        try:
                            val = int(val)
                        except:
                            pass
                    res[varname] = val

            if res["cfg_js9"].strip() != "":
                try:
                    res["cfg_js9"] = pytoml.loads(res["cfg_js9"])
                except Exception as e:
                    raise RuntimeError(
                        "Could not load jumpscale config file (pytoml error)\n%s\n" % res["cfg_js9"])
            else:
                res["cfg_js9"] = {}
            if res["cfg_state"].strip() != "":
                try:
                    res["cfg_state"] = pytoml.loads(res["cfg_state"])
                except Exception as e:
                    raise RuntimeError(
                        "Could not load jumpscale config file (pytoml error)\n%s\n" % res["cfg_state"])

            else:
                res["cfg_state"] = {}

            if res["cfg_me"].strip() != "":
                try:
                    res["cfg_me"] = pytoml.loads(res["cfg_me"])
                except Exception as e:
                    raise RuntimeError(
                        "Could not load me config file (pytoml error)\n%s\n" % res["cfg_me"])
            else:
                res["cfg_me"] = {}

            envdict = {}
            for line in res["env"].split("\n"):
                line = line.replace("declare -x", "")
                line = line.strip()
                if line.strip() == "":
                    continue
                if "=" in line:
                    pname, pval = line.split("=", 1)
                    pval = pval.strip("'").strip("\"")
                    envdict[pname.strip()] = pval.strip()

            res["env"] = envdict

            self._stateOnSystem = res

        return self._stateOnSystem

    def enableDebug(self):
        self.state.configSetInDictBool("system", "debug", True)
        self.state.configSave()
        self.cache.reset()

    def _getDirPathConfig(self):

        if self.isContainer:
            T = '''
            BASEDIR = "/opt"
            CODEDIR = "/opt/code"
            HOSTDIR = "/host"
            HOSTCFGDIR = "/hostcfg"
            CFGDIR = "{{HOSTCFGDIR}}"
            VARDIR = "{{HOSTDIR}}/var"
            '''
        elif self.platformtype.isMac:
            T = '''
            BASEDIR = "{{HOMEDIR}}/opt"
            CODEDIR = "{{HOMEDIR}}/code"
            HOSTDIR = "{{HOMEDIR}}/js9host/"
            HOSTCFGDIR = "{{HOMEDIR}}/js9host/cfg/"
            CFGDIR = "{{HOSTCFGDIR}}"
            VARDIR = "{{BASEDIR}}/var"
            '''
        else:
            T = '''
            BASEDIR = "/opt"
            CODEDIR = "/opt/code"
            HOSTDIR = "{{HOMEDIR}}/js9host/"
            HOSTCFGDIR = "{{HOMEDIR}}/js9host/cfg/"
            CFGDIR = "{{BASEDIR}}/cfg"
            VARDIR = "{{BASEDIR}}/var"
            '''

        BASE = '''
        HOMEDIR = "~"
        TMPDIR = "{{TMPDIR}}"
        BASEDIRJS = "{{BASEDIR}}/jumpscale9"
        JSAPPSDIR= "{{BASEDIRJS}}/apps"
        TEMPLATEDIR ="{{VARDIR}}/templates"
        DATADIR = "{{VARDIR}}/data"
        BUILDDIR = "{{VARDIR}}/build"
        LIBDIR = "{{BASEDIR}}/lib/"
        LOGDIR = "{{VARDIR}}/log"
        BINDIR="{{BASEDIR}}/bin"
        '''

        TXT = j.data.text.strip(BASE) + "\n" + j.data.text.strip(T)

        return self._replaceInToml(TXT)

    def _replaceInToml(self, T):
        T = T.replace("~", self.env["HOME"])
        # T = T.replace("{{TMPDIR}}", self.env["TMPDIR"])
        # need to see if this works well on mac
        T = T.replace("{{TMPDIR}}", "/tmp")
        # will replace  variables in itself
        counter = 0
        while "{{" in T and counter < 10:
            TT = pytoml.loads(T)
            T = pystache.render(T, **TT)
            counter += 1
        TT = pytoml.loads(T)

        if counter > 9:
            raise RuntimeError(
                "cannot convert default configfile, template arguments still in")

        return T

    def initEnv(self):
        """
        init the environment of an executor
        """
        self.reset()
        T = self._getDirPathConfig()
        T = T.replace("//", "/")
        DIRPATHS = pytoml.loads(T)

        # get env dir arguments & overrule them in jumpscale config
        for key, val in self.env.items():
            if "DIR" in key and key in DIRPATHS:
                DIRPATHS[key] = val

        TSYSTEM = '''

        [system]
        debug = true
        autopip = false
        readonly = false
        container = false

        [redis]
        enabled = false
        port = 6379
        addr = "localhost"

        '''

        TSYSTEM = j.data.text.strip(TSYSTEM)
        TT = pytoml.loads(TSYSTEM)

        TT["dirs"] = DIRPATHS

        # need to see if this works everywhere but think so
        TT["dirs"]["TMPDIR"] = "/tmp"

        TT["system"]["container"] = self.stateOnSystem["iscontainer"]

        if self.exists("%s/github/jumpscale/core9/" % DIRPATHS["CODEDIR"]):
            if "plugins" not in TT.keys():
                TT["plugins"] = {
                    "JumpScale9": "%s/github/jumpscale/core9/JumpScale9/" % DIRPATHS["CODEDIR"]}

        if TT["system"]["container"] == True:
            self.state.configUpdate(TT, True)  # will overwrite
        else:
            self.state.configUpdate(TT, False)  # will not overwrite

        # check if there is a cfg_me if not put defaults
        if self.stateOnSystem["cfg_me"] == {}:

            TME = '''
            [email]
            server = ""

            [me]
            fullname = ""
            loginname = ""
            email = ""

            [ssh]
            sshkeyname = "idonotexist"

            '''

            TME = j.data.text.strip(TME)
            # load the defaults
            self.state.configMe = pytoml.loads(TME)

        self.state.configSave()
        if self.type == "local":
            j.core.state = self._state

        self.cache.reset()

        for key, val in DIRPATHS.items():
            out = ""
            if not self.exists(val):
                out += "mkdir -p %s\n" % val
            self.execute(out)

        if self.type == "local":
            src = "%s/github/jumpscale/core9/cmds/" % j.core.state.configGetFromDict("dirs", "CODEDIR")
            j.do.symlinkFilesInDir(
                src, "/usr/local/bin", delete=True, includeDirs=False, makeExecutable=True)

        print("initenv done on executor base")

    @property
    def dir_paths(self):
        if not self.state.configGet('dirs', None):
                self.initEnv()
        return self.state.configGet("dirs")

    @property
    def platformtype(self):
        return j.core.platformtype.get(self)

    def file_read(self, path):
        self.logger.debug("file read:%s" % path)
        rc, out, err = self.execute("cat %s" % path, showout=False, hide=True)
        return out

    def file_write(self, path, content, mode=None, owner=None, group=None, append=False,hide=False):
        """
        @param append if append then will add to file

        if file bigger than 100k it will not set the attributes!

        """
        if hide==False:
            self.logger.debug("file write:%s" % path)
        # if sig != self.file_md5(location):
        # cmd = 'set -ex && echo "%s" | openssl base64 -A -d > %s' % (content_base64, location)

        if len(content) > 100000:
            # when contents are too big, bash will crash
            temp = j.sal.fs.getTempFileName()
            j.sal.fs.writeFile(filename=temp, contents=content, append=False)
            self.upload(temp, path)
            j.sal.fs.remove(temp)
        else:
            content2 = content.encode('utf-8')
            # sig = hashlib.md5(content2).hexdigest()
            cmd = "set -e\n"
            cmd = "set +x\n"
            parent = j.sal.fs.getParent(path)
            cmd += "mkdir -p %s\n" % parent

            content_base64 = base64.b64encode(content2).decode()
            if self.platformtype.isMac:
                # cmd += 'echo "%s" | openssl base64 -D '%content_base64   #DONT KNOW WHERE THIS COMES FROM?
                cmd += 'echo "%s" | openssl base64 -A -d ' % content_base64
            else:
                cmd += 'echo "%s" | openssl base64 -A -d ' % content_base64

            if append:
                cmd += ">> %s\n" % path
            else:
                cmd += "> %s\n" % path

            if mode:
                cmd += 'chmod %s %s\n' % (mode, path)
            if owner:
                cmd += 'chown %s %s\n' % (owner, path)
            if group:
                cmd += 'chgrp %s %s\n' % (group, path)

            # if sig != self.file_md5(location):

            # print(cmd)
            res = self.execute(cmd, hide=True)

        self.cache.reset()

    def test(self):

        # test that it does not do repeating thing & cache works
        for i in range(1000):
            ptype = self.platformtype

        for i in range(1000):
            env = self.env

        prev = None
        for i in range(10000):
            tmp = self.exists("/tmp")
            if prev != None:
                assert prev == tmp
            prev = tmp

        content = ""
        for i in range(10):
            content += "abcdefg hijklmn %s\n" % i

        contentbig = ""
        for i in range(20000):
            contentbig += "abcdefg hijklmn %s\n" % i

        tmpfile = self.dir_paths["TMPDIR"] + "/testfile"

        self.file_write(tmpfile, content, append=False)
        content2 = self.file_read(tmpfile)

        assert content == content2

        self.file_write(tmpfile, contentbig, append=False)
        content2 = self.file_read(tmpfile)

        assert contentbig == content2

        print("TEST for executor done")
