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

        self.debug=debug
        self.checkok = checkok
        self._prefab = None
        self.type = None
        self.config = {}
        self._id = None
        self.readonly = False
        self.CURDIR = ""
        self.reset()
        self._logger = None
        self._iscontainer=None
        self._state=None
        self.authorizing = False

    @property
    def state(self):
        if self._state==None:
            from JumpScale9.core.State import State
            self._state = State(self)
            self.config=self.state.config
        return self._state

    @property
    def logger(self):
        if self._logger is None:
            self._logger = j.logger.get("unknown")
        return self._logger

    @property
    def id(self):
        if self._id is None:
            raise RuntimeError("self._id cannot be None")
        return self._id


    @property
    def env(self):
        if self._env is None:
            res = {}
            # print("DEBUG: EXECUTOR GET ENV")
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

        if env!={}:
            for key,val in env.items():
                pre+="%s=%s%s"%(key,val,separator)

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
        if path=="/env.sh":
            raise RuntimeError("SS")
        def check():
            rc,_,_=self.execute('test -e %s'%path,die=False,showout=False)
            if rc>0:
                return False
            else:
                return True
        return self.cache.get("exists:%s"%path, check)

    def configSave(self):
        """
        Config Save
        """
        self.state.configSave()

    # interface to implement by child classes
    def execute(self, cmds, die=True, checkok=None, showout=True, timeout=0, env={}):
        raise NotImplementedError()

    def executeRaw(self, cmd, die=True, showout=False):
        raise NotImplementedError()

    def reset(self):
        self._env=None

    @property
    def isDebug(self):
        return self.config["system"]["debug"]=="1" or  self.config["system"]["debug"]==1 or  self.config["system"]["debug"]==True or self.config["system"]["debug"]=="true"

    @property
    def isContainer(self):
        """
        means we don't work with ssh-agent ...
        """
        if self._iscontainer==None:
            self._iscontainer= self.exists("/root/.iscontainer")
        return self._iscontainer

    def enableDebug(self):
        self.config["system"]["debug"] = value
        self.state.configSave()
        self.cache.reset()

    def _getDirPathConfig(self):

        hostdirexists= self.exists("/host")

        if self.isContainer and not hostdirexists:
            raise RuntimeError("if container the hostdir needs to exists (/host)")

        if self.isContainer:
            T = '''
            BASEDIR = "/opt"
            CODEDIR = "/opt/code"
            HOSTDIR = "/host"
            HOSTCFGDIR = "/hostcfg"
            VARDIR = "{{HOSTDIR}}/var"
            '''
        elif j.core.platformtype.myplatform.isMac:
            T = '''
            BASEDIR = "{{HOMEDIR}}/opt"
            CODEDIR = "{{HOMEDIR}}/code"
            HOSTDIR = "{{HOMEDIR}}/js9host/"
            HOSTCFGDIR = "{{HOMEDIR}}/js9host/cfg/"
            VARDIR = "{{BASEDIR}}/var"
            '''
        else:
            T = '''
            BASEDIR = "/opt"
            CODEDIR = "/opt/code"
            HOSTDIR = "{{HOMEDIR}}/js9host/"
            HOSTCFGDIR = "{{HOMEDIR}}/js9host/cfg/"
            VARDIR = "{{BASEDIR}}/var"
            '''


        BASE='''
        HOMEDIR = "~"
        TMPDIR = "/tmp"
        BASEDIRJS = "{{BASEDIR}}/jumpscale9"
        JSAPPSDIR= "{{BASEDIRJS}}/app"
        TEMPLATEDIR ="{{VARDIR}}/templates"
        DATADIR = "{{VARDIR}}/data"
        BUILDDIR = "{{VARDIR}}/build"
        LIBDIR = "{{BASEDIR}}/lib/"
        LOGDIR = "{{VARDIR}}/log"
        BINDIR="{{BASEDIR}}/bin"
        CFGDIR = "{{BASEDIR}}/cfg"
        '''

        TXT=j.data.text.strip(BASE)+"\n"+j.data.text.strip(T)

        return self._replaceInToml(TXT)

    def _replaceInToml(self,T):
        T=T.replace("~", self.env["HOME"])
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

        T=self._getDirPathConfig()
        T=T.replace("//", "/")
        DIRPATHS = pytoml.loads(T)

        # get env dir arguments & overrule them in jumpscale config
        for key, val in self.env.items():
            if "DIR" in key and key in DIRPATHS:
                DIRPATHS[key] = val

        TME = '''
        [email]
        from = "info@incubaid.com"
        smtp_port = 443
        smtp_server = ""

        [me]
        fullname = "This is my full name, needs to be replace"
        loginname = "someid"

        [ssh]
        SSHKEYNAME = "somename"

        '''

        TME=j.data.text.strip(TME)

        # if DIRPATHS["HOSTCFGDIR"]!="":
        #     path=self.joinPaths(DIRPATHS["HOSTCFGDIR"],"me.toml")
        #     if not self.exists(path):
        #         self.writeFile(path,j.data.text.strip(TME))
        #     else:
        #         #config file exists lets load it
        #         TME=self.readFile(path)

        TSYSTEM= '''

        [system]
        debug = true
        autopip = false
        readonly = false
        container = false

        [grid]
        gid = 0
        nid = 0

        [redis]
        enabled = false
        port = 6379
        addr = "localhost"

        '''

        TSYSTEM=j.data.text.strip(TSYSTEM)

        T = TSYSTEM + "\n" + TME + "\n"

        TT = pytoml.loads(T)
        TT["dirs"]=DIRPATHS

        TT["system"]["container"] = self.exists("/root/.iscontainer")

        if self.exists("%s/github/jumpscale/core9/" % DIRPATHS["CODEDIR"]):
            if "plugins" not in TT.keys():
                TT["plugins"]={"JumpScale9":"%s/github/jumpscale/core9/JumpScale9/" % DIRPATHS["CODEDIR"]}

        if TT["system"]["container"] == True:
            self.state.configUpdate(TT, True)  # will overwrite
        else:
            self.state.configUpdate(TT, False)  # will not overwrite

        for key, val in DIRPATHS.items():
            if not self.exists(val) and not self.authorizing:
                self.execute("mkdir -p %s"%val)

        # if DIRPATHS["HOSTCFGDIR"]!="":
        #     path=self.joinPaths(DIRPATHS["HOSTCFGDIR"],"me.toml")
        #     if not self.exists(path):
        #         self.writeFile(path,j.data.text.strip(TME))  #needs to use the args I already know & then put in separate file

        if self.type == "local":
            src = "%s/github/jumpscale/core9/cmds/" % j.core.state.config["dirs"]["CODEDIR"]
            j.do.symlinkFilesInDir(src, "/usr/local/bin", delete=True, includeDirs=False, makeExecutable=True)

        # self.writeEnvArgsBash()

        self.state.configSave()

        self.reset()
        self.cache.reset()

        print ("initenv done on executor base")

    @property
    def dir_paths(self):
        if "dirs" not in self.config:
            self.initEnv()
        return self.config["dirs"]


    @property
    def platformtype(self):
        return j.core.platformtype.get(self)

    def file_read(self,path):
        rc, out, err=self.execute("cat %s"%path,showout=False)
        return out

    def file_write(self, path, content, mode=None, owner=None, group=None, append=False):
        """
        @param append if append then will add to file

        if file bigger than 100k it will not set the attributes!

        """

        # if sig != self.file_md5(location):
        # cmd = 'set -ex && echo "%s" | openssl base64 -A -d > %s' % (content_base64, location)

        if len(content) > 100000:
            # when contents are too big, bash will crash
            temp = j.sal.fs.getTempFileName()
            j.sal.fs.writeFile(filename=temp, contents=content, append=False)
            self.upload(temp, path)
            j.sal.fs.remove(temp)
        else:
            content2=content.encode('utf-8')
            # sig = hashlib.md5(content2).hexdigest()
            cmd="set -e\n"
            parent=j.sal.fs.getParent(path)
            cmd+="mkdir -p %s\n"%parent

            content_base64 = base64.b64encode(content2).decode()
            if self.platformtype.isMac:
                cmd += 'echo "%s" | openssl base64 -D '%content_base64
            else:
                cmd += 'echo "%s" | openssl base64 -A -d '%content_base64
            if append:
                cmd+=">> %s\n"%path
            else:
                cmd+="> %s\n"%path

            if mode:
                cmd+='chmod %s %s\n' % ( mode, path)
            if owner:
                cmd+='chown %s %s\n' % ( owner, path)
            if group:
                cmd+='chgrp %s %s\n' % ( group, path)

            # if sig != self.file_md5(location):

            # print(cmd)
            res = self.execute(cmd)

        self.cache.reset()


    def test(self):

        #test that it does not do repeating thing & cache works
        for i in range(1000):
            ptype=self.platformtype

        for i in range(1000):
            env=self.env

        prev=None
        for i in range(10000):
            tmp=self.exists("/tmp")
            if prev!=None:
                assert prev==tmp
            prev=tmp

        content=""
        for i in range (10):
            content+="abcdefg hijklmn %s\n"%i

        contentbig=""
        for i in range (20000):
            contentbig+="abcdefg hijklmn %s\n"%i

        tmpfile=self.dir_paths["TMPDIR"]+"/testfile"

        self.file_write(tmpfile, content, append=False)
        content2=self.file_read(tmpfile)

        assert content==content2

        self.file_write(tmpfile, contentbig, append=False)
        content2=self.file_read(tmpfile)

        assert contentbig==content2

        print ("TEST for executor done")
