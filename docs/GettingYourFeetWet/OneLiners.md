
We will talk today on some examples of what jumpscale provides for you to make your life easier.

## Generating ID
Generating IDs is very essential (GUID, random int, Id of specific length)

```ipython

In [1]: j.data.idgenerator.generateGUID()
Out[1]: 'ebc7e5a1-7639-42a6-8e53-901cee6c931b'

In [2]: j.data.idgenerator.generateRandomInt(1, 29)
Out[2]: 25

In [3]: j.data.idgenerator.generateXCharID(20)
Out[3]: '9ifglpbab8mf7ay6pkks'


```
You can even create a capnp id
```ipython

In [4]: j.data.idgenerator.generateCapnpID()
Out[4]: '0x9863fa568bb0f744'

```

## Data serialization

You can serialize (dump) and deserialize (load) your data form and to many data formats (base64, hrd, msgpack, lzma, pickle, snappy, toml, ujson, yaml) with the same interfaces

`j.data.serializer.`yourserializer.`dumps/loads`
```IPython

In [15]: obj = [1,2,3,4]

In [16]: j.data.serializer.yaml.dumps(obj)
Out[16]: '[1, 2, 3, 4]\n'

In [17]: h2=j.data.serializer.yaml.loads(_)


In [18]: h2
Out[18]: [1, 2, 3, 4]


```

## Hashing
Jumpscale supports many hashing algorithms like (crc, md5, sha*, blake2) with interface to hash (strings, filedescriptors, paths).
```ipython
In [22]: j.data.hash.md5("/home/ahmed/1.xml")
Out[22]: 'a1cba27e3905ab8a87e23f4247f0783c'

In [23]: j.data.hash.md5("/home/ahmed/1.xml")
Out[23]: 'a1cba27e3905ab8a87e23f4247f0783c'

In [24]: pprint(j.data.hash.hashDir("/home/ahmed/wspace/attrdict/"))
('a03714c32f1bf93be0ec138a7828a197',
 b'a8ba672d93697971031015181d7008c3|.git/COMMIT_EDITMSG\n0650081b0c8c21786f3'
 b'3370dbcc20a7e|.git/FETCH_HEAD\n4cf2d64e44205fe628ddd534e1151b58|.git/HEAD'
 b'\n990f1e08576e4e4b1492a142141aa5aa|.git/ORIG_HEAD\n0f60315a5ee638518cdbed4'
 b'6b4fb566c|.git/config\na0a7c3fff21f2aea3cfa1d0316dd816c|.git/description\n'
 b'ce562e08d8098926a3862fc6e7905199|.git/hooks/applypatch-msg.sample\n579a3c'
 b'1e12a1e74a98169175fb913012|.git/hooks/commit-msg.sample\n2b7ea5cee3c49ff5'
 b'3d41e00785eb974c|.git/hooks/post-update.sample\n054f9ffb8bfe04a599751cc75'
 b'7226dda|.git/hooks/pre-applypatch.sample\n01b1688f97f94776baae85d77b06048'
 b'b|.git/hooks/pre-commit.sample\n3c5989301dd4b949dfa1f43738a22819|.git/hoo'
 b'ks/pre-push.sample\n3ff6ba9cf6d8e5332978e057559b5562|.git/hooks/pre-rebas'
 b'e.sample\n7dfe15854212a30f346da5255c1d794b|.git/hooks/prepare-commit-msg.'
 b'sample\nf51b02427757e79621b5235d7efdf117|.git/hooks/update.sample\n58befc9'
 b'cffd0e803cef26937064ab7d9|.git/index\n036208b4a1ab4a235d75c181e685e5a3|.g'
 b'it/info/exclude\nb2c436f2b321c5887c4663a439e9196a|.git/logs/HEAD\nb2c436f2'
 b'b321c5887c4663a439e9196a|.git/logs/refs/heads/master\n1b2eb649d8cb8028e49'
 b'f9214747841d6|.git/logs/refs/remotes/origin/master\n9ff68db58b10564ebae06'
 b'392da0e220e|.git/objects/1d/bc687de014ee027b4e6c0d7f2a37ee7636137e\n50414'
 b'84adfd0c0c248bbf01afe185c92|.git/objects/5a/5d387731d8406b30049641c9396b9184'
 b'ab787e\n38881406bf9e7dfe0b7c6d5231d456eb|.git/objects/78/091299df38c8b8c3'
 b'eb7f8ba77e900bbb0d0a6e\ne962bd5910d29e438833f1df82cbf498|.git/objects/78/'
 b'faa91cd17b2a9439b4537898c335f86de39a8e\n4fb9ee5a29654637ce2a1b56269ab15b|'
 b'.git/objects/7e/a3aba7b297151581037b559c46ed8f16e7cadd\n2b9bcba7b49e2e0d6'
 b'59b4ddeff394f56|.git/objects/b9/dd24da737ae3496cdda521f4b2dc9d388937df\ne'
 b'500b4255e5ccd6522665e473deb6e2f|.git/objects/bd/24b79930f6093a288904408c9c62'
 b'bcb0b91f30\nf021c19346d92699d3fcdf48cd9c6c4e|.git/objects/f2/2555c431dd7d'
 b'e3cb6c577a02304dd3518183ac\n3e83fc05e0d661f25c42d6382ab8cb35|.git/refs/he'
 b'ads/master\n3e83fc05e0d661f25c42d6382ab8cb35|.git/refs/remotes/origin/mas'
 b'ter\n740bcc7fa7d48710fdcd1c49f11acb93|.gitignore\n70b1515752a3ece4a8f504a2'
 b'f5d5a918|attrdict.py\n')


```
In general with reimplementing that in python you will go with something like that
```python
def hash_fd(fd, alg):

    impl = hashlib.new(alg)

    blocksize = impl.block_size

    while True:
        s = fd.read(blocksize)
        if not s:
            break
        impl.update(s)
        # Maybe one day this will help the GC
        del s

    return impl.hexdigest()

```

