
# TODO: *1 is this still used somewhere, we have so much duplication

import sys
import os
import os.path
import re
import select
import time
import subprocess
import signal
from subprocess import Popen


from js9 import j


# Fix subprocess.Popen EINTR issues
# The _communicate method on Unix uses select(2) to monitor stdout/err pipes,
# which can raise an exception (EINTR) whenever the parent process receives a
# signal (or the system call is interrupted for some other reason), eg a
# SIGCHLD when the actual subprocess stops.
# This was partially fixed in Python 2.6.0, but not completely. This code
# replaces the standard implementation with a patched one based on the code
# in Python 2.6.0, a patch in Python bug #1068268
#(http://bugs.python.org/issue1068268) and a patch applied to the Python2.5
# package in Ubuntu Linux (http://patches.ubuntu.com/p/python2.5/extracted/
#        subprocess-eintr-safety.dpatch)
mswindows = (j.core.platformtype.myplatform == "win32")
# Bump this version number as long as the upstream subprocess module is not
# fixed. Testcases on Solaris tend to fail easily.
if sys.version_info >= (2, 7, 0) or mswindows:
    SafePopen = subprocess.Popen
else:
    import types
    import errno
    import gc
    import traceback
    import pickle

    class SafePopen(subprocess.Popen):
        # Make sure we wrap this for Unix/win32 splitup if ever we need some
        # win32-specific fixes (see original subprocess.Popen)

        def communicate(self, input=None):
            # This is based on code in CPython 2.6.0, but including some extra
            # checks to emulate 2.5 behavior which didn't close stdout/err.
            if [self.stdin, self.stdout, self.stderr].count(None) >= 2:
                stdout = None
                stderr = None
                if self.stdin:
                    if input:
                        #MOD - 1068268
                        self._fo_write_no_intr(self.stdin, input)
                        # END MOD
                    self.stdin.close()
                elif self.stdout:
                    #MOD - 1068268
                    stdout = self._fo_read_no_intr(self.stdout)
                    # END MOD
                    # MOD
                    if sys.version_info >= (2, 7):
                        self.stdout.close()
                    # END MOD
                elif self.stderr:
                    #MOD - 1068268
                    stderr = self._fo_read_no_intr(self.stderr)
                    # END MOD
                    # MOD
                    if sys.version_info >= (2, 7):
                        self.stderr.close()
                    # END MOD
                self.wait()
                return (stdout, stderr)

            return self._communicate(input)

        if sys.version_info < (2, 6):
            def _communicate(self, input):
                # This is subprocess.Popen._communicate in the non-win32 case of
                # Python 2.5.2, as found on
                # http://svn.python.org/projects/python/tags/r252/Lib/subprocess.py
                # 2 modifications were made: a minor self-check, and an exception
                # handling clause around select.select as found in the version of
                # subprocess.Popen._communicate of Python 2.6.0
                # The differences found in the patch of 1068268 are applied as
                # well, similar to the 2.6.0 _communicate

                # First we'll check whether 'self' got all attributes used in this
                # method, to catch issues with older versions of subprocess.Popen.
                # MOD START
                for attr in ('stdin', 'stdout', 'stderr',
                             'universal_newlines', '_translate_newlines',
                             'wait', ):
                    if not hasattr(self, attr):
                        # This implementation can't be used, use the original
                        return subprocess.Popen._communicate(self, input)
                # MOD END
                read_set = []
                write_set = []
                stdout = None  # Return
                stderr = None  # Return

                if self.stdin:
                    # Flush stdio buffer.  This might block, if the user has
                    # been writing to .stdin in an uncontrolled fashion.
                    self.stdin.flush()
                    if input:
                        write_set.append(self.stdin)
                    else:
                        self.stdin.close()
                if self.stdout:
                    read_set.append(self.stdout)
                    stdout = []
                if self.stderr:
                    read_set.append(self.stderr)
                    stderr = []

                input_offset = 0
                while read_set or write_set:
                    #MOD - 1068268
                    # Handle EINTR in select(2)
                    import select
                    try:
                        rlist, wlist, xlist = select.select(read_set, write_set, [])
                    except select.error as e:
                        if e.args[0] == errno.EINTR:
                            continue
                        raise
                    # MOD END

                    if self.stdin in wlist:
                        # When select has indicated that the file is writable,
                        # we can write up to PIPE_BUF bytes without risk
                        # blocking.  POSIX defines PIPE_BUF >= 512
                        #MOD - 1068268
                        bytes_written = self._write_no_intr(self.stdin.fileno(),
                                                            buffer(input, input_offset, 512))
                        # END MOD
                        input_offset += bytes_written
                        if input_offset >= len(input):
                            self.stdin.close()
                            write_set.remove(self.stdin)

                    if self.stdout in rlist:
                        #MOD - 1068268
                        data = self._read_no_intr(self.stdout.fileno(), 1024)
                        # END MOD
                        if data == "":
                            self.stdout.close()
                            read_set.remove(self.stdout)
                        stdout.append(data)

                    if self.stderr in rlist:
                        #MOD - 1068268
                        data = self._read_no_intr(self.stderr.fileno(), 1024)
                        # END MOD
                        if data == "":
                            self.stderr.close()
                            read_set.remove(self.stderr)
                        stderr.append(data)

                # All data exchanged.  Translate lists into strings.
                if stdout is not None:
                    stdout = ''.join(stdout)
                if stderr is not None:
                    stderr = ''.join(stderr)

                # Translate newlines, if requested.  We cannot let the file
                # object do the translation: It is based on stdio, which is
                # impossible to combine with select (unless forcing no
                # buffering).
                if self.universal_newlines and hasattr(file, 'newlines'):
                    if stdout:
                        stdout = self._translate_newlines(stdout)
                    if stderr:
                        stderr = self._translate_newlines(stderr)

                self.wait()
                return (stdout, stderr)

        # sys.version_info >= (2, 6)
        # We only patch 2.6.0 though, bump this if necessary
        elif sys.version < (2, 7, 0):
            def _communicate(self, input):
                # This is _communicate of Python 2.6.0 + partial application of
                #patch in 1068268
                read_set = []
                write_set = []
                stdout = None  # Return
                stderr = None  # Return

                if self.stdin:
                    # Flush stdio buffer.  This might block, if the user has
                    # been writing to .stdin in an uncontrolled fashion.
                    self.stdin.flush()
                    if input:
                        write_set.append(self.stdin)
                    else:
                        self.stdin.close()
                if self.stdout:
                    read_set.append(self.stdout)
                    stdout = []
                if self.stderr:
                    read_set.append(self.stderr)
                    stderr = []

                input_offset = 0
                while read_set or write_set:
                    try:
                        rlist, wlist, xlist = select.select(read_set, write_set, [])
                    except select.error as e:
                        if e.args[0] == errno.EINTR:
                            continue
                        raise

                    if self.stdin in wlist:
                        # When select has indicated that the file is writable,
                        # we can write up to PIPE_BUF bytes without risk
                        # blocking.  POSIX defines PIPE_BUF >= 512
                        chunk = input[input_offset: input_offset + 512]
                        #MOD - 1068268
                        bytes_written = self._write_no_intr(self.stdin.fileno(),
                                                            chunk)
                        # END MOD
                        input_offset += bytes_written
                        if input_offset >= len(input):
                            self.stdin.close()
                            write_set.remove(self.stdin)

                    if self.stdout in rlist:
                        #MOD - 1068268
                        data = self._read_no_intr(self.stdout.fileno(), 1024)
                        # END MOD
                        if data == "":
                            self.stdout.close()
                            read_set.remove(self.stdout)
                        stdout.append(data)

                    if self.stderr in rlist:
                        #MOD - 1068268
                        data = self._read_no_intr(self.stderr.fileno(), 1024)
                        # END MOD
                        if data == "":
                            self.stderr.close()
                            read_set.remove(self.stderr)
                        stderr.append(data)

                # All data exchanged.  Translate lists into strings.
                if stdout is not None:
                    stdout = ''.join(stdout)
                if stderr is not None:
                    stderr = ''.join(stderr)

                # Translate newlines, if requested.  We cannot let the file
                # object do the translation: It is based on stdio, which is
                # impossible to combine with select (unless forcing no
                # buffering).
                if self.universal_newlines and hasattr(file, 'newlines'):
                    if stdout:
                        stdout = self._translate_newlines(stdout)
                    if stderr:
                        stderr = self._translate_newlines(stderr)

                self.wait()
                return (stdout, stderr)

        def _execute_child(self, args, executable, preexec_fn, close_fds,
                           cwd, env, universal_newlines,
                           startupinfo, creationflags, shell,
                           p2cread, p2cwrite,
                           c2pread, c2pwrite,
                           errread, errwrite):
            """Execute program (POSIX version)"""

            if isinstance(args, str):
                args = [args]
            else:
                args = list(args)

            if shell:
                args = ["/bin/sh", "-c"] + args

            if executable is None:
                executable = args[0]

            # For transferring possible exec failure from child to parent
            # The first char specifies the exception type: 0 means
            # OSError, 1 means some other error.
            errpipe_read, errpipe_write = os.pipe()
            self._set_cloexec_flag(errpipe_write)

            gc_was_enabled = gc.isenabled()
            # Disable gc to avoid bug where gc -> file_dealloc ->
            # write to stderr -> hang.  http://bugs.python.org/issue1336
            gc.disable()
            try:
                self.pid = os.fork()
            except BaseException: if gc_was_enabled:
                    gc.enable()
                raise
            self._child_created = True
            if self.pid == 0:
                # Child
                try:
                    # Close parent's pipe ends
                    if p2cwrite is not None:
                        os.close(p2cwrite)
                    if c2pread is not None:
                        os.close(c2pread)
                    if errread is not None:
                        os.close(errread)
                    os.close(errpipe_read)

                    # Dup fds for child
                    if p2cread is not None:
                        os.dup2(p2cread, 0)
                    if c2pwrite is not None:
                        os.dup2(c2pwrite, 1)
                    if errwrite is not None:
                        os.dup2(errwrite, 2)

                    # Close pipe fds.  Make sure we don't close the same
                    # fd more than once, or standard fds.
                    if p2cread is not None and p2cread not in (0,):
                        os.close(p2cread)
                    if c2pwrite is not None and c2pwrite not in (p2cread, 1):
                        os.close(c2pwrite)
                    if errwrite is not None and errwrite not in (p2cread, c2pwrite, 2):
                        os.close(errwrite)

                    # Close all other fds, if asked for
                    if close_fds:
                        self._close_fds(but=errpipe_write)

                    if cwd is not None:
                        os.chdir(cwd)

                    if preexec_fn:
                        preexec_fn()

                    if env is None:
                        os.execvp(executable, args)
                    else:
                        os.execvpe(executable, args, env)

                except BaseException:                    exc_type, exc_value, tb = sys.exc_info()
                    # Save the traceback and attach it to the exception object
                    exc_lines = traceback.format_exception(exc_type,
                                                           exc_value,
                                                           tb)
                    exc_value.child_traceback = ''.join(exc_lines)
                    #MOD - 1068268
                    self._write_no_intr(errpipe_write, pickle.dumps(exc_value))
                    # END MOD

                # This exitcode won't be reported to applications, so it
                # really doesn't matter what we return.
                os._exit(255)

            # Parent
            if gc_was_enabled:
                gc.enable()
            os.close(errpipe_write)
            if p2cread is not None and p2cwrite is not None:
                os.close(p2cread)
            if c2pwrite is not None and c2pread is not None:
                os.close(c2pwrite)
            if errwrite is not None and errread is not None:
                os.close(errwrite)

            # Wait for exec to fail or succeed; possibly raising exception
            #MOD - 1068268
            data = self._read_no_intr(errpipe_read, 1048576)  # Exceptions limited to 1 MB
            # END MOD
            os.close(errpipe_read)
            if data != "":
                #MOD - 1068268
                self._waitpid_no_intr(self.pid, 0)
                # END MOD
                child_exception = pickle.loads(data)
                raise child_exception

        def _fixed_poll(self, _deadstate=None):
            """Check if child process has terminated.  Returns returncode
            attribute."""
            if self.returncode is None:
                try:
                    #MOD - 1068268
                    pid, sts = self._waitpid_no_intr(self.pid, os.WNOHANG)
                    # END MOD
                    if pid == self.pid:
                        self._handle_exitstatus(sts)
                except os.error:
                    if _deadstate is not None:
                        self.returncode = _deadstate
            return self.returncode

        # poll became _internal_poll in 2.6
        if sys.version_info >= (2, 7):
            _internal_poll = _fixed_poll
        else:
            poll = _fixed_poll

        def wait(self):
            """Wait for child process to terminate.  Returns returncode
            attribute."""
            if self.returncode is None:
                #MOD - 1068268
                pid, sts = self._waitpid_no_intr(self.pid, 0)
                # END MOD
                self._handle_exitstatus(sts)
            return self.returncode

        def _read_no_intr(self, fd, buffersize):
            """Like os.read, but retries on EINTR"""
            while True:
                try:
                    return os.read(fd, buffersize)
                except OSError as e:
                    if e.errno == errno.EINTR:
                        continue
                    else:
                        raise

        def _write_no_intr(self, fd, s):
            """Like os.write, but retries on EINTR"""
            while True:
                try:
                    return os.write(fd, s)
                except OSError as e:
                    if e.errno == errno.EINTR:
                        continue
                    else:
                        raise

        def _waitpid_no_intr(self, pid, options):
            """Like os.waitpid, but retries on EINTR"""
            while True:
                try:
                    return os.waitpid(pid, options)
                except OSError as e:
                    if e.errno == errno.EINTR:
                        continue
                    else:
                        raise

        def _fo_read_no_intr(self, obj):
            """Like obj.read(), but retries on EINTR"""
            while True:
                try:
                    return obj.read()
                except IOError as e:
                    if e.errno == errno.EINTR:
                        continue
                    else:
                        raise

        def _fo_write_no_intr(self, obj, data):
            """Like obj.write(), but retries on EINTR"""
            while True:
                try:
                    return obj.write(data)
                except IOError as e:
                    if e.errno == errno.EINTR:
                        continue
                    else:
                        raise

