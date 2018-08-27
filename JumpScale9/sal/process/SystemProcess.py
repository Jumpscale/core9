
import os
import os.path
import re
import time
import sys
# import select
# import threading
# import queue
import random
import subprocess
import signal
from subprocess import Popen
import select

#for execute
from fcntl import fcntl, F_GETFL, F_SETFL
from os import O_NONBLOCK, read

from JumpScale9 import j

JSBASE = j.application.jsbase_get_class()


class SystemProcess(JSBASE):

    def __init__(self):
        if not hasattr(self, '__jslocation__'):
            self.__jslocation__ = "j.sal.process"
        JSBASE.__init__(self)
        self._isunix=None

    @property
    def isUnix(self):
        if self._isunix==None:
            if 'posix' in sys.builtin_module_names:
                self._isunix = True
            else:
                self._isunix = False
        return self._isunix


    def executeWithoutPipe(self, command, die=True, printCommandToStdout=False):
        """

        Execute command without opening pipes, returns only the exitcode
        This is platform independent
        @param command: command to execute
        @param die: boolean to die if got non zero exitcode
        @param printCommandToStdout: boolean to show/hide output to stdout
        @param showout: Deprecated. Use 'printCommandToStdout' instead.
        @rtype: integer represents the exitcode
        if exitcode is not zero then the executed command returned with errors
        """

        if printCommandToStdout:
            self.logger.info(
                "system.process.executeWithoutPipe [%s]" % command)
        else:
            self.logger.debug(
                "system.process.executeWithoutPipe [%s]" % command)
        exitcode = os.system(command)

        if exitcode != 0 and die:
            self.logger.error(
                "command: [%s]\nexitcode:%s" % (command, exitcode))
            raise j.exceptions.RuntimeError(
                "Error during execution!\nCommand: %s\nExitcode: %s" % (command, exitcode))

        return exitcode

    def execute(self, command, showout=True, useShell=True, log=True, cwd=None, timeout=600, errors=[], ok=[], captureout=True, die=True, async_=False, env=None):

        command = j.data.text.strip(command)
        if "\n" in command:
            path = j.sal.fs.getTmpFilePath()
            self.logger.debug("execbash:\n'''%s\n%s'''\n" % (path, command))
            if die:
                command = "set -ex\n%s" % command
            j.sal.fs.writeFile(path, command + "\n")
            command = "bash %s" % path
        else:
            # self.logger.info("exec:%s" % command)
            path = None
            self.logger.debug("execute:%s"%command)

        os.environ["PYTHONUNBUFFERED"] = "1" #WHY THIS???


        if hasattr(subprocess, "_mswindows"):
            mswindows = subprocess._mswindows
        else:
            mswindows = subprocess.mswindows

        if env==None:
            env=os.environ


        p = Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                  close_fds=self.isUnix,
                  shell=useShell, env=env, universal_newlines=False, cwd=cwd, bufsize=0, executable="/bin/bash")


        # set the O_NONBLOCK flag of p.stdout file descriptor:
        flags = fcntl(p.stdout, F_GETFL) # get current p.stdout flags
        flags = fcntl(p.stderr, F_GETFL) # get current p.stderr flags
        fcntl(p.stdout, F_SETFL, flags | O_NONBLOCK)
        fcntl(p.stderr, F_SETFL, flags | O_NONBLOCK)

        out=""
        err=""

        if async_:
            return p

        captureOutput=True

        def readout(stream):
            if self.isUnix:
                # Store all intermediate data
                data = list()
                while True:
                    # Read out all available data
                    line = stream.read()
                    if not line:
                        break
                    line=line.decode()#will be utf8
                    # Honour subprocess univeral_newlines
                    if p.universal_newlines:
                        line = p._translate_newlines(line)
                    # Add data to cache
                    data.append(line)
                    if showout:
                        self.logger.debug(line)

                # Fold cache and return
                return ''.join(data)

            else:
                # This is not UNIX, most likely Win32. read() seems to work
                def readout(stream):
                    line= stream.read().decode()
                    if showout:
                        self.logger.debug(line)

        if timeout < 0:
            out, err = p.communicate()
            out=out.decode()
            err=err.decode()

        else:  # timeout set
            start = time.time()
            end = start + timeout
            now = start

            # if command already finished then read stdout, stderr
            out = readout(p.stdout)
            err = readout(p.stderr)
            while p.poll() is None:
                #means process is still running

                time.sleep(0.01)
                now = time.time()
                # print("wait")

                if timeout!=0 and now > end:
                    if self.isUnix:
                        # Soft and hard kill on Unix
                        try:
                            p.terminate()
                            # Give the process some time to settle
                            time.sleep(0.2)
                            p.kill()
                        except OSError:
                            pass
                    else:
                        # Kill on anything else
                        time.sleep(0.1)
                        if p.poll():
                            p.terminate()

                    self.logger.warning("process killed because of timeout")
                    return (-2, out, err)

                # Read out process streams, but don't block
                out += readout(p.stdout)
                err += readout(p.stderr)

        rc = -1 if p.returncode < 0 else p.returncode

        if rc<0 or rc>0:
            j.sal.process.logger.debug('system.process.run ended, exitcode was %d' % rc)
        if out!="":
            j.sal.process.logger.debug('system.process.run stdout:\n%s' % out)
        if err!="":
            j.sal.process.logger.debug('system.process.run stderr:\n%s' % err)

        if die and rc!=0:
            msg="\nCould not execute:"
            if command.find("\n") ==-1 and len(command)<40:
                msg+=" '%s'"%command
            else:
                command="\n".join(command.split(";"))
                msg+= j.data.text.indent(command).rstrip()+"\n\n"
            if out.strip()!="":
                msg+="stdout:\n"
                msg+= j.data.text.indent(out).rstrip()+"\n\n"
            if err.strip()!="":
                msg+="stderr:\n"
                msg+= j.data.text.indent(err).rstrip()+"\n\n"
            raise RuntimeError(msg)

        return (rc, out, err)



    def executeAsyncIO(self, command, outMethod="print", errMethod="print", timeout=600,
                       buffersize=5000000, useShell=True, cwd=None, die=True,
                       captureOutput=True):
        """
        @outmethod gets a byte string as input, deal with it e.g. print
        same for errMethod
        resout&reserr are lists with output/error
        return rc, resout, reserr
        @param captureOutput, if that one == False then will not populate resout/reserr
        @param outMethod,errMethod if None then will print to out
        """
        # TODO: *2 check if this works on windows
        # TODO: *2 there is an ugly error when there is a timeout (on some systems seems to work though)

        if cwd is not None:
            if not useShell:
                raise j.exceptions.Input(message="when using cwd, useshell needs to be used",
                                         level=1, source="", tags="", msgpub="")
            if "cd %s;" % cwd not in command:
                command = "cd %s;%s" % (cwd, command)

        if useShell:
            if "set -e" not in command:
                command = "set -e;%s" % command

        # if not specified then print to stdout/err
        if outMethod == "print":
            def outMethod(x): return print("STDOUT: %s" %
                                           x.decode("UTF-8").rstrip())
            # outMethod = lambda x: sys.stdout.buffer.write(x)  #DOESN't work, don't know why
        if errMethod == "print":
            # errMethod = lambda x: sys.stdout.buffer.write(x)
            def errMethod(x): return print("STDERR: %s" %
                                           x.decode("UTF-8").rstrip())

        async def _read_stream(stream, cb, res):
            while True:
                line = await stream.readline()
                if res is not None:
                    res.append(line)
                if line:
                    if cb is not None:
                        cb(line)
                else:
                    break

        async def _stream_subprocess(cmd, stdout_cb, stderr_cb, timeout=1, buffersize=500000, captureOutput=True):

            process = await asyncio.create_subprocess_exec(*cmd,
                                                           stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                                                           limit=buffersize)

            if captureOutput:
                resout = []
                reserr = []
            else:
                resout = None
                reserr = None

            rc = 0

            done, pending = await asyncio.wait([
                _read_stream(process.stdout, stdout_cb, resout),
                _read_stream(process.stderr, stderr_cb, reserr)
            ], timeout=timeout, return_when=asyncio.ALL_COMPLETED)

            if pending != set():
                # timeout happened
                self.logger.debug("ERROR TIMEOUT happend")
                for task in pending:
                    task.cancel()
                process.kill()
                return 124, resout, reserr

            await process.wait()
            rc = process.returncode
            return rc, resout, reserr

        loop = asyncio.get_event_loop()
        # executor = concurrent.futures.ThreadPoolExecutor(5)
        # loop.set_default_executor(executor)
        # loop.set_debug(True)

        if useShell:
            cmds = ["bash", "-c", command]
        else:
            cmds = command.split()

        rc, resout, reserr = loop.run_until_complete(
            _stream_subprocess(
                cmds,
                outMethod,
                errMethod,
                timeout=timeout,
                buffersize=buffersize,
                captureOutput=captureOutput
            ))

        # TODO: *1 if I close this then later on there is problem, says loop is closed
        # # if loop.is_closed() == False:
        # print("STOP")
        # # executor.shutdown(wait=True)
        # loop.stop()
        # loop.run_forever()
        # loop.close()

        if len(reserr) > 0 and reserr[-1] == b"":
            reserr = reserr[:-1]
        if len(resout) > 0 and resout[-1] == b"":
            resout = resout[:-1]

        if die and rc > 0:
            out = "\n".join([item.rstrip().decode("UTF-8") for item in resout])
            err = "\n".join([item.rstrip().decode("UTF-8") for item in reserr])
            if rc == 124:
                raise RuntimeError("\nOUT:\n%s\nSTDERR:\n%s\nERROR: Cannot execute (TIMEOUT):'%s'\nreturncode (%s)" %
                                   (out, err, command, rc))
            else:
                raise RuntimeError("\nOUT:\n%s\nSTDERR:\n%s\nERROR: Cannot execute:'%s'\nreturncode (%s)" %
                                   (out, err, command, rc))

        return rc, resout, reserr

    # def executeBackgroundNoPipe(self, cmd):
    #     """
    #     RUN IN BACKGROUND, won't see anything
    #     """
    #     # devnull = open(os.devnull, 'wb') # use this in python < 3.3
    #     # Popen(['nohup', cmd+" &"], stdout=devnull, stderr=devnull)
    #     cmd2 = "nohup %s > /dev/null 2>&1 &" % cmd
    #     cmd2 = j.dirs.replace_txt_dir_vars(cmd2)
    #     print(cmd2)
    #     j.sal.process.executeWithoutPipe(cmd2)

    def executeScript(self, scriptName):
        """execute python script from shell/Interactive Window"""
        self.logger.debug('Excecuting script with name: %s' % scriptName)
        if scriptName is None:
            raise ValueError(
                'Error, Script name in empty in system.process.executeScript')
        try:
            script = j.sal.fs.readFile(scriptName)
            scriptc = compile(script, scriptName, 'exec')
            exec(scriptc)
        except Exception as err:
            raise j.exceptions.RuntimeError(
                'Failed to execute the specified script: %s, %s' % (scriptName, str(err)))

    def executeBashScript(
            self,
            content="",
            path=None,
            die=True,
            remote=None,
            sshport=22,
            showout=True,
            sshkey="",
            timeout=600,
            executor=None):
        """
        @param remote can be ip addr or hostname of remote, if given will execute cmds there
        """
        if path is not None:
            content = j.sal.fs.readFile(path)
        if content[-1] != "\n":
            content += "\n"

        if remote is None:
            tmppath = "/tmp"
            content = "cd %s\n%s" % (tmppath, content)
        else:
            content = "cd /tmp\n%s" % content

        if die:
            content = "set -ex\n%s" % content

        tmppathdest = "/tmp/do.sh"
        j.sal.fs.writeFile(tmppathdest, content)

        if remote is not None:
            if sshkey:
                if not j.clients.ssh.sshkey_path_get(sshkey, die=False) is None:
                    self.execute('ssh-add %s' % sshkey)
                sshkey = '-i %s ' % sshkey.replace('!', '\!')
            self.execute(
                "scp %s -oStrictHostKeyChecking=no -P %s %s root@%s:%s " %
                (sshkey, sshport, tmppathdest, remote, tmppathdest), die=die)
            rc, res, err = self.execute(
                "ssh %s -oStrictHostKeyChecking=no -A -p %s root@%s 'bash %s'" %
                (sshkey, sshport, remote, tmppathdest), die=die, timeout=timeout)
        else:
            rc, res, err = self.execute(
                "bash %s" %
                tmppathdest, die=die, showout=showout, timeout=timeout)
            j.sal.fs.remove(tmppathdest)
        return rc, res, err

    def executeInteractive(self, command, die=True):
        exitcode = os.system(command)
        if exitcode != 0 and die:
            raise RuntimeError("Could not execute %s" % command)
        return exitcode

    def executeInSandbox(self, command, timeout=0):
        """Executes a command
        @param command: string (command to be executed)
        @param timeout: 0 means to ever, expressed in seconds
        """
        self.logger.debug('Executing command %s in sandbox' % command)
        if command is None:
            raise j.exceptions.RuntimeError(
                'Error, cannot execute command not specified')
        try:
            p = os.popen(command)
            output = p.read()
            exitcode = p.close() or 0
            if exitcode != 0 and timeout:
                raise j.exceptions.RuntimeError(
                    "Error durring execution!\nCommand: %s\nErrormessage: %s" % (command, output))
            return exitcode, output
        except BaseException:
            raise j.exceptions.RuntimeError(
                'Failed to execute the specified command: %s' % command)

    def executeCode(self, code, params=None):
        """
        execute a method (python code with def)
        use params=j.data.params.get() as input
        """
        if params is None:
            params = j.data.params.get()
        codeLines = code.split("\n")
        if "def " not in codeLines[0]:
            raise ValueError("code to execute needs to start with def")
        def_indent = codeLines[0].find("def ")
        if def_indent:
            # means we need to lower identation with 4
            def unindent(line):
                if len(line) >= def_indent:
                    return line[def_indent:]
                else:
                    return line

            out = "\n".join(map(unindent, codeLines))
            code = out

        if len(j.data.regex.findAll("^def", code)) != 1:
            server.raiseError(
                "Cannot find 1 def method in code to execute, code submitted was \n%s" % code)

        code2 = ""
        for line in code.split("\n"):
            if line.find("def") == 0:
                line = "def main(" + "(".join(line.split("(")[1:])
            code2 += "%s\n" % line

        # try to load the code
        self.logger.debug(code2)
        execContext = {}
        try:
            exec((code2, globals(), locals()), execContext)
        except Exception as e:
            raise j.exceptions.RuntimeError(
                "Could not import code, code submitted was \n%s" % code)

        main = execContext['main']

        # try to execute the code
        result = {}
        try:
            result = main(params)
        except Exception as e:
            raise j.exceptions.RuntimeError(
                "Error %s.\ncode submitted was \n%s" % (e, code))
        return result

    def isPidAlive(self, pid):
        """Checks whether this pid is alive.
           For unix, a signal is sent to check that the process is alive.
           For windows, the process information is retrieved and it is double checked that the process is python.exe
           or pythonw.exe
        """
        self.logger.info('Checking whether process with PID %d is alive' % pid)
        if self.isUnix:
            # Unix strategy: send signal SIGCONT to process pid
            # Achilles heal: another process which happens to have the same pid could be running
            # and incorrectly considered as this process
            import signal
            try:
                os.kill(pid, 0)
            except OSError:
                return False

            return True

        elif j.core.platformtype.myplatform.isWindows:
            return j.sal.windows.isPidAlive(pid)

    def checkInstalled(self, cmdname):
        """
        @param cmdname is cmd to check e.g. curl
        """
        rc, out, err = self.execute(
            "which %s" %
            cmdname, die=False, showout=False)
        if rc == 0:
            return True
        else:
            return False

    def kill(self, pid, sig=None):
        """
        Kill a process with a signal
        @param pid: pid of the process to kill
        @param sig: signal. If no signal is specified signal.SIGKILL is used
        """
        pid=int(pid)
        j.sal.process.logger.debug('Killing process %d' % pid)
        if self.isUnix:
            try:
                if sig is None:
                    sig = signal.SIGKILL

                os.kill(pid, sig)

            except OSError as e:
                raise j.exceptions.RuntimeError(
                    "Could not kill process with id %s.\n%s" % (pid, e))

        elif j.core.platformtype.myplatform.isWindows:
            import win32api
            import win32process
            import win32con
            try:
                handle = win32api.OpenProcess(
                    win32con.PROCESS_TERMINATE, False, pid)
                win32process.TerminateProcess(handle, 0)
            except BaseException:
                raise

    def psfind(self, name):
        rc, out, err = self.execute("ps ax | grep %s" % name, showout=False)
        for line in out.split("\n"):
            if line.strip() == "":
                continue
            if "grep" in line:
                continue
            return True
        return False

    def killall(self, name):
        rc, out, err = self.execute("ps ax | grep %s" % name, showout=False)
        for line in out.split("\n"):
            # print("L:%s" % line)
            if line.strip() == "":
                continue
            if "grep" in line:
                continue
            line = line.strip()
            pid = line.split(" ")[0]
            self.logger.info("kill:%s (%s)" % (name, pid))
            self.kill(pid)
        if self.psfind(name):
            raise RuntimeError(
                "Could not kill:%s, is still, there check if its not autorestarting." %
                name)

    def getPidsByFilterSortable(self, filterstr, sortkey=None):
        """
        Get pids of process by a filter string and optionally sort by sortkey

        @param filterstr string: filter string.
        @param sortkey   string: sort key for ps command
        sortkey can be one of the following:
            %cpu           cpu utilization of the process in
            %mem           ratio of the process's resident set size  to the physical memory on the machine, expressed as a percentage.
            cputime        cumulative CPU time, "[DD-]hh:mm:ss" format.  (alias time).
            egid           effective group ID number of the process as a decimal integer.  (alias gid).
            egroup         effective group ID of the process.  This will be the textual group ID, if it can be obtained and the field width permits, or a decimal representation otherwise.  (alias group).
            euid           effective user ID (alias uid).
            euser          effective user name.
            gid            see egid.  (alias egid).
            pid            a number representing the process ID (alias tgid).
            ppid           parent process ID.
            psr            processor that process is currently assigned to.
            start_time     starting time or date of the process.


        """
        if sortkey is not None:
            cmd = "ps aux --sort={sortkey} | grep '{filterstr}'".format(
                filterstr=filterstr, sortkey=sortkey)
        else:
            cmd = "ps ax | grep '{filterstr}'".format(filterstr=filterstr)
        rcode, out, err = j.sal.process.execute(cmd)
        # print out
        found = []
        for line in out.split("\n"):
            if line.find("grep") != -1 or line.strip() == "":
                continue
            if line.strip() != "":
                if line.find(filterstr) != -1:
                    line = line.strip()
                    if sortkey is not None:
                        found.append(int([x for x in line.split(" ") if x][1]))
                    else:
                        found.append(int(line.split(" ")[0]))
        return found

    def getPidsByFilter(self, filterstr):
        cmd = "ps ax | grep '%s'" % filterstr
        rcode, out, err = j.sal.process.execute(cmd)
        # print out
        found = []
        for line in out.split("\n"):
            if line.find("grep") != -1 or line.strip() == "":
                continue
            if line.strip() != "":
                if line.find(filterstr) != -1:
                    line = line.strip()
                    # print "found pidline:%s"%line

                    found.append(int(line.split(" ")[0]))
        return found

    def checkstart(self, cmd, filterstr, nrtimes=1, retry=1):
        """
        @param cmd is which command to execute to start e.g. a daemon
        @param filterstr is what to check on if its running
        @param nrtimes is how many processes need to run
        """

        found = self.getPidsByFilter(filterstr)
        for i in range(retry):
            if len(found) == nrtimes:
                return
            # print "START:%s"%cmd
            self.execute(cmd)
            time.sleep(1)
            found = self.getPidsByFilter(filterstr)
        if len(found) != nrtimes:
            raise j.exceptions.RuntimeError(
                "could not start %s, found %s nr of instances. Needed %s." % (cmd, len(found), nrtimes))

    def checkstop(self, cmd, filterstr, retry=1, nrinstances=0):
        """
        @param cmd is which command to execute to start e.g. a daemon
        @param filterstr is what to check on if its running
        @param nrtimes is how many processes need to run
        """

        found = self.getPidsByFilter(filterstr)
        for i in range(retry):
            if len(found) == nrinstances:
                return
            # print "START:%s"%cmd
            self.execute(cmd, die=False)
            time.sleep(1)
            found = self.getPidsByFilter(filterstr)
            for item in found:
                self.kill(int(item), 9)
            found = self.getPidsByFilter(filterstr)

        if len(found) != 0:
            raise j.exceptions.RuntimeError(
                "could not stop %s, found %s nr of instances." % (cmd, len(found)))

    def getProcessPid(self, process):
        if process is None:
            raise j.exceptions.RuntimeError("process cannot be None")
        if self.isUnix:
            # Need to set $COLUMNS such that we can grep full commandline
            # Note: apparently this does not work on solaris
            command = "bash -c 'env COLUMNS=300 ps -ef'"
            (exitcode, output, err) = j.sal.process.execute(
                command, die=False, showout=False)
            pids = list()
            co = re.compile(
                "\s*(?P<uid>[a-z]+)\s+(?P<pid>[0-9]+)\s+(?P<ppid>[0-9]+)\s+(?P<cpu>[0-9]+)\s+(?P<stime>\S+)\s+(?P<tty>\S+)\s+(?P<time>\S+)\s+(?P<cmd>.+)")
            for line in output.splitlines():
                match = co.search(line)
                if not match:
                    continue
                gd = match.groupdict()
                # print "%s"%line
                # print gd["cmd"]
                # print process
                if isinstance(process, int) and gd['pid'] == process:
                    pids.append(gd['pid'])
                elif gd['cmd'].find(process.strip()) != -1:
                    pids.append(gd['pid'])
            pids = [int(item) for item in pids]
            return pids
        else:
            raise NotImplementedError(
                "getProcessPid is only implemented for unix")

    def getMyProcessObject(self):
        return self.getProcessObject(os.getpid())

    def getProcessObject(self, pid):
        import psutil
        for process in psutil.process_iter():
            if process.pid == pid:
                return process
        raise j.exceptions.RuntimeError(
            "Could not find process with pid:%s" % pid)

    def getProcessPidsFromUser(self, user):
        import psutil
        result = []
        for process in psutil.process_iter():
            if process.username == user:
                result.append(process.pid)
        return result

    def killUserProcesses(self, user):
        for pid in self.getProcessPidsFromUser(user):
            j.sal.process.kill(pid)

    def getSimularProcesses(self):
        import psutil
        myprocess = self.getMyProcessObject()
        result = []
        for item in psutil.process_iter():
            try:
                if item.cmdline == myprocess.cmdline:
                    result.append(item)
            except psutil.NoSuchProcess:
                pass
        return result

    def checkProcessRunning(self, process, min=1):
        """
        Check if a certain process is running on the system.
        you can specify minimal running processes needed.
        @param process: String with the name of the process we
            are trying to check
        @param min: (int) minimal threads that should run.
        @return True if ok
        """
        self.logger.debug(
            'Checking whether at least %d processes %s are running' % (min, process))
        if self.isUnix:
            pids = self.getProcessPid(process)
            if len(pids) >= min:
                return True
            return False

        # Windows platform
        elif j.core.platformtype.myplatform.isWindows:

            return j.sal.windows.checkProcess(process, min)

    def checkProcessForPid(self, pid, process):
        """
        Check whether a given pid actually does belong to a given process name.
        @param pid: (int) the pid to check
        @param process: (str) the process that should have the pid
        @return status: (int) 0 when ok, 1 when not ok.
        """
        self.logger.info(
            'Checking whether process with PID %d is actually %s' % (pid, process))
        if self.isUnix:
            command = "ps -p %i" % pid
            (exitcode, output, err) = j.sal.process.execute(
                command, die=False, showout=False)
            i = 0
            for line in output.splitlines():
                if j.core.platformtype.myplatform.isLinux or j.core.platformtype.myplatform.isESX():
                    match = re.match(
                        ".{23}.*(\s|\/)%s(\s|$).*" % process, line)
                elif j.core.platformtype.myplatform.isSolaris():
                    match = re.match(
                        ".{22}.*(\s|\/)%s(\s|$).*" % process, line)
                if match:
                    i = i + 1
            if i >= 1:
                return 0
            return 1

        elif j.core.platformtype.myplatform.isWindows:

            return j.sal.windows.checkProcessForPid(process, pid)

    def setEnvironmentVariable(self, varnames, varvalues):
        """Set the value of the environment variables C{varnames}. Existing variable are overwritten

        @param varnames: A list of the names of all the environment variables to set
        @type varnames: list<string>
        @param varvalues: A list of all values for the environment variables
        @type varvalues: list<string>
        """
        try:
            for i in range(len(varnames)):
                os.environ[varnames[i]] = str(varvalues[i]).strip()
        except Exception as e:
            raise j.exceptions.RuntimeError(e)

    def getPidsByPort(self, port):
        """
        Returns pid of the process that is listening on the given port
        """
        name = self.getProcessByPort(port)
        if name is None:
            return []
        # print "found name:'%s'"%name
        pids = j.sal.process.getProcessPid(name)
        # print pids
        return pids

    def killProcessByName(self, name, sig=None):
        pids = self.getProcessPid(name)
        for pid in pids:
            self.kill(pid, sig)

    def killProcessByPort(self, port):
        for pid in self.getPidsByPort(port):
            self.kill(pid)

    def getProcessByPort(self, port):
        """
        Returns the full name of the process that is listening on the given port

        @param port: the port for which to find the command
        @type port: int
        @return: full process name
        @rtype: string
        """
        if port == 0:
            return None
        if j.core.platformtype.myplatform.isLinux:
            command = "netstat -ntulp | grep ':%s '" % port
            (exitcode, output, err) = j.sal.process.execute(
                command, die=False, showout=False)

            # Not found if grep's exitcode  > 0
            if not exitcode == 0:
                return None

            # Note: we can have multiline output. For example:
            #   tcp        0      0 0.0.0.0:5432            0.0.0.0:*               LISTEN      28419/postgres
            #   tcp6       0      0 :::5432                 :::*                    LISTEN      28419/postgres

            regex = "^.+\s(\d+)/.+\s*$"
            pid = -1
            for line in output.splitlines():
                match = re.match(regex, line)
                if not match:
                    raise j.exceptions.RuntimeError(
                        "Unexpected output from netstat -tanup: [%s]" % line)
                pid_of_line = match.groups()[0]
                if pid == -1:
                    pid = pid_of_line
                else:
                    if pid != pid_of_line:

                        raise j.exceptions.RuntimeError(
                            "Found multiple pids listening to port [%s]. Error." % port)
            if pid == -1:
                # No process found listening on this port
                return None

            # Need to set $COLUMNS such that we can grep full commandline
            # Note: apparently this does not work on solaris
            command = "bash -c 'env COLUMNS=300 ps -ef'"
            (exitcode, output, err) = j.sal.process.execute(
                command, die=False, showout=False)
            co = re.compile(
                "\s*(?P<uid>[a-z]+)\s+(?P<pid>[0-9]+)\s+(?P<ppid>[0-9]+)\s+(?P<cpu>[0-9]+)\s+(?P<stime>\S+)\s+(?P<tty>\S+)\s+(?P<time>\S+)\s+(?P<cmd>.+)")
            for line in output.splitlines():
                match = co.search(line)
                if not match:
                    continue
                gd = match.groupdict()
                if gd['pid'] == pid:
                    return gd['cmd'].strip()
            return None
        else:
            # TODO: needs to be validated on mac & windows
            import psutil
            for process in psutil.process_iter():
                try:
                    cc = [x for x in process.connections() if x.status ==
                          psutil.CONN_LISTEN]
                except Exception as e:
                    if str(e).find("psutil.AccessDenied") == -1:
                        raise j.exceptions.RuntimeError(str(e))
                    continue
                if cc != []:
                    for conn in cc:
                        portfound = conn.laddr[1]
                        if port == portfound:
                            return process
            return None
            # raise j.exceptions.RuntimeError("This platform is not supported in j.sal.process.getProcessByPort()")

    # IS NOW IN SYSTEMPPROCESS OLD no idea why we have all of this double
    # run = staticmethod(run)
    # runScript = staticmethod(runScript)
    # runDaemon = staticmethod(runDaemon)

    def getDefunctProcesses(self):
        rc, out, err = j.sal.process.execute("ps ax")
        llist = []
        for line in out.split("\n"):
            if line.strip() == "":
                continue
            if line.find("<defunct>") != -1:
                # print "defunct:%s"%line
                line = line.strip()
                pid = line.split(" ", 1)[0]
                pid = int(pid.strip())
                llist.append(pid)

        return llist

    def getEnviron(self, pid):
        environ = j.sal.fs.fileGetContents('/proc/%s/environ' % pid)
        env = dict()
        for line in environ.split('\0'):
            if '=' in line:
                key, value = line.split('=', 1)
                env[key] = value
        return env

    # DO NOT REENABLE, if you need it, call the j.sal.process.executeASyncIO

    # def executeAsync(self, command, args=[], printCommandToStdout=False, redirectStreams=True,
    #                  argsInCommand=False, useShell=None, showout=True):
    #     """ Execute command asynchronous. By default, the input, output and error streams of the command will be piped to the returned Popen object. Be sure to call commands that don't expect user input, or send input to the stdin parameter of the returning Popen object.
    #     @param command: Command to execute. (string)
    #     @param args: [Optional, [] by default] Arguments to be passed to the command. (Array of string)
    #     @param printCommandToStdOut: [Optional, False by default] Indicates if the command to be executed needs to be printed to screen. (boolean)
    #     @param redirectStreams: [Optional, True by default] Indicates if the input, output and error streams should be captured by the returned Popen object. If not, the output and input will be mixed with the streams of the calling process. (boolean)
    #     @param argsInCommand: [Optional, False by default] Indicates if the command-parameter contains command-line arguments.  If argsInCommand is False and args is not empty, the contents of args will be added to the command when executing.
    #     @param useShell: [Optional, False by default on Windows, True by default on Linux] Indicates if the command should be executed throug the shell.
    #     @return: If redirectStreams is true, this function returns a subprocess.Popen object representing the started process. Otherwise, it will return the pid-number of the started process.
    #     """
    #     if useShell is None:  # The default value depends on which platform we're using.
    #         if self.isUnix:
    #             useShell = True
    #         elif j.core.platformtype.myplatform.isWindows:
    #             useShell = False
    #         else:
    #             raise j.exceptions.RuntimeError("Platform not supported")
    #
    #     self.logger.info("system.process.executeAsync [%s]" % command)
    #     if printCommandToStdout:
    #         print(("system.process.executeAsync [%s]" % command))
    #
    #     if j.core.platformtype.myplatform.isWindows:
    #         if argsInCommand:
    #             cmd = subprocess.list2cmdline([command] + args)
    #         else:
    #             cmd = command
    #
    #         if redirectStreams:  # Process will be started and the Popen object will be returned. The calling function can use this object to read or write to its pipes or to wait for completion.
    #             retVal = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    #                                       stderr=subprocess.PIPE, env=os.environ, shell=useShell)
    #         else:
    #             # Process will be started without inheriting handles. Subprocess doesn't offer functionality to accomplish this, so we implement it ourselves using the lowlevel win32.CreateProcess method.
    #             # Example use-case: Image a vapp that contains a deamon that can be started using a control script, and we want to start this deamon after installation.
    #             #                   In this case, we want to call the control script from the install script using system.process.execute to be able to capture the output of the control script.
    #             #                   The control script in turn will start the daemon in an asynchronous way and is not interested in the output of the daemon.
    #             #                   If we would use the subprocess.Popen object to start the daemon in the control script, the stdout pipe of the control script will be inherited by the daemon,
    #             # it will not be closed before the control script AND the daemon have
    #             # ended both, so the install script will stay listening on the stdout pipe
    #             # as long as it exists and the system.process.execute() method will not
    #             # return until the daemon ends.
    #             from win32process import CreateProcess, STARTUPINFO, STARTF_USESHOWWINDOW
    #             from win32con import SW_HIDE
    #             sui = STARTUPINFO()
    #             if useShell:  # 4 lines below are copied from subprocess.Popen._execute_child().  (Code for Win9x is omitted as we only support WinXP and higher.)
    #                 sui.dwFlags |= STARTF_USESHOWWINDOW
    #                 sui.wShowWindow = SW_HIDE
    #                 comspec = os.environ.get("COMSPEC", "cmd.exe")
    #                 cmd = comspec + " /c " + cmd
    #             # Returns a handle for the created process, a handle for the main thread,
    #             # the identifier of the process (PID) and the identifier of the main
    #             # thread.
    #             hp, ht, pid, tid = CreateProcess(None,        # Executable
    #                                              cmd,         # Command Line
    #                                              None,        # Security Attributes for Process
    #                                              None,        # Securtiy Attributes for Thread
    #                                              0,           # Inherithandles = False(0)
    #                                              0,           # Creation Flags
    #                                              os.environ,  # Environment Settings (use the same as calling process)
    #                                              None,        # CurrentDir (Don't change)
    #                                              sui)         # Startup Information
    #             retVal = pid
    #
    #     elif self.isUnix:
    #         if useShell:
    #             if argsInCommand:
    #                 cmd = command
    #             else:
    #                 cmd = subprocess.list2cmdline([command] + args)
    #
    #             if redirectStreams:
    #                 retVal = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE,
    #                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
    #             else:
    #                 if showout:
    #                     proc = subprocess.Popen(cmd, shell=True, env=os.environ)
    #                 else:
    #                     devnull = open('/dev/null', 'w')
    #                     proc = subprocess.Popen(cmd, shell=True, env=os.environ, stdout=devnull, stderr=devnull)
    #                     devnull.close()
    #                 # Returning the pid, analogous to the windows implementation where we
    #                 # don't have a Popen object to return.
    #                 retVal = proc.pid
    #         else:
    #             # Not possible, only the shell is able to parse command line arguments form a space-separated string.
    #             if argsInCommand:
    #                 raise j.exceptions.RuntimeError(
    #                     "On Unix, either use the shell to execute a command, or split your command in an argument list")
    #             if redirectStreams:
    #                 retVal = subprocess.Popen([command] + args, shell=False, stdin=subprocess.PIPE,
    #                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
    #             else:
    #                 if showout:
    #                     proc = subprocess.Popen([command] + args, shell=False, env=os.environ)
    #                 else:
    #                     devnull = open('/dev/null', 'w')
    #                     proc = subprocess.Popen([command] + args, shell=False, env=os.environ,
    #                                             stdout=devnull, stderr=devnull)
    #                     devnull.close()
    #                 # Returning the pid, analogous to the windows implementation where we
    #                 # don't have a Popen object to return.
    #                 retVal = proc.pid
    #     else:
    #         raise j.exceptions.RuntimeError("Platform not supported")
    #
    #     return retVal
