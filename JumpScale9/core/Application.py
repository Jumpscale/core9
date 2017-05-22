from JumpScale9 import j
import os
# import sys
import atexit
import struct
from collections import namedtuple


WhoAmI = namedtuple('WhoAmI', 'gid nid pid')


class Application:

    def __init__(self):

        self.logger = j.logger.get("application")

        self._calledexit = False

        self.state = "UNKNOWN"
        self.appname = 'UNKNOWN'

        self._debug = j.core.state.config["system"]["debug"]

        self.config = j.core.state.config

        self._systempid = None
        self._whoAmIBytestr = None
        self._whoAmi = None

        self.interactive = True
        self._fixlocale = False
        self.__jslocation__ = "j.core.application"

    def reset(self):
        """
        empties the core.db
        """
        if j.core.db is not None:
            for key in j.core.db.keys():
                j.core.db.delete(key)
        self.reload()

    def reload(self):
        from IPython import embed
        print("DEBUG NOW application implement reload")
        embed()
        raise RuntimeError("stop debug here")

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, value):
        self._debug = value

    def break_into_jshell(self, msg="DEBUG NOW"):
        if self.debug is True:
            print(msg)
            from IPython import embed
            embed()
        else:
            raise j.exceptions.RuntimeError(
                "Can't break into jsshell in production mode.")

    def fixlocale(self):
        return
        rc, out, err = self.executor.execute("locale -a", showout=False)
        out = [item for item in out.split(
            "\n") if not item.startswith("locale:")]
        if 'C.UTF-8' not in out:
            raise j.exceptions.RuntimeError(
                "Cannot find C.UTF-8 in locale -a, cannot continue.")
        # 'LANG': 'en_GB.UTF-8'
        # os.environ["LC_ALL"]='C.UTF-8''
        # TERMINFO
        # export TERM=linux
        # export TERMINFO=/etc/terminfo
        from IPython import embed
        print("DEBUG NOW fix locale in application")
        embed()
        o

    def init(self):

        # if not embed() and self.config.jumpscale is not None:
        #     logging_cfg = self.config.jumpscale.get('logging')
        #     if not logging_cfg:
        #         # auto recover logging settings
        #         j.do.installer._writeLoggingEnv(j.dirs.JSCFGDIR)
        #         logging_cfg = self.config.jumpscale.get('logging')
        #     level = logging_cfg.get('level', 'DEBUG')
        #     mode = logging_cfg.get('mode', 'DEV')
        #     filter_module = logging_cfg.get('filter', [])
        #     j.logger.init(mode, level, filter_module)
        # else:
        #     j.logger.init("DEV", "INFO", [])

        if self._fixlocale:
            self.fixlocale()

    # def useCurrentDirAsHome(self):
    #     """
    #     use current directory as home for JumpScale
    #     e.g. /optrw/jumpscale9
    #     there needs to be a env.sh in that dir
    #     will also empty redis
    #     """
    #     if not j.do.exists("env.sh"):
    #         raise j.exceptions.RuntimeError(
    #             "Could not find env.sh in current directory, please go to root of jumpscale e.g. /optrw/jumpscale9")
    #     # C=j.do.fileGetContents("env.sh")
    #     # C2=""
    #     # for line in C.split("\n"):
    #     #     if line.startswith("export JSBASE"):
    #     #         line="export JSBASE=/optrw/jumpscale9"
    #     #     C2+="%s\n"%line
    #     # j.do.fileGetContents("env.sh",C2)
    #     j.core.db.flushall()
    #     j.do.installer.writeenv(base=j.do.getcwd())
    #     j.core.db.flushall()

    @property
    def whoAmIBytestr(self):
        if self._whoAmi is None:
            self._initWhoAmI()
        return self._whoAmIBytestr

    @property
    def whoAmI(self):
        if self._whoAmi is None:
            self._initWhoAmI()
        return self._whoAmi

    @property
    def systempid(self):
        if self._systempid is None:
            self._systempid = os.getpid()
        return self._systempid

    def _initWhoAmI(self):
        self._whoAmi = WhoAmI(gid=int(self.config['grid']["gid"]), nid=int(
            self.config['grid']["nid"]), pid=self.systempid)
        self._whoAmIBytestr = struct.pack(
            "<IHH", self.whoAmI.pid, self.whoAmI.nid, self.whoAmI.gid)

    def getWhoAmiStr(self):
        return "_".join([str(item) for item in self.whoAmI])

    def start(self, name=None):
        '''Start the application

        You can only stop the application with return code 0 by calling
        j.application.stop(). Don't call sys.exit yourself, don't try to run
        to end-of-script, I will find you anyway!
        '''
        if name:
            self.appname = name

        if "JSPROCNAME" in os.environ:
            self.appname = os.environ["JSPROCNAME"]

        if self.state == "RUNNING":
            raise j.exceptions.RuntimeError(
                "Application %s already started" % self.appname)

        # Register exit handler for sys.exit and for script termination
        atexit.register(self._exithandler)

        # if j.core.db is not None:
        #     if j.core.db.hexists("application", self.appname):
        #         pids = j.data.serializer.json.loads(
        #             j.core.db.hget("application", self.appname))
        #     else:
        #         pids = []
        #     if self.systempid not in pids:
        #         pids.append(self.systempid)
        #     j.core.db.hset("application", self.appname,
        #                    j.data.serializer.json.dumps(pids))

        # Set state
        self.state = "RUNNING"

        # self.initWhoAmI()

        self.logger.info("***Application started***: %s" % self.appname)

    def stop(self, exitcode=0, stop=True):
        '''Stop the application cleanly using a given exitcode

        @param exitcode: Exit code to use
        @type exitcode: number
        '''
        import sys

        # TODO: should we check the status (e.g. if application wasnt started,
        # we shouldnt call this method)
        if self.state == "UNKNOWN":
            # Consider this a normal exit
            self.state = "HALTED"
            sys.exit(exitcode)

        # Since we call os._exit, the exithandler of IPython is not called.
        # We need it to save command history, and to clean up temp files used by
        # IPython itself.
        self.logger.info("Stopping Application %s" % self.appname)
        try:
            __IPYTHON__.atexit_operations()
        except BaseException:
            pass

        # # Write exitcode
        # if self.writeExitcodeOnExit:
        #     exitcodefilename = j.do.joinPaths(j.dirs.TMPDIR, 'qapplication.%d.exitcode'%os.getpid())
        #     j.logger.log("Writing exitcode to %s" % exitcodefilename, 5)
        #     j.do.writeFile(exitcodefilename, str(exitcode))

        # was probably done like this so we dont end up in the _exithandler
        # os._exit(exitcode) Exit to the system with status n, without calling
        # cleanup handlers, flushing stdio buffers, etc. Availability: Unix,
        # Windows.

        # exit will raise an exception, this will bring us to _exithandler
        self._calledexit = True
        # to remember that this is correct behavior we set this flag

        # tell gridmaster the process stopped

        # TODO: this SHOULD BE WORKING AGAIN, now processes are never removed

        if stop:
            sys.exit(exitcode)

    def _exithandler(self):
        # Abnormal exit
        # You can only come here if an application has been started, and if
        # an abnormal exit happened, i.e. somebody called sys.exit or the end of script was reached
        # Both are wrong! One should call j.application.stop(<exitcode>)
        # TODO: can we get the line of code which called sys.exit here?

        # j.logger.log("UNCLEAN EXIT OF APPLICATION, SHOULD HAVE USED j.application.stop()", 4)
        import sys
        if not self._calledexit:
            self.stop(stop=False)

    def existAppInstanceHRD(self, name, instance, domain="jumpscale"):
        """
        returns hrd for specific appname & instance name (default domain=jumpscale or not used when inside a config git repo)
        """
        return False
        # TODO: fix
        if j.core.atyourservice.type != "c":
            path = '%s/%s__%s__%s.hrd' % (j.dirs.getHrdDir(),
                                          domain, name, instance)
        else:
            path = '%s/%s__%s.hrd' % (j.dirs.getHrdDir(), name, instance)
        if not j.do.exists(path=path):
            return False
        return True

    def getAppInstanceHRD(
            self,
            name,
            instance,
            domain="jumpscale",
            parent=None):
        """
        returns hrd for specific domain,name and & instance name
        """
        return j.application.config
        # TODO: fix
        service = j.core.atyourservice.getService(
            domain=domain, name=name, instance=instance)
        return service.hrd

    def getAppInstanceHRDs(self, name, domain="jumpscale"):
        """
        returns list of hrd instances for specified app
        """
        # TODO: fix
        res = []
        for instance in self.getAppHRDInstanceNames(name, domain):
            res.append(self.getAppInstanceHRD(name, instance, domain))
        return res

    def getAppHRDInstanceNames(self, name, domain="jumpscale"):
        """
        returns hrd instance names for specific appname (default domain=jumpscale)
        """
        repos = []
        for path in j.core.atyourservice.findAYSRepos(j.dirs.CODEDIR):
            repos.append(j.core.atyourservice.get(path=path))
        names = sorted([service.instance for aysrepo in repos for service in list(
            aysrepo.services.values()) if service.templatename == name])
        return names

    def getCPUUsage(self):
        """
        try to get cpu usage, if it doesn't work will return 0
        By default 0 for windows
        """
        try:
            pid = os.getpid()
            if j.core.platformtype.myplatform.isWindows:
                return 0
            if j.core.platformtype.myplatform.isLinux:
                command = "ps -o pcpu %d | grep -E --regex=\"[0.9]\"" % pid
                self.logger.debug("getCPUusage on linux with: %s" % command)
                exitcode, output, err = j.sal.process.execute(
                    command, True, False)
                return output
            elif j.core.platformtype.myplatform.isSolaris():
                command = 'ps -efo pcpu,pid |grep %d' % pid
                self.logger.debug("getCPUusage on linux with: %s" % command)
                exitcode, output, err = j.sal.process.execute(
                    command, True, False)
                cpuUsage = output.split(' ')[1]
                return cpuUsage
        except Exception:
            pass
        return 0

    def getMemoryUsage(self):
        """
        try to get memory usage, if it doesn't work will return 0i
        By default 0 for windows
        """
        try:
            pid = os.getpid()
            if j.core.platformtype.myplatform.isWindows:
                # Not supported on windows
                return "0 K"
            elif j.core.platformtype.myplatform.isLinux:
                command = "ps -o pmem %d | grep -E --regex=\"[0.9]\"" % pid
                self.logger.debug("getMemoryUsage on linux with: %s" % command)
                exitcode, output, err = j.sal.process.execute(
                    command, True, False)
                return output
            elif j.core.platformtype.myplatform.isSolaris():
                command = "ps -efo pcpu,pid |grep %d" % pid
                self.logger.debug("getMemoryUsage on linux with: %s" % command)
                exitcode, output, err = j.sal.process.execute(
                    command, True, False)
                memUsage = output.split(' ')[1]
                return memUsage
        except Exception:
            pass
        return 0

    def appCheckActive(self, appname):
        return self.appNrInstances(appname) > 0

    def appNrInstances(self, appname):
        return len(self.appGetPids(appname))

    def appNrInstancesActive(self, appname):
        return len(self.appGetPidsActive(appname))

    # TODO: *2 is this still being used?
    def appGetPids(self, appname):
        if j.core.db is None:
            raise j.exceptions.RuntimeError(
                "Redis was not running when applications started, cannot get pid's")
        if not j.core.db.hexists("application", appname):
            return list()
        else:
            pids = j.data.serializer.json.loads(
                j.core.db.hget("application", appname))
            return pids

    def appsGetNames(self):
        if j.core.db is None:
            raise j.exceptions.RuntimeError(
                "Make sure redis is running for port 9999")
        return j.core.db.hkeys("application")

    def appsGet(self):

        defunctlist = self.getDefunctProcesses()
        result = {}
        for item in self.appsGetNames():
            pids = self.appGetPidsActive(item)
            pids = [pid for pid in pids if pid not in defunctlist]

            if pids == []:
                j.core.db.hdelete("application", item)
            else:
                result[item] = pids
        return result

    def appGetPidsActive(self, appname):
        pids = self.appGetPids(appname)
        todelete = []
        for pid in pids:
            if not self.isPidAlive(pid):
                todelete.append(pid)
            else:
                environ = self.getEnviron(pid)
                if environ.get('JSPROCNAME') != appname:
                    todelete.append(pid)
        for item in todelete:
            pids.remove(item)
        j.core.db.hset(
            "application",
            appname,
            j.data.serializer.json.dumps(pids))

        return pids

    def getUniqueMachineId(self):
        """
        will look for network interface and return a hash calculated from lowest mac address from all physical nics
        """
        # if unique machine id is set in grid.hrd, then return it
        uniquekey = 'node.machineguid'
        if j.application.config.jumpscale['system']['grid'].get(
                uniquekey, False):
            machineguid = j.application.config.jumpscale['system']['grid'].get(
                uniquekey)
            if machineguid.strip():
                return machineguid

        nics = j.sal.nettools.getNics()
        if j.core.platformtype.myplatform.isWindows:
            order = ["local area", "wifi"]
            for item in order:
                for nic in nics:
                    if nic.lower().find(item) != -1:
                        return j.sal.nettools.getMacAddress(nic)
        macaddr = []
        for nic in nics:
            if nic.find("lo") == -1:
                nicmac = j.sal.nettools.getMacAddress(nic)
                macaddr.append(nicmac.replace(":", ""))
        macaddr.sort()
        if len(macaddr) < 1:
            raise j.exceptions.RuntimeError(
                "Cannot find macaddress of nics in machine.")

        if j.application.config.jumpscale['system']['grid'].get(
                uniquekey, False):
            j.application.config.jumpscale['system']['grid'][uniquekey] = macaddr[0]
        return macaddr[0]

    def _setWriteExitcodeOnExit(self, value):
        if not j.data.types.bool.check(value):
            raise TypeError
        self._writeExitcodeOnExit = value

    def _getWriteExitcodeOnExit(self):
        if not hasattr(self, '_writeExitcodeOnExit'):
            return False
        return self._writeExitcodeOnExit

    writeExitcodeOnExit = property(
        fset=_setWriteExitcodeOnExit,
        fget=_getWriteExitcodeOnExit,
        doc="Gets / sets if the exitcode has to be persisted on disk")