if sys.version_info < (2, 6):
    # Add terminate() and kill() as introduced in Python2.6
    import signal

    class SafePopen(SafePopen):
        if j.core.platformtype.myplatform.isWindows:
            def send_signal(self, sig):
                '''Send a signal to the process'''
                if sig == signal.SIGTERM:
                    self.terminate()
                else:
                    raise ValueError('Only SIGTERM is supported on Windows')

            def terminate(self):
                '''Terminate the process'''
                from _subprocess import TerminateProcess
                TerminateProcess(self._handle, 1)

            kill = terminate

        else:
            def send_signal(self, sig):
                '''Send a signal to the process'''
                os.kill(self.pid, sig)

            def terminate(self):
                '''Terminate the process with SIGTERM'''
                self.send_signal(signal.SIGTERM)

            def kill(self):
                '''Kill the process with SIGKILL'''
                self.send_signal(signal.SIGKILL)


def _safe_subprocess(*args, **kwargs):
    '''Create a L{subprocess.Popen} object in a safe way

    This function will disable all threaded log targets before creating the
    subprocess (which forks, introducing lots of troubles in threaded
    application), and re-enable these log targets afterwards.

    The arguments provided to this method are copied verbatim to the
    L{subprocess.Popen} constructor.

    @see: L{subprocess.Popen}
    '''
    # Close all threaded log targets before creating a subprocess, which forks
    ##from JumpScale9AYS.core.log.LogTargets import ThreadedLogTarget
    # ThreadedLogTarget.disable_all_instances(close=True)

    try:
        # Make sure we re-enable logging, even when subprocess creation fails
        process = SafePopen(*args, **kwargs)
    finally:
        # Re-enable afterwards
        # ThreadedLogTarget.enable_all_instances()
        pass

    return process


