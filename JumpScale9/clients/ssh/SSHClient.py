from js9 import j

import paramiko
from paramiko.ssh_exception import SSHException, BadHostKeyException, AuthenticationException
import time
import socket
import os
import threading
import queue
import io


class StreamReader(threading.Thread):

    def __init__(self, stream, channel, queue, flag):
        super(StreamReader, self).__init__()
        self.stream = stream
        self.channel = channel
        self.queue = queue
        self.flag = flag
        self._stopped = False
        self.setDaemon(True)

    def run(self):
        """
        read until all buffers are empty and retrun code is ready
        """
        while not self.stream.closed and not self._stopped:
            buf = ''
            buf = self.stream.readline()
            if len(buf) > 0:
                self.queue.put((self.flag, buf))
            elif not self.channel.exit_status_ready():
                continue
            elif self.flag == 'O' and self.channel.recv_ready():
                continue
            elif self.flag == 'E' and self.channel.recv_stderr_ready():
                continue
            else:
                break
        self.queue.put(('T', self.flag))


class SSHClient:

    def __init__(
            self,
            addr='',
            port=22,
            login="root",
            passwd=None,
            usesproxy=False,
            stdout=True,
            forward_agent=True,
            allow_agent=True,
            look_for_keys=True,
            key_filename=None,
            passphrase=None,
            timeout=5.0):
        self._lock = threading.Lock()
        self.port = port
        self.addr = addr
        self.login = login
        self.passwd = passwd
        self.stdout = stdout
        self.timeout = timeout
        self.allow_agent = allow_agent
        if passwd:
            self.forward_agent = False
            self.look_for_keys = False
            self.key_filename = None
            self.passphrase = None
        else:
            self.forward_agent = forward_agent
            self.look_for_keys = look_for_keys
            self.key_filename = key_filename
            self.passphrase = passphrase

        self.logger = j.logger.get("ssh sync client: %s(%s):" % (self.addr, self.port))

        self._transport = None
        self._client = None
        self._prefab = None
        self.usesproxy = usesproxy

    def _test_local_agent(self):
        """
        try to connect to the local ssh-agent
        return True if local agent is running, False if not
        """
        agent = paramiko.Agent()
        if len(agent.get_keys()) == 0:
            return False
        else:
            return True

    def connectViaProxy(self, host, username, port, identityfile, proxycommand=None):
        self.usesproxy = True
        client = paramiko.SSHClient()
        client._policy = paramiko.WarningPolicy()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        import os.path
        self.host = host
        cfg = {'hostname': host, 'username': username, "port": port}
        self.addr = host
        self.user = username

        if identityfile is not None:
            cfg['key_filename'] = identityfile
            self.key_filename = cfg['key_filename']

        if proxycommand is not None:
            cfg['sock'] = paramiko.ProxyCommand(proxycommand)
        cfg['timeout'] = 5
        cfg['allow_agent'] = True
        cfg['banner_timeout'] = 5
        self.cfg = cfg
        self.forward_agent = True
        self._client = client
        self._client.connect(**cfg)

        return self._client

    @property
    def transport(self):
        if self.client is None:
            raise j.exceptions.RuntimeError("Could not connect to %s:%s" % (self.addr, self.port))
        return self.client.get_transport()

    def _connect(self):
        # with self._lock:
        self.logger.info("Test sync ssh connection to %s:%s:%s" % (self.addr, self.port, self.login))

        if j.sal.nettools.waitConnectionTest(self.addr, self.port, self.timeout) is False:
            self.logger.error("Cannot connect to ssh server %s:%s with login:%s and using sshkey:%s" %
                              (self.addr, self.port, self.login, self.key_filename))
            return None

        self.pkey = None
        if self.key_filename is not None and self.key_filename != '':
            self.pkey = paramiko.RSAKey.from_private_key_file(self.key_filename, password=self.passphrase)

        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if self.key_filename:
            self.allow_agent = True
            self.look_for_keys = True
            if j.clients.ssh.SSHKeyGetPathFromAgent(self.key_filename, die=False) is not None and not self.passphrase:
                j.clients.ssh.SSHKeysLoad(self.key_filename)

        start = j.data.time.getTimeEpoch()
        while start + self.timeout > j.data.time.getTimeEpoch():
            try:
                self.logger.info("connect to:%s" % self.addr)
                self._client.connect(
                    self.addr,
                    self.port,
                    username=self.login,
                    password=self.passwd,
                    pkey=self.pkey,
                    allow_agent=self.allow_agent,
                    look_for_keys=self.look_for_keys,
                    timeout=2.0,
                    banner_timeout=3.0)
                self.logger.info("connection ok")
                return self._client

            except (BadHostKeyException, AuthenticationException) as e:
                self.logger.error("Authentification error. Aborting connection : %s" % str(e))
                self.logger.error(str(e))
                raise j.exceptions.RuntimeError(str(e))

            except (SSHException, socket.error) as e:
                self.logger.error(
                    "Unexpected error in socket connection for ssh. Aborting connection and try again.")
                self.logger.error(e)
                self._client.close()
                # self.reset()
                time.sleep(1)
                continue

            except Exception as e:
                j.clients.ssh.removeFromCache(self)
                msg = "Could not connect to ssh on %s@%s:%s. Error was: %s" % (self.login, self.addr, self.port, e)
                raise j.exceptions.RuntimeError(msg)

        if self._client is None:
            raise j.exceptions.RuntimeError('Impossible to create SSH connection to %s:%s' % (self.addr, self.port))

    @property
    def client(self):
        if self._client is None:
            self._connect()
        return self._client

    def reset(self):
        with self._lock:
            if self._client is not None:
                self._client = None

    def getSFTP(self):
        self.logger.info("open sftp")
        sftp = self.client.open_sftp()
        return sftp

    def execute(self, cmd, showout=True, die=True):
        """
        run cmd & return
        return: (retcode,out_err)
        """
        ch = None
        # with self._lock:
        ch = self.transport.open_session()

        if self.forward_agent:
            paramiko.agent.AgentRequestHandler(ch)

        # execute the command on the remote server
        ch.exec_command(cmd)
        # indicate that we're not going to write to that channel anymore
        ch.shutdown_write()
        # create file like object for stdout and stderr to read output of
        # command
        stdout = ch.makefile('r')
        stderr = ch.makefile_stderr('r')

        # Start stream reader thread that will read strout and strerr
        inp = queue.Queue()
        outReader = StreamReader(stdout, ch, inp, 'O')
        errReader = StreamReader(stderr, ch, inp, 'E')
        outReader.start()
        errReader.start()

        err = io.StringIO()  # error buffer
        out = io.StringIO()  # stdout buffer
        out_eof = False
        err_eof = False

        while out_eof is False or err_eof is False:
            try:
                chan, line = inp.get(block=True, timeout=1.0)
                if chan == 'T':
                    if line == 'O':
                        out_eof = True
                    elif line == 'E':
                        err_eof = True
                    continue
                line = j.data.text.toAscii(line)
                if chan == 'O':
                    if showout:
                        with self._lock:
                            self.logger.info(line.rstrip())
                    out.write(line)
                elif chan == 'E':
                    if showout:
                        with self._lock:
                            self.logger.error(line.rstrip())
                    err.write(line)
            except queue.Empty:
                pass

        # stop the StreamReader and wait for the thread to finish
        outReader._stopped = True
        errReader._stopped = True
        outReader.join()
        errReader.join()

        # indicate that we're not going to read from this channel anymore
        ch.shutdown_read()
        # close the channel
        ch.close()

        # close all the pseudofiles
        stdout.close()
        stderr.close()

        rc = ch.recv_exit_status()

        if rc and die:
            raise j.exceptions.RuntimeError(
                "Cannot execute (ssh):\n%s\noutput:\n%serrors:\n%s" % (cmd, out.getvalue(), err.getvalue()))

        return rc, out.getvalue(), err.getvalue()

    def close(self):
        if self.client is not None:
            self.client.close()

    def rsync_up(self, source, dest, recursive=True):
        if dest[0] != "/":
            raise j.exceptions.RuntimeError(
                "dest path should be absolute, need / in beginning of dest path")

        dest = "%s@%s:%s" % (self.login, self.addr, dest)
        j.do.copyDirTree(
            source,
            dest,
            keepsymlinks=True,
            deletefirst=False,
            overwriteFiles=True,
            ignoredir=[
                ".egg-info",
                ".dist-info",
                "__pycache__"],
            ignorefiles=[".egg-info"],
            rsync=True,
            ssh=True,
            sshport=self.port,
            recursive=recursive)

    def rsync_down(self, source, dest, source_prefix="", recursive=True):
        if source[0] != "/":
            raise j.exceptions.RuntimeError(
                "source path should be absolute, need / in beginning of source path")
        source = "%s@%s:%s" % (self.login, self.addr, source)
        j.do.copyDirTree(
            source,
            dest,
            keepsymlinks=True,
            deletefirst=False,
            overwriteFiles=True,
            ignoredir=[
                ".egg-info",
                ".dist-info"],
            ignorefiles=[".egg-info"],
            rsync=True,
            ssh=True,
            sshport=self.port,
            recursive=recursive)

    @property
    def prefab(self):
        if not self.usesproxy and self._prefab is None:
            executor = j.tools.executor.getSSHBased(self.addr, self.port, self.login, self.passwd)
            self._prefab = executor.prefab
        if self.usesproxy:
            ex = j.tools.executor.getSSHViaProxy(self.host)
            self._prefab = j.tools.prefab.get(self)
        return self._prefab

    def ssh_authorize(self, user, key):
        self.prefab.ssh.authorize(user, key)

    def portforwardToLocal(self, remoteport, localport):
        self.portforwardKill(localport)
        C = "ssh -L %s:localhost:%s root@%s -p %s" % (remoteport, localport, self.addr, self.port)
        print(C)
        j.tools.prefab.local.processmanager.ensure(cmd=C, name="ssh_%s" % localport, wait=0.5)
        print("Test tcp port to:%s" % localport)
        if not j.sal.nettools.waitConnectionTest("127.0.0.1", localport, 10):
            raise RuntimeError("Cannot open ssh forward:%s_%s_%s" % (self, remoteport, localport))
        print("Connection ok")

    def portforwardKill(self, localport):
        print("kill portforward %s" % localport)
        j.tools.prefab.local.processmanager.stop('ssh_%s' % localport)
