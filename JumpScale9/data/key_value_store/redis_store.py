from JumpScale9.data.key_value_store.store import KeyValueStoreBase
from js9 import j

import re

# import time
#
#
# def chunks(l, n):
#     for i in range(0, len(l), n):
#         yield l[i:i + n]


class RedisKeyValueStore(KeyValueStoreBase):

    def __init__(
            self,
            name,
            namespace="db",
            host='localhost',
            port=6379,
            unixsocket=None,
            db=0,
            password='',
            serializers=[],
            masterdb=None,
            cache=None,
            changelog=None):

        self.redisclient = j.clients.redis.get(host, port, password=password, unixsocket=unixsocket)
        # self.redisclient.port = port
        # self.redisclient.host = host
        KeyValueStoreBase.__init__(self, namespace=namespace, name=name, serializers=serializers,
                                   masterdb=masterdb, cache=cache, changelog=changelog)
        self._indexkey = "index:%s" % namespace

        self.inMem = False
        self.type = "redis"

        self.logger = j.logger.get("j.data.kvs.redis")

    def _getKey(self, key):
        return '%s:%s' % (self.namespace, key)

    def _get(self, key):
        return self.redisclient.get(self._getKey(key))

    def _set(self, key, val, expire=None):
        return self.redisclient.set(self._getKey(key), val, ex=expire)

    def _delete(self, key):
        return self.redisclient.delete(self._getKey(key))

    def _exists(self, key):
        return self.redisclient.exists(self._getKey(key))

    @property
    def keys(self):
        l = len(self.namespace) + 1
        res = [item.decode()[l:] for item in self.redisclient.keys(self.namespace + ":*")]
        return res

    def increment(self, key):
        # only overrule if supporting DB has better ways
        return self.redisclient.incr(self._getKey(key))

    def index(self, items, secret=""):
        """
        @param items is {indexitem:key}
            indexitem is e.g. $actorname:$state:$role (is a text which will be index to key)
            key links to the object in the db
        ':' is not allowed in indexitem
        """
        # if in non redis, implement as e.g. str index in 1 key and if gets too big then create multiple
        for key, val in items.items():
            current_val = self.redisclient.hget(self._indexkey, key)
            if current_val is not None:
                current_val = current_val.decode()
                if val not in current_val.split(','):
                    current_val += "," + val
                    self.redisclient.hset(self._indexkey, key, current_val)
            else:
                self.redisclient.hset(self._indexkey, key, val)
        return True

    def index_destroy(self):
        self.redisclient.delete(self._indexkey)
        self.redisclient.delete(self._indexkey + "lookup")

    def index_remove(self, keys, secret=""):
        """
        @param keys is the key to remove from index
        """
        if not isinstance(keys, list):
            keys = [keys]
        for key in keys:
            if self.redisclient.hexists(self._indexkey, key):
                self.redisclient.hdel(self._indexkey, key)

    def list(self, regex=".*", returnIndex=False, secret=""):
        """
        regex is regex on the index, will return matched keys
        e.g. .*:new:.* would match all actors with state new
        """
        res = set()
        for item in self.redisclient.hkeys(self._indexkey):
            item = item.decode()
            if re.match(regex, item) is not None:
                key = self.redisclient.hget(self._indexkey, item)
                if key:
                    key = key.decode()
                else:
                    continue
                if returnIndex is False:
                    for key2 in key.split(","):
                        res.add(key2)
                else:
                    for key2 in key.split(","):
                        res.add((item, key2))
        return list(res)

    def _getQueueNameKey(self, name):
        return "%s:queue:%s" % (self.namespace, name)

    def queueSize(self, name):
        """Return the approximate size of the queue."""
        return self.redisclient.llen(self._getQueueNameKey(name))

    def queuePut(self, name, item):
        """Put item into the queue."""
        self.redisclient.rpush(self._getQueueNameKey(name), item)

    def queueGet(self, name, timeout=20):
        """Remove and return an item from the queue."""
        if timeout > 0:
            item = self.redisclient.blpop(self._getQueueNameKey(name), timeout=timeout)
            if item:
                item = item[1]
        else:
            item = self.redisclient.lpop(self._getQueueNameKey(name))
        return item

    def queueFetch(self, name, block=True, timeout=None):
        """ Like get but without remove"""
        if block:
            item = self.redisclient.brpoplpush(self._getQueueNameKey(name), self._getQueueNameKey(name), timeout)
        else:
            item = self.redisclient.lindex(self._getQueueNameKey(name), 0)
        return item

    def lookupSet(self, name, key, fkey):
        # self.logger.info("lookupset:%s,%s,%s"%(name,key,fkey))
        self.redisclient.hset(self._indexkey + "lookup", key, fkey)

    def lookupGet(self, name, key):
        res = self.redisclient.hget(self._indexkey + "lookup", key)
        # self.logger.info("lookupset:%s,%s,%s"%(name,key,fkey))
        return res

    def lookupDestroy(self, name):
        self.redisclient.delete(self._indexkey + "lookup")

    def delete(self, key):
        if self.exists(key):
            self._delete(key)

        for k, v in self.redisclient.hgetall(self._indexkey).items():
            if v == key:
                self.redisclient.hdel(self._indexkey, v)