def _convert_uid_gid(user, group):
    '''Convert a given user and/or group to the UID/GID

    This function calculates UID and GID of a given user and/or group name or
    ID, performing several sanity checks on the provided values and system
    environment.

    This function is used by runDaemon and executeAsUser. If it returns without
    exceptions, there's a rather big chance setuid/setgid will work fine.

    @param user: Username or UID of user to setuid() to
    @type user: string or number
    @param group: Groupname of GID of group to setgid() to
    @type group: string or number

    @returns: Calculated UID and GID
    @rtype: tuple<number, number>
    '''
    uid, gid = None, None

    def _convert(value, name, idname, setfunc, namfunc, idfield, idfunc):
        '''Convert a given name of ID to a system ID, validating all input

        The returned value will be C{None} if user or group is not given.

        @param value: Name or ID of the user/group to lookup
        @type value: string or number
        @param name: Human-readable name of the object type to lookup, 'user'
                     or 'group'
        @type name: string
        @param idname: Human-readable name of the resulting ID, 'UID' or 'GID'
        @type idname: string
        @param setfunc: Name of the function (attribute of the 'os' module)
                        used to switch to the desired system ID, 'setuid' or
                        'setgid'
        @type setfunc: string
        @param namfunc: Function used to retrieve information of a system
                        object based on its name, pwd.getpwnam or grp.getgrnam
        @type namfunc: callable
        @param idfield: Name of the attribute of the value returned by
                        C{namfunc} containing the ID, 'pw_uid' or 'gr_gid'
        @type idfield: string
        @param idfunc: Function used to retrieve information of a system
                       object based on its name, pwd.getpwuid or grp.getgruid
        @type idfunc: callable

        @returns: ID of the given system object name
        @rtuple: number
        '''
        # Used in some exception strings
        cname = name.capitalize()

        # Validation: does os.set*id exist?
        if not hasattr(os, setfunc):
            raise j.exceptions.RuntimeError('%s provided but %s() not available on '
                                            'this platform' % (cname, setfunc))

        # We want to make sure we're running as root. This requires os.getuid
        if not hasattr(os, 'getuid'):
            raise j.exceptions.RuntimeError('No getuid() available on this platform')
        if os.getuid() != 0:
            raise ValueError('%s argument only supported when running '
                             'as root' % cname)

        # If the given value is not a string, assume its a *ID
        if not isinstance(value, str):
            id_ = value
        else:
            try:
                # Lookup object information
                data = namfunc(value)
                # And retrieve the *ID field
                id_ = getattr(data, idfield)
            except KeyError:
                # Unless the object can't be found
                raise ValueError('Unknown %s %s' % (name, value))

        # Make sure we're really using an integer
        try:
            id_ = int(id_)
        except (ValueError, TypeError):
            raise ValueError('Provided %s should be a number' % idname)

        # Check whether there's a reverse mapping of the *ID to a system object
        # We don't want people to use *IDs of unknown system objects
        try:
            idfunc(id_)
        except KeyError:
            raise ValueError('Invalid %s %d' % (idname, id_))

        return id_

    # Calculate UID
    if user is not None:
        import pwd

        uid = _convert(user, 'user', 'UID', 'setuid', pwd.getpwnam, 'pw_uid',
                       pwd.getpwuid)

    # Calculate GID
    if group is not None:
        import grp

        gid = _convert(group, 'group', 'GID', 'setgid', grp.getgrnam, 'gr_gid',
                       grp.getgrgid)

    # Return them
    return uid, gid