## Units
You can easily convert from a size unit to another (from MB to KB maybe) or display what unit fits a number the best

```ipython
In [41]: j.data_units.sizes.converToBestUnit(2048*2**5, 'M')
Out[41]: (65.536, 'G')

In [42]: j.data_units.sizes.toSize(2048*2**5, 'M', 'G')
Out[42]: 65.536
```

## Daemonizing a process
To demonize a process it requires tedious including a double fork , chdir, becoming session leader , `dup` stdout and stderr

Something like this

```python
if not hasattr(os, 'fork'):
    raise j.exceptions.RuntimeError(
        'os.fork not found, daemon mode not supported on your system')

import threading
if threading.activeCount() > 1:
    j.errorhandler.raiseWarning(
        'You application got running threads, this can cause issues when using fork')

pid = os.fork()
if pid == 0:
    # First child
    # Become session leader...
    os.setsid()

    # Double fork
    pid = os.fork()
    if pid == 0:
        # Second child
        if umask >= 0:
            os.umask(umask)
        if chdir:
            os.chdir(chdir)
    else:
        # First child is useless now
        os._exit(0)
else:
    return False, os.getpid()

# Close all FDs
import resource
maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
if maxfd == resource.RLIM_INFINITY:
    maxfd = 1024

sys.stdin.close()
sys.stdout.close()
sys.stderr.close()

for fd in range(maxfd):
    try:
        os.close(fd)
    except OSError:
        pass

# Open fd0 to /dev/null
redirect = getattr(os, 'devnull', '/dev/null')
os.open(redirect, os.O_RDWR)

# dup to stdout and stderr
os.dup2(0, 1)
os.dup2(0, 2)
```

you can easily achieve that with `j.sal.unix.daemonize`

## Tidy your markdown

Markdown is awesome and we want to get it tidied everynow and then.
```python
j.tools.markdown.tidy(mddirectorypath)

```

instead of something like that
```python
def tidy(self, path=""):
    """
    walk over files & tidy markdown
    only look for .md files
    if path=="" then start from current path
    """
    if path == "":
        path = j.do.getcwd()
    for item in j.do.listFilesInDir(path, True, filter="*.md"):
        cmd = "cat %s|tidy-markdown" % item
        rc, out, err = j.sal.process.execute(cmd)
        if rc == 0 and len(out.strip()) > 0:
            j.do.writeFile(filename=item, contents=out, append=False)

```

```
!!!
title = "OneLiners"
date = "2017-04-08"
tags = []
```
