import struct

import time

try:
    import regex
except BaseException:
    pass


class DispersedBlock:

    def __init__(self):
        self.subblocks = []

    def create(self, s, nrblocks, extrablocks, compress=True):
        pass


class ByteProcessor:
    'ByteProcessor'
    @staticmethod
    def hashMd5(s):
        import hashlib
        if isinstance(s, str):
            s = s.encode('utf-8')
        impl = hashlib.md5(s)
        return impl.hexdigest()

    @staticmethod
    def hashTiger160(s):
        import mhash
        if isinstance(s, str):
            s = s.encode('utf-8')
        h = mhash.MHASH(mhash.MHASH_TIGER160, s)
        return h.hexdigest()

    @staticmethod
    def hashTiger160bin(s):
        import mhash
        if isinstance(s, str):
            s = s.encode('utf-8')
        h = mhash.MHASH(mhash.MHASH_TIGER160, s)
        return h.digest()

    @staticmethod
    def hashTiger192(s):
        import mhash
        h = mhash.MHASH(mhash.MHASH_TIGER, s)
        return h.hexdigest()

    @staticmethod
    def compress(s):
        import blosc
        return blosc.compress(s, typesize=8)

    @staticmethod
    def decompress(s):
        import blosc
        return blosc.decompress(s)

    @staticmethod
    def disperse(s, nrblocks, extrablocks, compress=True):
        """
        returns DispersedBlock object
        """
        db = DispersedBlock()
        db.create(s, nrblocks, extrablocks, compress)
        return db

    @staticmethod
    def getDispersedBlockObject():
        return DispersedBlock

    @staticmethod
    def undisperse(dispersedBlockObject, uncompress=True):
        dispersedBlockObject.restore


class RegexTool():

    @staticmethod
    def match(pattern, text):
        m = regex.match(pattern, text)
        if m:
            print(("%s %s" % (pattern, text)))
            return True
        else:
            return False

    @staticmethod
    def matchContent(path, contentRegexIncludes=[], contentRegexExcludes=[]):
        content = j.do.fileGetContents(path)
        if RegexTool.matchMultiple(patterns=contentRegexIncludes, text=content) and not RegexTool.matchMultiple(
                patterns=contentRegexExcludes, text=content):
            return True
        return False

    @staticmethod
    def matchMultiple(patterns, text):
        """
        see if any patterns matched
        if patterns=[] then will return False
        """
        if type(patterns).__name__ != 'list':
            raise j.exceptions.RuntimeError("patterns has to be of type list []")
        if patterns == []:
            return True
        for pattern in patterns:
            pattern = RegexTool._patternFix(pattern)
            if RegexTool.match(pattern, text):
                return True
        return False

    @staticmethod
    def matchPath(path, regexIncludes=[], regexExcludes=[]):
        if RegexTool.matchMultiple(patterns=regexIncludes, text=path) and not RegexTool.matchMultiple(
                patterns=regexExcludes, text=path):
            return True
        return False

    @staticmethod
    def _patternFix(pattern):
        if pattern.find("(?m)") == -1:
            pattern = "%s%s" % ("(?m)", pattern)
        return pattern