def run(commandline, showOutput=False, captureOutput=True, maxSeconds=0,
        stopOnError=True, user=None, group=None, **kwargs):
    '''Execute a command and wait for its termination

    This function spawns a subprocess which executes the given command line in a
    subshell. The function waits for the spawned process to terminate, or until
    a time period of maxSeconds was exceeded.

    When showOutput is set to True, stdin, stderr and stdout handles of the
    subprocess are bound to the handles of the calling process. This can be used
    to run interactive commands.

    Both showOutput and captureOutput can't be True at the same time.

    Any extra keyword arguments are passed to L{subprocess.Popen}. These
    arguments can overwrite any argument set by this function, so setting any of
    the arguments used by this function (including C{stdin}, C{stdout},
    C{stderr}, C{env}, C{shell} and C{preexec_fn}) can change the behavior
    of this function. This could e.g. be used to set C{cwd}.

    The exit code contained in the returned tuple is the exit code of the
    spawned process if equal to or larger than 0. If the subprocess was killed
    while running, the exit code will be -1. If the process was stopped because
    maxSeconds was exceeded, an exit code equal to -2 will be returned.

    If user or group is defined (as name of number), the process will
    setuid/setgid to this user and group before executing the command line,
    effectively running the child process with the privileges of the provided
    user and group.

    Remarks:
     * Don't use the '&' shell operator to run a process in the background, use
       the startDaemon function instead
     * Shell operators including pipes and redirects are allowed in the
       command line string
     * When spawning processes which generate large amounts of output, make sure
       you set captureOutput to False, otherwise too much data will be buffered
       in memory
     * If captureOutput is set to False, the values of stdout and stderr in the
       return value will be empty strings
     * If stopOnError is set to True, the calling process will exit with exit
       code 44 if the child process returned a non-zero exit code, or 45 if the
       child process exceeds maxSeconds

    @param commandline: Command line string to execute
    @type commandline: string
    @param showOutput: Bind stdin/stdout/stderr to parent process
    @type showOutput: bool
    @param captureOutput: Capture generated output
    @type captureOutput: bool
    @param maxSeconds: Maximum number of seconds the subprocess should be
                       allowed to run
    @type maxSeconds: number
    @param stopOnError: Quit the caller process when the subprocess fails
    @type stopOnError: bool
    @param user: Username or UID of user to setuid() to
    @type user: string or number
    @param group: Groupname of GID of group to setgid() to
    @type group: string or number
    @param kwargs: Extra arguments passed through to L{subprocess.Popen}

    @return: Tuple containing subprocess exitcode, stdout and stderr output
    @rtype: tuple(number, string, string)
    '''
    env = kwargs.pop('env', os.environ)
    env = env.copy()

    # Calculate UID and GID t run as
    if user is not None or group is not None:
        uid, gid = _convert_uid_gid(user, group)

        # Once we reached this point, we can be pretty sure the uid and gid
        # variables can be passed to processhelper.py with only a slight
        # chance of things going wrong in there

        jumpscale_path = os.path.join(j.dirs.JSBASEDIR, 'lib', 'jumpscale', 'core')

        cmd = list()
        cmd.append(sys.executable)

        cmd.extend(('-c', '\'from JumpScale9AYS.sal.process.processhelper import main; main()\'', ))

        if uid is not None:
            cmd.extend(('--uid', '%d' % uid, ))
        if gid is not None:
            cmd.extend(('--gid', '%d' % gid, ))

        cmd.append('--')
        cmd.append(commandline)

        commandline = ' '.join(cmd)

        # TODO Do we want to cleanup the environment, eg HOME and USER?
        # See Trac #165
        path = env.get('PYTHONPATH', None)
        if path:
            path = os.pathsep.join((jumpscale_path, path, ))
        else:
            path = jumpscale_path
        env['PYTHONPATH'] = path

    return _runWithEnv(commandline, showOutput=showOutput,
                       captureOutput=captureOutput, maxSeconds=maxSeconds,
                       stopOnError=stopOnError, env=env, **kwargs)


