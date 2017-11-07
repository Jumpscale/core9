from JumpScale9 import j
import time


class StoreFactory:
    '''
    The key value store factory provides logic to retrieve store instances. It
    also caches the stores based on their type, name and namespace.
    '''

    def __init__(self):
        self.__imports__ = "msgpack"
        self._cache = dict()
        self._redisCacheLocal = None

    # def getMongoDBStore(self, namespace='',serializers=[]):
    #     '''
    #     Gets an MongoDB key value store.

    #     @param namespace: namespace of the store, defaults to None
    #     @type namespace: String

    #     @return: key value store
    #     @rtype: ArakoonKeyValueStore
    #     '''
    #     from mongodb_store import MongoDBKeyValueStore
    #     key = '%s_%s' % ("arakoon", namespace)
    #     if key not in self._cache:
    #         if namespace=="":
    #             namespace="main"
    #         self._cache[key] = MongoDBKeyValueStore(namespace)
    #     return self._cache[key]

    def test(self):

        for db in [j.data.kvs.getRedisStore(name="kvs", namespace="testdb"), j.data.kvs.getMemoryStore()]:

            print(db)
            db.destroy()

            assert [] == db.list()

            # some basic tests

            db.set("mykey33", "string")
            val2 = db.get("mykey33")
            assert "string" == val2

            val = db.set("mykey34", b"byte")
            val2 = db.get("mykey34")
            assert b"byte" == val2

            val = db.set("mykey35", [1, 2, 3])
            val2 = db.get("mykey35")
            assert [1, 2, 3] == val2

            if db.type == "redis" or db.type == "mem":
                assert [] != db.keys

            db.destroy()
            assert [] == db.keys

            # test now expiration
            print("expiration test")
            db.set("mykey", "string", expire=1)

            assert "string" == db.get("mykey")
            time.sleep(2)

            assert None == db.get("mykey")

            db.destroy()

        # cache = j.data.kvs.getRedisCacheLocal()
        cache = None  # NOT IMPLEMENTED YET

        serializer = j.data.serializer.json
        db = j.data.kvs.getRedisStore(name="kvs", namespace="testdb", serializers=[serializer], cache=cache)
        db.destroy()
        obj = [1, 2, 3, 4]
        secret = j.data.hash.md5_string("a")  # generate whatever secret (needs to be 32 hex byte str eg result of md5)
        secret2 = j.data.hash.md5_string("b")
        acl = {secret: "r", secret2: "rwd"}

        db.set("mykey", obj, acl=acl, expire=10)
        assert db.get("mykey", secret=secret) == obj

        res = db.getraw("mykey", secret=secret)
        print(res)

        obj2 = [1, 2, 3, 4, 5]
        db.set("mykey", obj2, acl=acl, expire=0, secret=secret2)

        assert db.get("mykey", secret=secret) == obj2

        res2 = db.getraw("mykey", secret=secret)
        print(res2)

        # next should fail
        try:
            db.set("mykey", obj2, acl=acl, expire=0, secret=secret)
        except Exception as e:
            if "because mode 'w' is not allowed" not in str(e):
                raise j.exceptions.Input(
                    message="test failed, should not be allowed writing because of acl",
                    level=1,
                    source="",
                    tags="",
                    msgpub="")

        # on my laptop performance is 50k+ per sec, so good enough for now
        def encodetest():
            print("start encode test")
            for i in range(100000):
                res = db._encode(b"aaaaaaabbbbbbbbccccccddddddddeeeeeeeeffffffffff", expire=10, acl=acl)
            print("stop encode test")
            print("start decode test")
            for i in range(100000):
                res2 = db._decode(res)
            print("stop decode test")

        encodetest()

        print("test ok")

    def getRedisCacheLocal(self):
        """
        example:
        cache=j.data.kvs.getRedisCacheLocal()
        serializer=j.data.serializer.json
        db=j.data.kvs.getRedisStore(namespace="cache",serializers=[serializer],cache=cache)

        """
        # for now just local to test

        # the std redis is not on tcp, so this will not work in all cases, had to modify

        if self._redisCacheLocal is None:
            cache = self.getRedisStore(
                name='kvs-cache',
                namespace='cache',
                host='localhost',
                port=6379,
                db=0,
                password='',
                serializers=[]
            )
            try:
                cache.set("test", "test")
            except Exception as e:
                cache = self.getRedisStore('kvs-cache', namespace='cache', host='localhost',
                                           unixsocket='%s/redis.sock' % j.dirs.TMPDIR,
                                           db=0, password='',
                                           serializers=[])
                cache.set("test", "test")
            self._redisCacheLocal = cache

        return self._redisCacheLocal

    # def getFSStore(self, name, namespace='', baseDir=None, serializers=[], cache=None, changelog=None, masterdb=None):
    #     '''
    #     Gets a file system key value store.
    #
    #     @param namespace: namespace of the store, defaults to an empty string
    #     @type namespace: String
    #
    #     @param baseDir: base directory of the store, defaults to j.dirs.db
    #     @type namespace: String
    #
    #     @param defaultJSModelSerializer: default JSModel serializer
    #     @type defaultJSModelSerializer: Object
    #
    #     @return: key value store
    #     @rtype: FileSystemKeyValueStore
    #     '''
    #
    #     if serializers == []:
    #         serializers = [j.data.serializer.serializers.getMessagePack()]
    #
    #     if name not in self._cache:
    #         self._cache[name] = FileSystemKeyValueStore(
    #             name, namespace=namespace, baseDir=baseDir, serializers=serializers, cache=cache, masterdb=masterdb, changelog=changelog)
    #     return self._cache[name]
    #
    def getFileStore(self, name="core", namespace='db', baseDir='/tmp', serializers=[]):
        from JumpScale9.data.key_value_store.file_store import FileKeyValueStore
        return FileKeyValueStore(name=name, namespace=namespace, baseDir=baseDir, serializers=serializers)

    def getPickleDBStore(self, name="core", namespace='db', baseDir='/tmp', serializers=[]):
        from JumpScale9.data.key_value_store.pickledb_store import PickleDBStore
        return PickleDBStore(name=name, namespace=namespace, baseDir=baseDir, serializers=serializers)

    def getMemoryStore(self, name="core", namespace=None, changelog=None):
        '''
        Gets a memory key value store.

        @return: key value store
        @rtype: MemoryKeyValueStore
        '''
        from JumpScale9.data.key_value_store.memory_store import MemoryKeyValueStore
        return MemoryKeyValueStore(name=name, namespace=namespace)

    def getRedisStore(
            self,
            name="core",
            namespace='db',
            host='localhost',
            port=None,
            unixsocket=None,
            db=0,
            password='',
            serializers=None,
            masterdb=None,
            cache=None,
            changelog=None):
        '''
        Gets a memory key value store.

        @param name: name of the store
        @type name: String

        @param namespace: namespace of the store, defaults to None
        @type namespace: String

        @return: key value store
        @rtype: MemoryKeyValueStore
        '''
        if not port:
            port = 6379
            if j.core.state.configGetFromDict("redis", "port", ""):
                port = j.core.state.configGetFromDict("redis", "port")
        if not unixsocket:
            unixsocket = None
            if j.core.state.configGetFromDict("redis", "unixsocket", ""):
                port = j.core.state.configGetFromDict("redis", "unixsocket")

        from JumpScale9.data.key_value_store.redis_store import RedisKeyValueStore

        if j.clients.redis.get4core() is None:
            j.clients.redis.start4core()

        res = RedisKeyValueStore(
            name=name,
            namespace=namespace,
            host=host,
            port=port,
            unixsocket=unixsocket,
            db=db,
            password=password,
            serializers=serializers,
            masterdb=masterdb,
            changelog=changelog,
            cache=cache
        )

        return res

    def getARDBStore(
            self,
            name="core",
            namespace='db',
            host='localhost',
            port=16379,
            unixsocket=None,
            db=0,
            password='',
            serializers=None,
            masterdb=None,
            cache=None,
            changelog=None):
        '''
        Gets a memory key value store.

        @param name: name of the store
        @type name: String

        @param namespace: namespace of the store, defaults to None
        @type namespace: String

        @return: key value store
        @rtype: MemoryKeyValueStore
        '''
        from JumpScale9.data.key_value_store.ardb_store import ARDBKeyValueStore
        res = ARDBKeyValueStore(
            name=name,
            namespace=namespace,
            host=host,
            port=port,
            unixsocket=unixsocket,
            db=db,
            password=password,
            serializers=serializers,
            masterdb=masterdb,
            changelog=changelog,
            cache=cache
        )

        return res

    def getRocksDBStore(self, name, namespace='db', dbpath="/tmp/kvs.db",
                        serializers=None, masterdb=None, cache=None, changelog=None):
        '''
        Gets a RocksDB key value store.

        @param name: name of the store
        @type name: String

        @param namespace: namespace of the store, defaults to 'db'
        @type namespace: String

        @return: key value store
        @rtype: RocksDBKeyValueStore
        '''
        from JumpScale9.data.key_value_store.rocksdb_store import RocksDBKeyValueStore
        res = RocksDBKeyValueStore(
            name=name,
            namespace=namespace,
            dbpath=dbpath,
            serializers=serializers,
            masterdb=masterdb,
            changelog=changelog,
            cache=cache
        )

        return res

    def _aclSerialze(self, acl={}):
        """
        access list

        key is secret in 16 or 32 bytes (32 bytes will be hex2byte changed)
        val is "rwd"
        """

        #
        # access list
        #
        nrsecrets = 0
        secrets2 = b""
        for secret, aclitem in acl.items():
            acli = 0
            if "r" in aclitem:
                acli += 0b10000000

            if "w" in aclitem:
                acli += 0b01000000

            if "d" in aclitem:
                acli += 0b00100000

            finalacli = acli.to_bytes(1, byteorder='big', signed=False)

            if len(secret) == 32:
                secret = j.data.hash.hex2bin(secret)

            elif len(secret) != 16:
                raise j.exceptions.Input(message="secret needs to be 16 bytes", level=1, source="", tags="", msgpub="")

            nrsecrets += 1
            secrets2 += secret + finalacli

        if nrsecrets > 254:
            raise j.exceptions.Input(message="cannot have more than 254 secrets",
                                     level=1, source="", tags="", msgpub="")

        acls = nrsecrets.to_bytes(1, byteorder='big', signed=False) + secrets2

        return acls

    def _aclUnserialze(self, data):
        #
        # extracting acl
        #
        acl = {}
        counter = 0
        nrsecrets = int.from_bytes(data[counter:counter + 1], byteorder='big', signed=False)
        counter += 1
        for i in range(nrsecrets):

            secret = j.data.hash.bin2hex(data[counter:counter + 16])

            counter += 16

            access = data[counter:counter + 1]
            accessint = int.from_bytes(access, byteorder='big', signed=False)

            counter += 1

            astr = ""

            if accessint & 0b10000000:
                astr += "r"

            if accessint & 0b01000000:
                astr += "w"

            if accessint & 0b00100000:
                astr += "d"

            acl[secret.decode()] = astr
        return acl

    def _aclCheck(self, aclInObj, ownerInObj, secret, mode):
        """
        Check if user is allowed to do mode ("r", "w", "d")
        """
        if len(mode) > 1:
            res = True
            for modeitem in mode:
                res = res and self._aclCheck(aclInObj, ownerInObj, secret, modeitem)
            return res

        # owner got full right
        if len(secret) == 16:
            secret = j.data.hash.bin2hex(secret)

        if ownerInObj == secret:
            return True

        # if there is no acl, skipping
        if aclInObj == {}:
            # need to deny access if no acl list & is not owner
            return False

        #* means everyone
        if "*" in aclInObj:
            if mode in aclInObj["*"]:
                return True

        # user not found on acl
        if not aclInObj.get(secret):
            return False

        # checking mode
        if mode in aclInObj[secret]:
            return True

        return False

    # def getLevelDBStore(self, name, namespace='', basedir=None, serializers=[], cache=None, changelog=None, masterdb=None):
    #     '''
    #     Gets a leveldb key value store.
    #
    #     @param name: name of the store
    #     @type name: String
    #
    #     @param namespace: namespace of the store, defaults to ''
    #     @type namespace: String
    #
    #     @return: key value store
    #     '''
    #     from JumpScale9.data.key_value_store.leveldb_store import LevelDBKeyValueStore
    #     if name not in self._cache:
    #         self._cache[name] = LevelDBKeyValueStore(
    #             name=name, namespace=namespace, basedir=basedir, serializers=serializers, cache=cache, masterdb=masterdb, changelog=changelog)
    #     return self._cache[name]

    # def getTarantoolDBStore(self, name, namespace='', host='localhost', port=6379, db=0, password='', serializers=[], cache=None, changelog=None, masterdb=None):
    #     '''
    #     Gets a leveldb key value store.
    #
    #     @param name: name of the store
    #     @type name: String
    #
    #     @param namespace: namespace of the store, defaults to ''
    #     @type namespace: String
    #
    #     @return: key value store
    #     '''
    #     from JumpScale9.data.key_value_store.tarantool_store import TarantoolStore
    #     if name not in self._cache:
    #         self._cache[name] = TarantoolStore(namespace=namespace, host='localhost',
    #                                            port=6379, db=0, password='', serializers=serializers, cache=cache, masterdb=masterdb, changelog=changelog)
    #     return self._cache[name]