class FSWalkerStats():

    def __init__(self, do):
        self.do = do
        self.start = do.getTimeEpoch()
        self.stop = 0
        self.sizeUncompressed = {}

        self.sizeCompressed = {}
        self.nr = {}
        self.duplicate = {}

        for i in ["D", "F", "L"]:
            self.registerType(i)

        self.sizeUncompressedTotal = 0
        self.sizeCompressedTotal = 0
        self.nrTotal = 0
        self.duplicateTotal = 0

    def registerType(self, ttype):
        if ttype not in self.sizeUncompressed:
            self.sizeUncompressed[ttype] = 0
        if ttype not in self.sizeCompressed:
            self.sizeCompressed[ttype] = 0
        if ttype not in self.nr:
            self.nr[ttype] = 0
        if ttype not in self.duplicate:
            self.duplicate[ttype] = 0

    def callstop(self):
        self.stop = j.data.time.getTimeEpoch()
        self._getTotals()

    def _getTotals(self):
        sizeUncompressed = 0
        for key in list(self.sizeUncompressed.keys()):
            sizeUncompressed += self.sizeUncompressed[key]
        self.sizeUncompressedTotal = sizeUncompressed

        sizeCompressed = 0
        for key in list(self.sizeCompressed.keys()):
            sizeCompressed += self.sizeCompressed[key]
        self.sizeCompressedTotal = sizeCompressed

        nr = 0
        for key in list(self.nr.keys()):
            nr += self.nr[key]
        self.nrTotal = nr

        duplicate = 0
        for key in list(self.duplicate.keys()):
            duplicate += self.duplicate[key]
        self.duplicateTotal = duplicate

    def add2stat(self, ttype="F", sizeUncompressed=0, sizeCompressed=0, duplicate=False):
        self.sizeUncompressed[ttype] += sizeUncompressed
        self.sizeCompressed[ttype] += sizeCompressed
        self.nr[ttype] += 1
        if duplicate:
            self.duplicate[ttype] += 1

    def __repr__(self):
        self.callstop()
        duration = self.stop - self.start
        # out="nrsecs:%s"%duration
        out = "nrfiles:%s\n" % self.nrTotal
        out += "nrfilesDuplicate:%s\n" % self.duplicateTotal
        sizeUncompressedTotal = (float(self.sizeUncompressedTotal) / 1024 / 1024)
        out += "size uncompressed:%s\n" % sizeUncompressedTotal
        sizeCompressedTotal = (float(self.sizeCompressedTotal) / 1024 / 1024)
        out += "size compressed:%s\n" % sizeCompressedTotal
        out += "uncompressed send per sec in MB/sec: %s\n" % round(sizeUncompressedTotal / duration, 2)
        out += "compressed send per sec in MB/sec: %s\n" % round(sizeCompressedTotal / duration, 2)
        return out

    __str__ = __repr__


class LocalFS():

    def abspath(self, path):
        return os.path.abspath(path)

    def isFile(self, path, followlinks=True):
        return do.isFile(path, followlinks)

    def isDir(self, path, followlinks=True):
        return do.isDir(path, followlinks)

    def isLink(self, path, junction=True):
        return do.isLink(path, junction)

    def stat(self, path):
        return do.stat(path)

    def lstat(self, path):
        return do.lstat(path)

    def list(self, path):
        return do.list(path)


class TIMER:

    @staticmethod
    def start():
        TIMER.clean()
        TIMER._start = time.time()

    @staticmethod
    def stop(nritems=0, log=True):
        TIMER._stop = time.time()
        TIMER.duration = TIMER._stop - TIMER._start
        if nritems > 0:
            TIMER.nritems = float(nritems)
            if TIMER.duration > 0:
                TIMER.performance = float(nritems) / float(TIMER.duration)
        if log:
            TIMER.result()

    @staticmethod
    def clean():
        TIMER._stop = 0.0
        TIMER._start = 0.0
        TIMER.duration = 0.0
        TIMER.performance = 0.0
        TIMER.nritems = 0.0

    @staticmethod
    def result():
        print(("duration:%s" % TIMER.duration))
        print(("nritems:%s" % TIMER.nritems))
        print(("performance:%s" % TIMER.performance))