def _runWithEnv(commandline, showOutput=False, captureOutput=True, maxSeconds=0,
                stopOnError=True, env=None, **kwargs):
    '''Execute a command and wait for its termination

    This method provides the same functionality as L{run}, but also allows a
    caller to provide an environment dictionary. If this is L{None}, an empty
    environment will be used.

    @see: run
    @param env: Environment to run the subprocess in
    @type env: dict
    '''
    # This list will contain callables executed at the end to clean up everything
    # where necessary, eg closing file descriptors
    cleanup = list()
    # Did we have to kill the subprocess (because maxSeconds timed out?)
    killed = False

    if captureOutput and showOutput:
        raise ValueError('captureOutput and showOutput are mutually exclusive')

    j.sal.process.logger.debug(
        'system.process.start "%s" maxSeconds=%d stopOnError=%s' %
        (commandline, maxSeconds, stopOnError))

    if captureOutput and not showOutput:
        stdin = None
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE
    elif showOutput and not captureOutput:
        stdin = sys.stdin
        stdout = sys.stdout
        stderr = sys.stderr
    elif not showOutput and not captureOutput:
        # There's no place like devnull
        fd = open(getattr(os, 'devnull',
                          'nul' if j.core.platformtype.myplatform.isWindows else '/dev/null'),
                  'rw')
        stdin = stdout = stderr = fd

        def cleanup_fd():
            fd.close()

        cleanup.append(cleanup_fd)

    # Set up the arguments we want...
    subprocess_kwargs = {
        'stdin': stdin,
        'stdout': stdout,
        'stderr': stderr,
        'shell': True,
        'env': env,
        'close_fds': True,
    }
    if j.core.platformtype.myplatform.isWindows:
        # Reset all signals before calling execlp but after forking. This
        # fixes Python issue 1652 (http://bugs.python.org/issue1652) and
        # jumpscale ticket 189
        def reset_signals():
            '''Reset all signals to SIG_DFL'''
            for i in range(1, signal.NSIG):
                if signal.getsignal(i) != signal.SIG_DFL:
                    try:
                        signal.signal(i, signal.SIG_DFL)
                    except RuntimeError:
                        # Skip, can't set this signal
                        pass

        subprocess_kwargs['preexec_fn'] = reset_signals

    # ... and overwrite with user-provided
    subprocess_kwargs.update(kwargs)

    process = _safe_subprocess(commandline, **subprocess_kwargs)

    if maxSeconds <= 0:
        if captureOutput:
            out, err = process.communicate()
        else:
            process.wait()
            out = err = ''

        code = -1 if process.returncode < 0 else process.returncode
        ret = (code, out, err)

    else:  # maxSeconds set
        start = time.time()
        # Use maxSeconds - 1 to make sure the function actually waits only
        # maxSeconds. If maxSeconds <= 1, use maxSeconds.
        timediff = maxSeconds - 1 if maxSeconds > 1 else maxSeconds
        while time.time() - start < timediff and process.poll() is None:
            # Wait 0.1 seconds between subprocess polling during the first 3
            # seconds the process runs. Bump this polling interval to 1s when
            # this threshold is reached.
            if time.time() - start < 3:
                time.sleep(0.1)
            else:
                time.sleep(1)

        if process.poll() is None:
            # Child is still running, kill it
            if j.core.platformtype.myplatform.isUnix:
                # Soft and hard kill on Unix
                try:
                    process.terminate()
                    # Give the process some time to settle
                    time.sleep(0.2)
                    process.kill()
                except OSError:
                    pass
            else:
                # Kill on anything else
                time.sleep(0.1)
                if process.poll():
                    process.terminate()

            killed = True

        if captureOutput and not killed:
            # Subprocess stopped in-time, let's read the output
            out = process.stdout.read()
            err = process.stderr.read()
        elif captureOutput and killed:
            # Subprocess had to be killed. This causes funny situations if we'd
            # want to read the output streams now (blocking read hangs the
            # application, whilst the intermediate shell goes into zombie mode,
            # fun).

            # Read out process streams, but don't block
            if j.core.platformtype.myplatform.isUnix:
                def readout(stream):
                    # Non-blocking, safe UNIX-style stream readout
                    import fcntl
                    import select
                    # Store original flags
                    flags = fcntl.fcntl(stream, fcntl.F_GETFL)
                    if not stream.closed:
                        # Set non-blocking
                        fcntl.fcntl(stream, fcntl.F_SETFL,
                                    flags | os.O_NONBLOCK)

                    # Store all intermediate data
                    data = list()
                    try:
                        while True:
                            # Check whether more data is available
                            if not select.select([stream], [], [], 0)[0]:
                                # If not, kthxbye
                                break

                            # Read out all available data
                            line = stream.read()
                            if not line:
                                break

                            # Honour subprocess univeral_newlines
                            if process.universal_newlines:
                                line = process._translate_newlines(line)

                            # Add data to cache
                            data.append(line)

                    finally:
                        # Don't forget to reset stream flags
                        # Although normally the stream won't ever be used after
                        # this
                        if not stream.closed:
                            fcntl.fcntl(stream, fcntl.F_SETFL, flags)

                    # Fold cache and return
                    return ''.join(data)

            else:
                # This is not UNIX, most likely Win32. read() seems to work
                def readout(stream):
                    return stream.read()

            out = readout(process.stdout)
            err = readout(process.stderr)

        else:
            out = err = ''

        code = -1 if process.returncode < 0 else process.returncode
        code = -2 if killed else code
        ret = (code, out, err)

    # Run cleanup callables
    for func in cleanup:
        func()

    j.sal.process.logger.debug('system.process.run ended, exitcode was %d' %
                               ret[0])
    j.sal.process.logger.debug('system.process.run stdout:\n%s' % ret[1])
    j.sal.process.logger.debug('system.process.run stderr:\n%s' % ret[2])

    # 45 first, since -2 != 0
    if stopOnError and killed:
        j.sal.process.logger.debug(
            'system.process.start had to kill the subprocess')
        sys.exit(45)
    if stopOnError and ret[0] != 0:
        j.sal.process.logger.debug('system.process.start subprocess failed')
        sys.exit(44)

    return ret


