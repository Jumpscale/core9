import os
from JumpScale9 import j


# def embed():
#     return "embed" in sys.__dict__
#
#
# def pathToUnicode(path):
#     """
#     Convert path to unicode. Use the local filesystem encoding. Will return
#     path unmodified if path already is unicode.
#
#     @param path: path to convert to unicode
#     @type path: basestring
#     @return: unicode path
#     @rtype: unicode
#     """
#     if isinstance(path, str):
#         return path
#
#     return path.decode(sys.getfilesystemencoding())


class Dirs:
    """Utility class to configure and store all relevant directory paths"""

    def __init__(self):
        '''jumpscale sandbox base folder'''
        self.__jslocation__ = "j.core.dirs"
        self.reload()

    def reload(self):

        for key, val in j.core.state.config["dirs"].items():
            self.__dict__[key] = val

    def replaceTxtDirVars(self, txt, additionalArgs={}):
        """
        replace $BASEDIR,$VARDIR,$JSCFGDIR,$bindir,$codedir,$tmpdir,$logdir,$appdir with props of this class
        also the Dir... get replaces e.g. varDir
        """

        for key, val in os.environ.items():
            if "DIR" in key:
                txt = txt.replace("$%s" % key, val)

        # for backwardscompatibility
        txt = txt.replace("$APPDIR", self.JSAPPSDIR)
        txt = txt.replace("$TMPLSDIR", self.TEMPLATEDIR)
        txt = txt.replace("$CODEDIR", self.CODEDIR)
        txt = txt.replace("$VARDIR", self.VARDIR)
        txt = txt.replace("$CFGDIR", self.CFGDIR)
        txt = txt.replace("$BINDIR", self.BINDIR)
        txt = txt.replace("$LOGDIR", self.LOGDIR)
        txt = txt.replace("$TMPDIR", self.TMPDIR)
        txt = txt.replace("$LIBDIR", self.JSLIBDIR)
        # txt = txt.replace("$jslibextdir", self.JSLIBEXTDIR)
        # txt = txt.replace("$jsbindir", self.BINDIR)
        txt = txt.replace("$nodeid", str(j.application.whoAmI.nid))
        for key, value in list(additionalArgs.items()):
            txt = txt.replace("$%s" % key, str(value))
        return txt

    @property
    def JSLIBDIR(self):
        return j.do.getParent(
            j.do.getDirName(
                j.do.getPathOfRunningFunction(
                    j.logger.__init__)))

    def replaceFilesDirVars(
            self,
            path,
            recursive=True,
            filter=None,
            additionalArgs={}):
        if j.do.isFile(path):
            paths = [path]
        else:
            paths = j.do.listFilesInDir(path, recursive, filter)

        for path in paths:
            content = j.do.fileGetContents(path)
            content2 = self.replaceTxtDirVars(content, additionalArgs)
            if content2 != content:
                j.do.writeFile(filename=path, contents=content2)

    # def _getParent(self, path):
    #     """
    #     Returns the parent of the path:
    #     /dir1/dir2/file_or_dir -> /dir1/dir2/
    #     /dir1/dir2/            -> /dir1/
    #     TODO: why do we have 2 implementations which are almost the same see getParentDirName()
    #     """
    #     parts = path.split(os.sep)
    #     if parts[-1] == '':
    #         parts = parts[:-1]
    #     parts = parts[:-1]
    #     if parts == ['']:
    #         return os.sep
    #     return os.sep.join(parts)
    #
    # def _getLibPath(self):
    #     parent = self._getParent
    #     libDir = parent(parent(__file__))
    #     libDir = os.path.abspath(libDir).rstrip("/")
    #     return libDir

    def __str__(self):
        out = ""
        for key, value in self.__dict__.items():
            if key[0] == "_":
                continue
            out += "%-20s : %s\n" % (key, value)
        out = j.data.text.sort(out)
        return out

    __repr__ = __str__