class FSWalker():

    def __init__(self, do, filesystemobject=None):
        self.do = do
        self.stats = None
        self.statsStart()
        self.statsNr = 0
        self.statsSize = 0
        self.lastPath = ""
        if filesystemobject is None:
            self.fs = LocalFS()
        else:
            self.fs = filesystemobject()

    def statsStart(self):
        self.stats = FSWalkerStats(self.do)

    def statsPrint(self):
        # print("lastpath:%s"%self.lastPath)
        print("\n")
        try:
            print((str(self.stats)))
        except Exception as e:
            pass

    def statsAdd(self, path="", ttype="F", sizeUncompressed=0, sizeCompressed=0, duplicate=False):
        self.stats.add2stat(ttype=ttype, sizeUncompressed=sizeUncompressed,
                            sizeCompressed=sizeCompressed, duplicate=duplicate)
        self.statsNr += 1
        self.statsSize += sizeUncompressed
        self.lastPath = path
        if self.statsNr > 2000 or self.statsSize > 100000000:
            self.statsPrint()
            self.statsNr = 0
            self.statsSize = 0

    def _findhelper(self, arg, path):
        arg.append(path)

    def find(
            self,
            root,
            includeFolders=False,
            includeLinks=False,
            pathRegexIncludes={},
            pathRegexExcludes={},
            followlinks=False,
            childrenRegexExcludes=[
                ".*/log/.*",
                "/dev/.*",
                "/proc/.*"],
            mdserverclient=None):
        """
        @return {files:[],dirs:[],links:[],...$othertypes}
        """

        result = {}
        result["F"] = []
        result["D"] = []
        result["L"] = []

        def processfile(path, stat, arg):
            result["F"].append([path, stat])

        def processdir(path, stat, arg):
            result["D"].append([path, stat])

        def processlink(src, dest, stat, arg):
            result["L"].append([src, dest, stat])

        def processother(path, stat, type, arg):
            if type in result:
                result[type] = []
            result[type].append([path, stat])

        callbackFunctions = {}
        callbackFunctions["F"] = processfile
        callbackFunctions["D"] = processdir
        callbackFunctions["L"] = processlink
        # type O is a generic callback which matches all not specified (will not match F,D,L)
        callbackFunctions["O"] = processother

        callbackMatchFunctions = self.getCallBackMatchFunctions(
            pathRegexIncludes, pathRegexExcludes, includeFolders=includeFolders, includeLinks=includeLinks)

        root = os.path.abspath(root)
        self.walk(
            root,
            callbackFunctions,
            arg={},
            callbackMatchFunctions=callbackMatchFunctions,
            childrenRegexExcludes=childrenRegexExcludes,
            pathRegexIncludes=pathRegexIncludes,
            pathRegexExcludes=pathRegexExcludes,
            mdserverclient=mdserverclient)

        return result

    def getCallBackMatchFunctions(self, pathRegexIncludes={}, pathRegexExcludes={},
                                  includeFolders=True, includeLinks=True):

        C = """
if pathRegexIncludes.has_key("$type") and not pathRegexExcludes.has_key("$type"):
    def matchobj$type(path,arg,pathRegexIncludes,pathRegexExcludes):
        return RegexTool.matchPath(path,pathRegexIncludes["$type"],[])
elif not pathRegexIncludes.has_key("$type") and pathRegexExcludes.has_key("$type"):
    def matchobj$type(path,arg,pathRegexIncludes,pathRegexExcludes):
        return RegexTool.matchPath(path,[],pathRegexExcludes["$type"])
elif pathRegexIncludes.has_key("$type") and pathRegexExcludes.has_key("$type"):
    def matchobj$type(path,arg,pathRegexIncludes,pathRegexExcludes):
        return RegexTool.matchPath(path,pathRegexIncludes["$type"],pathRegexExcludes["$type"])
else:
    matchobj$type=None
"""
        for ttype in ["F", "D", "L"]:
            C2 = C.replace("$type", ttype)
            exec(C2)

        callbackMatchFunctions = {}
        if matchobjF is not None and ("F" in pathRegexIncludes or "F" in pathRegexExcludes):
            callbackMatchFunctions["F"] = matchobjF
        if includeFolders:
            if matchobjD is not None and ("D" in pathRegexIncludes or "D" in pathRegexExcludes):
                callbackMatchFunctions["D"] = matchobjD
        if includeLinks:
            if matchobjL is not None and ("L" in pathRegexIncludes or "L" in pathRegexExcludes):
                callbackMatchFunctions["L"] = matchobjL
        if "O" in pathRegexIncludes or "O" in pathRegexExcludes:
            callbackMatchFunctions["O"] = matchobjO

        return callbackMatchFunctions

    def walk(self, root, callbackFunctions={}, arg=None, callbackMatchFunctions={}, followlinks=False,
             childrenRegexExcludes=["/dev/.*", "/proc/.*", "/cdrom/.*", "/mnt/.*", "/media/.*", "/run/.*", "/tmp/.*"],
             pathRegexIncludes={}, pathRegexExcludes={}, mdserverclient=None, stat=False):
        '''

        Walk through filesystem and execute a method per file and dirname if the match function selected the item

        Walk through all files and folders and other objects starting at root,
        recursive by default, calling a given callback with a provided argument and file
        path for every file & dir we could find.

        To match the function use the callbackMatchFunctions  which are separate for all types of objects (Dir=D, File=F, Link=L)
        when it returns True the path will be further processed

        Examples
        ========
        >>> def my_print(path,arg):
        ...     print arg+path
        ...

        >>> def match(path,arg):
        ...     return True #means will process the object e.g. file which means call my_print in this example
        ...

        >>> self.walk('/foo', my_print,arg="Test: ", callbackMatchFunctions=match)
        test: /foo/file1
        test: /foo/file2
        test: /foo/file3
        test: /foo/bar/file4

        @param root: Filesystem root to crawl (string)

        '''
        # We want to work with full paths, even if a non-absolute path is provided
        root = os.path.abspath(root)
        if not self.fs.isDir(root):
            raise ValueError('Root path for walk should be a folder, now path:%s' % root)

        # print "ROOT OF WALKER:%s"%root
        if mdserverclient is None:
            self._walkFunctional(
                root,
                callbackFunctions,
                arg,
                callbackMatchFunctions,
                followlinks,
                childrenRegexExcludes=childrenRegexExcludes,
                pathRegexIncludes=pathRegexIncludes,
                pathRegexExcludes=pathRegexExcludes,
                stat=stat)
        else:
            self._walkFunctionalMDS(
                root,
                callbackFunctions,
                arg,
                callbackMatchFunctions,
                followlinks,
                childrenRegexExcludes=childrenRegexExcludes,
                pathRegexIncludes=pathRegexIncludes,
                pathRegexExcludes=pathRegexExcludes,
                stat=stat)

    def _walkFunctional(self, root, callbackFunctions={}, arg=None, callbackMatchFunctions={}, followlinks=False,
                        childrenRegexExcludes=[], pathRegexIncludes={}, pathRegexExcludes={}, stat=False):

        statb = None
        stat = None

        paths = self.fs.list(root)
        for path2 in paths:
            path2 = path2.replace("//", "/")
            # self.logger.info("walker path:%s"% path2)
            if self.fs.isLink(path2):
                # print "LINK:%s"%path2
                ttype = "L"
            elif self.fs.isFile(path2):
                ttype = "F"
            elif self.fs.isDir(path2, followlinks):
                ttype = "D"
            else:
                raise j.exceptions.RuntimeError("Can only detect files, dirs, links,path was '%s'" % path2)

            if ttype not in callbackMatchFunctions or (ttype in callbackMatchFunctions and callbackMatchFunctions[
                                                       ttype](path2, arg, pathRegexIncludes, pathRegexExcludes)):
                # self.logger.info("walker filepath:%s"% path2)
                self.statsAdd(path=path2, ttype=ttype, sizeUncompressed=0, sizeCompressed=0, duplicate=False)

                if ttype in callbackFunctions:
                    if ttype in "DF":
                        if stat:
                            stat = self.fs.stat(path2)
                            statb = struct.pack("<IHHII", stat.st_mode, stat.st_gid,
                                                stat.st_uid, stat.st_size, stat.st_mtime)
                        callbackFunctions[ttype](path=path2, stat=statb, arg=arg)
                    else:
                        if stat:
                            stat = self.fs.lstat(path2)
                            statb = struct.pack("<IHHII", stat.st_mode, stat.st_gid,
                                                stat.st_uid, stat.st_size, stat.st_mtime)
                        callbackFunctions[ttype](src=path2, dest=os.path.realpath(path2), arg=arg, stat=statb)

            if ttype == "D":
                if path2[-1] != "/":
                    path2 += "/"

                if pathRegexIncludes.get(ttype, []) == [] and childrenRegexExcludes == []:
                    self._walkFunctional(
                        path2,
                        callbackFunctions,
                        arg,
                        callbackMatchFunctions,
                        followlinks,
                        childrenRegexExcludes=childrenRegexExcludes,
                        pathRegexIncludes=pathRegexIncludes,
                        pathRegexExcludes=pathRegexExcludes)

                elif RegexTool.matchPath(path2, pathRegexIncludes.get(ttype, []), childrenRegexExcludes):
                    self._walkFunctional(
                        path2,
                        callbackFunctions,
                        arg,
                        callbackMatchFunctions,
                        followlinks,
                        childrenRegexExcludes=childrenRegexExcludes,
                        pathRegexIncludes=pathRegexIncludes,
                        pathRegexExcludes=pathRegexExcludes)


class extra():

    def __init__(self):
        pass

    def getWalker(self, do):
        return FSWalker(do)

        # self.RegexTool=RegexTool
        # self.ByteProcessor=ByteProcessor


extra = extra()