def runScript(script, showOutput=False, captureOutput=True, maxSeconds=0,
              stopOnError=True):
    '''Execute a Python script

    This function executes a Python script, making sure the script output will
    not be buffered.

    For an overview of the parameters and function behavior, see the
    documentation of L{jumpscale.system.process.run}.

    @param script: Script to execute
    @type script: string

    @return: Tuple containing subprocess exitcode, stdout and stderr output
    @rtype: tuple(number, string, string)

    @raise ValueError: Script is not an existing file

    @see: jumpscale.system.process.run
    '''
    if not j.do.isFile(script):
        raise ValueError('Unable to execute %s: not an existing file' % script)

    cmdline = '%s -u "%s"' % (sys.executable, script)
    j.sal.process.logger.info('Executing script: %s' % cmdline, 6)

    return run(cmdline, showOutput=showOutput, captureOutput=captureOutput,
               maxSeconds=maxSeconds, stopOnError=stopOnError)


def runDaemon(commandline, stdout=None, stderr=None, user=None, group=None,
              env=None):
    '''Run an application as a background process

    This function will execute the given commandline decoupled from the host
    process by forking first. The stdout and stderr streams of the spawned
    application can be redirected to files.

    This can be compared to using

        nohup myapplication -u -b 1 &

    in a Bash shell.

    If no stdout or stderr paths are provided, those streams are ignored.

    If user or group is defined (as name of number), the daemon process will
    setuid/setgid to this user and group before executing the child process,
    effectively running the daemon process with the privileges of the provided
    user and group.

    If C{env} is provided, it will be used as environment in which the daemon
    process will be executed. If it is not set, C{os.environ} will be used. Do
    note C{PYTHONUNBUFFERED} and C{PYTHONPATH} will be slightly altered (in a
    copy of the provided dictionary) by this function before spawning the
    daemon process.

    @param commandline: Command line string to execute
    @type commandline: string
    @param stdout: Path to file to redirect stdout
    @type stdout: string
    @param stderr: Path to file to redirect stderr
    @type stderr: string
    @param user: Username or UID of user to setuid() to
    @type user: string or number
    @param group: Groupname of GID of group to setgid() to
    @type group: string or number
    @param env: Environment settings for the daemon
    @type env: dict

    @return: PID of the daemonized process
    @rtype: number
    '''
    logmessage = list()
    logmessage.append('Running command \'%s\' as daemon process' % commandline)
    if stdout is not None:
        logmessage.append('redirecting stdout to \'%s\'' % stdout)
    if stderr is not None:
        logmessage.append('redirecting stderr to \'%s\'' % stderr)
    if user is not None:
        logmessage.append('setuid to user %s' % str(user))
    if group is not None:
        logmessage.append('setgid to group %s' % str(group))
    logmessage = ', '.join(logmessage)
    j.sal.process.logger.info(logmessage)

    uid, gid = _convert_uid_gid(user, group)

    # Once we reached this point, we can be pretty sure the uid and gid
    # variables can be passed to processhelper.py with only a slight chance of
    # things going wrong in there

    jumpscale_path = os.path.join(j.dirs.JSBASEDIR, 'lib', 'jumpscale', 'core')

    cmd = list()
    cmd.append(sys.executable)

    cmd.extend(('-c', '\'from JumpScale9AYS.sal.process.processhelper import main; main()\'', ))

    if stdout:
        j.do.createDir(os.path.dirname(stdout))
        cmd.extend(('--stdout', '"%s"' % stdout, ))
    if stderr:
        j.do.createDir(os.path.dirname(stderr))
        cmd.extend(('--stderr', '"%s"' % stderr, ))

    if uid is not None:
        cmd.extend(('--uid', '%d' % uid, ))
    if gid is not None:
        cmd.extend(('--gid', '%d' % gid, ))

    cmd.append('--daemonize')

    cmd.append('--')
    cmd.append(commandline)

    cmd = ' '.join(cmd)

    env = env.copy() if env else os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    path = env.get('PYTHONPATH', None)
    if path:
        path = os.pathsep.join((jumpscale_path, path, ))
    else:
        path = jumpscale_path
    env['PYTHONPATH'] = path

    code, out, err = _runWithEnv(cmd, env=env)

    processdata = dict(line.split('=', 1) for line in out.splitlines())

    childpid = int(processdata['CHILDPID'])

    logmessage = list()
    logmessage.append('Started daemon process \'%s\'' % commandline)
    logmessage.append('PID is %d' % childpid)
    if 'UID' in processdata:
        logmessage.append('UID is %d' % int(processdata['UID']))
    if 'GID' in processdata:
        logmessage.append('GID is %d' % int(processdata['GID']))
    logmessage = ', '.join(logmessage)
    j.sal.process.logger.debug(logmessage)

    return childpid


