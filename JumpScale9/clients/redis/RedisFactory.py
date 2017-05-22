from JumpScale9 import j


from .Redis import Redis
from .RedisQueue import RedisQueue
import os
import time
# import sys
from redis._compat import nativestr
# import itertools
import socket


class RedisFactory:

    """
    """

    def __init__(self):
        self.clearCache()
        self.__jslocation__ = "j.clients.redis"

    def clearCache(self):
        self._redis = {}
        self._redisq = {}
        self._config = {}

    def get(
            self,
            ipaddr="localhost",
            port=6379,
            password="",
            fromcache=True,
            unixsocket=None,
            ardb_patch=False,
            **args):
        if unixsocket is None:
            key = "%s_%s" % (ipaddr, port)
        else:
            key = unixsocket
        if key not in self._redis or not fromcache:
            if unixsocket is None:
                self._redis[key] = Redis(ipaddr, port, password=password, **args)  # , unixsocket=unixsocket)
            else:
                self._redis[key] = Redis(unix_socket_path=unixsocket, password=password, **args)

        if ardb_patch:
            self._ardb_patch(self._redis[key])

        return self._redis[key]

    def _ardb_patch(self, client):
        client.response_callbacks['HDEL'] = lambda r: r and nativestr(r) == 'OK'

    def getQueue(self, ipaddr, port, name, namespace="queues", fromcache=True):
        if not fromcache:
            return RedisQueue(self.get(ipaddr, port, fromcache=False), name, namespace=namespace)
        key = "%s_%s_%s_%s" % (ipaddr, port, name, namespace)
        if key not in self._redisq:
            self._redisq[key] = RedisQueue(
                self.get(ipaddr, port), name, namespace=namespace)
        return self._redisq[key]

    def get4core(self):
        """
        will try to create redis connection to $tmpdir/redis.sock
        if that doesn't work then will look for std redis port
        if that does not work then will return None
        """
        if "TMPDIR" in os.environ:
            tmpdir = os.environ["TMPDIR"]
        else:
            tmpdir = "/tmp"

        unix_socket_path = '%s/redis.sock' % tmpdir

        db = None
        if os.path.exists(path=unix_socket_path):
            db = Redis(unix_socket_path=unix_socket_path)
        elif self._tcpPortConnectionTest("localhost", 6379, timeout=None):
            db = Redis()

        # try:
        #     j.core.db.set("internal.last", 0)
        #     return True
        # except:
        #     db = None

        return db

    def _tcpPortConnectionTest(self, ipaddr, port, timeout=None):
        conn = None
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if timeout:
                conn.settimeout(timeout)
            try:
                conn.connect((ipaddr, port))
            except BaseException:
                return False
        finally:
            if conn:
                conn.close()
        return True

    def kill(self):
        j.sal.process.execute("redis-cli -s %s/redis.sock shutdown" %
                              j.do.TMPDIR, die=False, showout=False, outputStderr=False)
        j.sal.process.execute("redis-cli shutdown", die=False, showout=False, outputStderr=False)
        j.do.killall("redis")

    def start4core(self):
        """
        starts a redis instance in separate ProcessLookupError
        standard on $tmpdir/redis.sock
        """
        if j.core.platformtype.myplatform.isMac:
            if not j.do.checkInstalled("redis-server"):
                j.sal.process.execute("brew unlink redis", die=False)
                j.sal.process.execute("brew install redis;brew link redis")
            if not j.do.checkInstalled("redis-server"):
                raise RuntimeError("Cannot find redis-server even after install")
            j.sal.process.execute("redis-cli -s %s/redis.sock shutdown" %
                                  j.do.TMPDIR, die=False, showout=False, outputStderr=False)
            j.sal.process.execute("redis-cli shutdown", die=False, showout=False, outputStderr=False)
        elif j.core.platformtype.myplatform.isLinux:
            if j.core.platformtype.myplatform.isAlpine:
                os.system("apk add redis")
            elif j.core.platformtype.myplatform.isUbuntu:
                os.system("apt install redis-server -y")
        else:
            raise RuntimeError("platform not supported for start redis")

        # cmd = "redis-server --port 6379 --unixsocket %s/redis.sock --maxmemory 100000000 --daemonize yes" % tmpdir  # 100MB
        # print("start redis in background (osx)")
        # os.system(cmd)
        # print("started")
        # time.sleep(1)
        # elif j.core.platformtype.myplatform.isCygwin:
        #     cmd = "redis-server --maxmemory 100000000 & "
        #     print("start redis in background (win)")
        #     os.system(cmd)

        cmd = "echo never > /sys/kernel/mm/transparent_hugepage/enabled"
        os.system(cmd)
        cmd = "sysctl vm.overcommit_memory=1"
        os.system(cmd)

        redis_bin = "redis-server"
        if "TMPDIR" in os.environ:
            tmpdir = os.environ["TMPDIR"]
        else:
            tmpdir = "/tmp"
        cmd = "%s  --port 0 --unixsocket %s/redis.sock --maxmemory 100000000" % (redis_bin, tmpdir)
        print(cmd)
        j.sal.process.execute(
            "redis-server --port 6379 --unixsocket %s/redis.sock --maxmemory 100000000 --daemonize yes" % tmpdir)