class _Unset:
    '''Value used in L{calculateEnvironment} to remove an item from the output'''


UNSET = _Unset()
del _Unset


def calculateEnvironment(values, source=None):
    '''Merge new keys in an environment dict

    All key/value pairs in the C{values} dict will be merged into the C{source}
    dict, which defaults to the current environment values, C{os.environ}.

    If L{UNSET} is used as a value in C{values}, the value will be removed from
    the result.

    Sample usage:

        >>> os_environ = {
        ...     'PATH': '/bin:/usr/bin',
        ...     'USER': 'root',
        ...     'PWD': '/root',
        ... }
        >>> myenv = {
        ...     'USER': UNSET,
        ...     'PWD': '/tmp',
        ... }
        >>> result = calculateEnvironment(myenv, os_environ)
        >>> print result['PATH']
        /bin:/usr/bin
        >>> print result['PWD']
        /tmp
        >>> print 'USER' in result
        False

    @param values: Values to merge into the environment
    @type values: dict
    @param source: Source environment, defaults to os.environ
    @type source: dict

    @return: Merged environment
    @rtype: dict
    '''
    source = os.environ if source is None else source
    result = source.copy()

    result.update(values)

    result = dict((k, v) for (k, v) in list(result.items()) if v is not UNSET)

    return result
