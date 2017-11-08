from JumpScale9 import j

import sys

from urllib.request import urlopen

import os
import tarfile
import shutil
import platform
import subprocess
import time
import pystache
import pytoml
import fnmatch
import re
import importlib


class TimeoutError(RuntimeError, TimeoutError):
    pass


class FSMethods():

    def getPythonLibSystem(self, jumpscale=False):
        PYTHONVERSION = platform.python_version()
        if j.core.platformtype.myplatform.isMac:
            destjs = "/usr/local/lib/python3.6/site-packages"
        elif j.core.platformtype.myplatform.isWindows:
            destjs = "/usr/lib/python3.4/site-packages"
        else:
            if PYTHONVERSION == '2':
                destjs = "/usr/local/lib/python/dist-packages"
            else:
                destjs = "/usr/local/lib/python3.5/dist-packages"

        if jumpscale:
            destjs += "/JumpScale/"

        self.createDir(destjs)
        return destjs

    def readFile(self, filename):
        """Read a file and get contents of that file
        @param filename: string (filename to open for reading )
        @rtype: string representing the file contents
        """
        filename = self.home_expand(filename)
        with open(filename) as fp:
            data = fp.read()
        return data

    def touch(self, path):
        path = self.home_expand(path)
        self.writeFile(path, "")

    textstrip = j.data.text.strip

    def writeFile(self, path, content, strip=True):
        path = self.home_expand(path)
        self.createDir(self.getDirName(path))

        if strip:
            content = self.textstrip(content, True)

        with open(path, "w") as fo:
            fo.write(content)

    def delete(self, path, force=False):
        path = self.home_expand(path)

        self.removeSymlink(path)

        if path.strip().rstrip("/") in ["",
                                        "/",
                                        "/etc",
                                        "/root",
                                        "/usr",
                                        "/opt",
                                        "/usr/bin",
                                        "/usr/sbin",
                                        "/opt/code"]:
            raise RuntimeError('cannot delete protected dirs')

        # if not force and path.find(j.CODEDIR)!=-1:
        #     raise RuntimeError('cannot delete protected dirs')

        if self.debug:
            self.logger.info(("delete: %s" % path))
        if os.path.exists(path) or os.path.islink(path):
            if os.path.isdir(path):
                # print "delete dir %s" % path
                if os.path.islink(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)
            else:
                # print "delete file %s" % path
                os.remove(path)

    def joinPaths(self, *args):
        if len(args) > 0:
            args = list(args)
            args[0] = self.home_expand(args[0])
        return os.path.join(*args)

    def copyTree(
            self,
            source,
            dest,
            keepsymlinks=False,
            deletefirst=False,
            overwriteFiles=True,
            ignoredir=[
                "*.egg-info",
                "*.dist-info"],
            ignorefiles=["*.egg-info"],
            rsync=True,
            ssh=False,
            sshport=22,
            recursive=True,
            rsyncdelete=False,
            createdir=False,
            executor=None):
        """
        if ssh format of source or dest is: remoteuser@remotehost:/remote/dir
        """
        if self.debug:
            self.logger.info(("copy %s %s" % (source, dest)))
        if not ssh and not self.exists(source, executor=executor):
            raise RuntimeError("copytree:Cannot find source:%s" % source)

        if executor and not rsync:
            raise RuntimeError("when executor used only rsync supported")
        if rsync:
            excl = ""
            for item in ignoredir:
                excl += "--exclude '%s/' " % item
            for item in ignorefiles:
                excl += "--exclude '%s' " % item
            excl += "--exclude '*.pyc' "
            excl += "--exclude '*.bak' "
            excl += "--exclude '*__pycache__*' "

            pre = ""
            if executor is None:
                if self.isDir(source):
                    if dest[-1] != "/":
                        dest += "/"
                    if source[-1] != "/":
                        source += "/"
                    # if ssh:
                    #     pass
                    #     # if dest.find(":")!=-1:
                    #     #     if dest.find("@")!=-1:
                    #     #         desthost=dest.split(":")[0].split("@", 1)[1].strip()
                    #     #     else:
                    #     #         desthost=dest.split(":")[0].strip()
                    #     #     dir_dest=dest.split(":",1)[1]
                    #     #     cmd="ssh -o StrictHostKeyChecking=no -p %s  %s 'mkdir -p %s'" % (sshport,sshport,dir_dest)
                    #     #     print cmd
                    #     #     self.executeInteractive(cmd)
                    # else:
                    #     self.createDir(dest)
                if dest.find(':') == -1:  # download
                    # self.createDir(self.getParent(dest))
                    dest = dest.split(':')[1] if ':' in dest else dest
            else:
                if not sys.platform.startswith("darwin"):
                    executor.prefab.package.ensure('rsync')
                if executor.prefab.core.dir_exists(source):
                    if dest[-1] != "/":
                        dest += "/"
                    if source[-1] != "/":
                        source += "/"

            dest = dest.replace("//", "/")
            source = source.replace("//", "/")

            if deletefirst:
                pre = "set -ex;rm -rf %s;mkdir -p %s;" % (dest, dest)
            elif createdir:
                pre = "set -ex;mkdir -p %s;" % dest

            cmd = "%srsync " % pre
            if keepsymlinks:
                #-l is keep symlinks, -L follow
                cmd += " -rlptgo --partial %s" % excl
            else:
                cmd += " -rLptgo --partial %s" % excl
            if not recursive:
                cmd += " --exclude \"*/\""
            # if self.debug:
            #     cmd += ' --progress'
            if rsyncdelete:
                cmd += " --delete"
            if ssh:
                cmd += " -e 'ssh -o StrictHostKeyChecking=no -p %s' " % sshport
            cmd += " '%s' '%s'" % (source, dest)
            # self.logger.info(cmd)
            if executor is not None:
                rc, out, err = executor.execute(cmd, showout=False)
            else:
                rc, out, err = self.execute(cmd, showout=False, outputStderr=False)
            # print(rc)
            # print(out)
            return
        else:
            old_debug = self.debug
            self.debug = False
            self._copyTree(
                source,
                dest,
                keepsymlinks,
                deletefirst,
                overwriteFiles,
                ignoredir=ignoredir,
                ignorefiles=ignorefiles)
            self.debug = old_debug

    def _copyTree(
            self,
            src,
            dst,
            keepsymlinks=False,
            deletefirst=False,
            overwriteFiles=True,
            ignoredir=[
                ".egg-info",
                "__pycache__"],
            ignorefiles=[".egg-info"]):
        """Recursively copy an entire directory tree rooted at src.
        The dst directory may already exist; if not,
        it will be created as well as missing parent directories
        @param src: string (source of directory tree to be copied)
        @param dst: string (path directory to be copied to...should not already exist)
        @param keepsymlinks: bool (True keeps symlinks instead of copying the content of the file)
        @param deletefirst: bool (Set to True if you want to erase destination first, be carefull, this can erase directories)
        @param overwriteFiles: if True will overwrite files, otherwise will not overwrite when destination exists
        """

        self.logger.info('Copy directory tree from %s to %s' % (src, dst), 6)
        if ((src is None) or (dst is None)):
            raise TypeError(
                'Not enough parameters passed in system.fs.copyTree to copy directory from %s to %s ' %
                (src, dst))
        if self.isDir(src):
            if ignoredir != []:
                for item in ignoredir:
                    if src.find(item) != -1:
                        return
            names = os.listdir(src)

            if not self.exists(dst):
                self.createDir(dst)

            errors = []
            for name in names:
                # is only for the name
                name2 = name

                srcname = self.joinPaths(src, name)
                dstname = self.joinPaths(dst, name2)
                if deletefirst and self.exists(dstname):
                    if self.isDir(dstname, False):
                        self.removeDirTree(dstname)
                    if self.isLink(dstname):
                        self.unlink(dstname)

                if keepsymlinks and self.isLink(srcname):
                    linkto = self.readLink(srcname)
                    # self.symlink(linkto, dstname)#, overwriteFiles)
                    try:
                        os.symlink(linkto, dstname)
                    except BaseException:
                        pass
                        # TODO: very ugly change
                elif self.isDir(srcname):
                    # print "1:%s %s"%(srcname,dstname)
                    self.copyTree(
                        srcname,
                        dstname,
                        keepsymlinks,
                        deletefirst,
                        overwriteFiles=overwriteFiles,
                        ignoredir=ignoredir)
                else:
                    # print "2:%s %s"%(srcname,dstname)
                    extt = self.getFileExtension(srcname)
                    if extt == "pyc" or extt == "egg-info":
                        continue
                    if ignorefiles != []:
                        for item in ignorefiles:
                            if srcname.find(item) != -1:
                                continue
                    self.copyFile(srcname, dstname, deletefirst=overwriteFiles)
        else:
            raise RuntimeError(
                'Source path %s in system.fs.copyTree is not a directory' %
                src)

    def copyFile(self, source, dest, deletefirst=False, skipIfExists=False, makeExecutable=False):
        source = self.home_expand(source)
        dest = self.home_expand(dest)
        if self.isDir(dest):
            dest = self.joinPaths(dest, self.getBaseName(source))

        if skipIfExists:
            if self.exists(dest):
                return

        if deletefirst:
            self.delete(dest)
        if self.debug:
            self.logger.info(("copy %s %s" % (source, dest)))

        shutil.copy(source, dest)

        if makeExecutable:
            self.chmod(dest, 0o770)

    def createDir(self, path):
        path = self.home_expand(path) 
        if not os.path.exists(path) and not os.path.islink(path):
            os.makedirs(path)


    def isDir(self, path, followSoftlink=False):
        """Check if the specified Directory path exists
        @param path: string
        @param followSoftlink: boolean
        @rtype: boolean (True if directory exists)
        """
        path = self.home_expand(path) 
        if self.isLink(path):
            if not followSoftlink:
                return False
            else:
                link = self.readLink(path)
                return self.isDir(link)
        else:
            return os.path.isdir(path)

    def isFile(self, path, followSoftlink=False):
        """Check if the specified file exists for the given path
        @param path: string
        @param followSoftlink: boolean
        @rtype: boolean (True if file exists for the given path)
        """
        path = self.home_expand(path) 
        if self.isLink(path):
            if not followSoftlink:
                return False
            else:
                link = self.readLink(path)
                return self.isFile(link)
        else:
            return os.path.isfile(path)

    def isLink(self, path, checkJunction=False):
        """Check if the specified path is a link
        @param path: string
        @rtype: boolean (True if the specified path is a link)
        """
        path = self.home_expand(path) 
        if path[-1] == os.sep:
            path = path[:-1]
        if (path is None):
            raise TypeError('Link path is None in system.fs.isLink')

        if checkJunction and j.core.platformtype.myplatform.isWindows:
            cmd = "junction %s" % path
            try:
                rc, result, err = self.execute(cmd)
            except Exception as e:
                raise RuntimeError(
                    "Could not execute junction cmd, is junction installed? Cmd was %s." %
                    cmd)
            if rc != 0:
                raise RuntimeError(
                    "Could not execute junction cmd, is junction installed? Cmd was %s." %
                    cmd)
            if result.lower().find("substitute name") != -1:
                return True
            else:
                return False

        if(os.path.islink(path)):
            # self.logger.info('path %s is a link'%path,8)
            return True
        # self.logger.info('path %s is not a link'%path,8)
        return False

    def list(self, path):
        path = self.home_expand(path) 
        # self.logger.info("list:%s"%path)
        if(self.isDir(path)):
            s = sorted(["%s/%s" % (path, item) for item in os.listdir(path)])
            return s
        elif(self.isLink(path)):
            link = self.readLink(path)
            return self.list(link)
        else:
            raise ValueError(
                "Specified path: %s is not a Directory in self.listDir" %
                path)

    def exists(self, path, executor=None):
        path = self.home_expand(path) 
        if executor:
            return executor.exists(path)
        else:
            return os.path.exists(path)

    def pip(self, items, force=False, executor=None):
        """
        @param items is string or list
        """
        if isinstance(items, list):
            pass
        elif isinstance(items, str):
            items = self.textstrip(items)
            items = [item.strip()
                     for item in items.split("\n") if item.strip() != ""]
        else:
            raise RuntimeError("input can only be string or list")

        for item in items:
            cmd = "pip3 install %s --upgrade" % item
            if executor is None:
                self.executeInteractive(cmd)
            else:
                executor.execute(cmd)

    def symlink(self, src, dest, delete=False):
        """
        dest is where the link will be created pointing to src
        """
        src = self.home_expand(src) 
        dest = self.home_expand(dest) 
        if self.debug:
            self.logger.info(("symlink: src:%s dest(islink):%s" % (src, dest)))

        if self.isLink(dest):
            self.removeSymlink(dest)

        if delete:
            if j.core.platformtype.myplatform.isWindows:
                self.removeSymlink(dest)
                self.delete(dest)
            else:
                self.delete(dest)

        if j.core.platformtype.myplatform.isWindows:
            cmd = "junction %s %s 2>&1 > null" % (dest, src)
            os.system(cmd)
            # raise RuntimeError("not supported on windows yet")
        else:
            dest = dest.rstrip("/")
            src = src.rstrip("/")
            if not self.exists(src):
                raise RuntimeError("could not find src for link:%s" % src)
            if not self.exists(dest):
                os.symlink(src, dest)

    def symlinkFilesInDir(self, src, dest, delete=True, includeDirs=False, makeExecutable=False):
        src = self.home_expand(src) 
        dest = self.home_expand(dest) 
        if includeDirs:
            items = self.listFilesAndDirsInDir(
                src, recursive=False, followSymlinks=False, listSymlinks=False)
        else:
            items = self.listFilesInDir(
                src,
                recursive=False,
                followSymlinks=True,
                listSymlinks=True)
        for item in items:
            dest2 = "%s/%s" % (dest, self.getBaseName(item))
            dest2 = dest2.replace("//", "/")
            self.logger.info(("link %s:%s" % (item, dest2)))
            self.symlink(item, dest2, delete=delete)
            if makeExecutable:
                # print("executable:%s" % dest2)
                self.chmod(dest2, 0o770)
                self.chmod(item, 0o770)

    def removeSymlink(self, path):
        path = self.home_expand(path) 
        if j.core.platformtype.myplatform.isWindows:
            try:
                cmd = "junction -d %s 2>&1 > null" % (path)
                self.logger.info(cmd)
                os.system(cmd)
            except Exception as e:
                pass
        else:
            if self.isLink(path):
                os.unlink(path.rstrip("/"))

    def getBaseName(self, path):
        """Return the base name of pathname path."""
        # self.logger.info('Get basename for path: %s'%path,9)
        if path is None:
            raise TypeError('Path is not passed in system.fs.getDirName')
        path = self.home_expand(path) 
        try:
            return os.path.basename(path.rstrip(os.path.sep))
        except Exception as e:
            raise RuntimeError(
                'Failed to get base name of the given path: %s, Error: %s' %
                (path, str(e)))

    def checkDirOrLinkToDir(self, fullpath):
        """
        check if path is dir or link to a dir
        """
        if fullpath is None or fullpath.strip == "":
            raise RuntimeError("path cannot be empty")

        fullpath = self.home_expand(fullpath) 
        if not self.isLink(fullpath) and os.path.isdir(fullpath):
            return True
        if self.isLink(fullpath):
            link = self.readLink(fullpath)
            if self.isDir(link):
                return True
        return False

    def getDirName(self, path, lastOnly=False, levelsUp=None):
        """
        Return a directory name from pathname path.
        @param path the path to find a directory within
        @param lastOnly means only the last part of the path which is a dir (overrides levelsUp to 0)
        @param levelsUp means, return the parent dir levelsUp levels up
         e.g. ...getDirName("/opt/qbase/bin/something/test.py", levelsUp=0) would return something
         e.g. ...getDirName("/opt/qbase/bin/something/test.py", levelsUp=1) would return bin
         e.g. ...getDirName("/opt/qbase/bin/something/test.py", levelsUp=10) would raise an error
        """
        # self.logger.info('Get directory name of path: %s' % path,9)
        if path is None:
            raise TypeError('Path is not passed in system.fs.getDirName')
        path = self.home_epand(path)
        dname = os.path.dirname(path)
        dname = dname.replace("/", os.sep)
        dname = dname.replace("//", os.sep)
        dname = dname.replace("\\", os.sep)
        if lastOnly:
            dname = dname.split(os.sep)[-1]
            return dname
        if levelsUp is not None:
            parts = dname.split(os.sep)
            if len(parts) - levelsUp > 0:
                return parts[len(parts) - levelsUp - 1]
            else:
                raise RuntimeError(
                    "Cannot find part of dir %s levels up, path %s is not long enough" %
                    (levelsUp, path))
        return dname + os.sep

    def readLink(self, path):
        """Works only for unix
        Return a string representing the path to which the symbolic link points.
        """
        path = self.home_expand(path) 
        while path[-1] == "/" or path[-1] == "\\":
            path = path[:-1]
        # self.logger.info('Read link with path: %s'%path,8)
        if path is None:
            raise TypeError('Path is not passed in system.fs.readLink')
        if j.core.platformtype.myplatform.isWindows:
            raise RuntimeError('Cannot readLink on windows')
        try:
            return os.readlink(path)
        except Exception as e:
            raise RuntimeError(
                'Failed to read link with path: %s \nERROR: %s' %
                (path, str(e)))


    def _listInDir(self, path, followSymlinks=True):
        """returns array with dirs & files in directory
        @param path: string (Directory path to list contents under)
        """
        if path is None:
            raise TypeError('Path is not passed in system.fs.listDir')
        path = self.home_expand(path) 
        if(self.exists(path)):
            if(self.isDir(path)) or (followSymlinks and self.checkDirOrLinkToDir(path)):
                names = os.listdir(path)
                return names
            else:
                raise ValueError(
                    "Specified path: %s is not a Directory in system.fs.listDir" %
                    path)
        else:
            raise RuntimeError(
                "Specified path: %s does not exist in system.fs.listDir" %
                path)

    def listDirsInDir(
            self,
            path,
            recursive=False,
            dirNameOnly=False,
            findDirectorySymlinks=True):
        """ Retrieves list of directories found in the specified directory
        @param path: string represents directory path to search in
        @rtype: list
        """
        # self.logger.info('List directories in directory with path: %s, recursive = %s' % (path, str(recursive)),9)

        # if recursive:
        # if not self.exists(path):
        # raise ValueError('Specified path: %s does not exist' % path)
        # if not self.isDir(path):
        # raise ValueError('Specified path: %s is not a directory' % path)
        # result = []
        # os.path.walk(path, lambda a, d, f: a.append('%s%s' % (d, os.path.sep)), result)
        # return result
        if path is None or path.strip == "":
            raise RuntimeError("path cannot be empty")
        path = self.home_expand(path) 
        files = self._listInDir(path, followSymlinks=True)
        filesreturn = []
        for file in files:
            fullpath = os.path.join(path, file)
            if (findDirectorySymlinks and self.checkDirOrLinkToDir(
                    fullpath)) or self.isDir(fullpath):
                if dirNameOnly:
                    filesreturn.append(file)
                else:
                    filesreturn.append(fullpath)
                if recursive:
                    filesreturn.extend(
                        self.listDirsInDir(
                            fullpath,
                            recursive,
                            dirNameOnly,
                            findDirectorySymlinks))
        return filesreturn

    def listFilesInDir(
            self,
            path,
            recursive=False,
            filter=None,
            minmtime=None,
            maxmtime=None,
            depth=None,
            case_sensitivity='os',
            exclude=[],
            followSymlinks=True,
            listSymlinks=False):
        """Retrieves list of files found in the specified directory
        @param path:       directory path to search in
        @type  path:       string
        @param recursive:  recursively look in all subdirs
        @type  recursive:  boolean
        @param filter:     unix-style wildcard (e.g. *.py) - this is not a regular expression
        @type  filter:     string
        @param minmtime:   if not None, only return files whose last modification time > minmtime (epoch in seconds)
        @type  minmtime:   integer
        @param maxmtime:   if not None, only return files whose last modification time < maxmtime (epoch in seconds)
        @Param depth: is levels deep wich we need to go
        @type  maxmtime:   integer
        @Param exclude: list of std filters if matches then exclude
        @rtype: list
        """
        path = self.home_expand(path) 
        if depth is not None:
            depth = int(depth)
        # self.logger.info('List files in directory with path: %s' % path,9)
        if depth == 0:
            depth = None
        # if depth is not None:
        #     depth+=1
        filesreturn, depth = self._listAllInDir(path, recursive, filter, minmtime, maxmtime, depth, type="f",
                                                case_sensitivity=case_sensitivity, exclude=exclude, followSymlinks=followSymlinks, listSymlinks=listSymlinks)
        return filesreturn

    def listFilesAndDirsInDir(
            self,
            path,
            recursive=False,
            filter=None,
            minmtime=None,
            maxmtime=None,
            depth=None,
            type="fd",
            followSymlinks=True,
            listSymlinks=False):
        """Retrieves list of files found in the specified directory
        @param path:       directory path to search in
        @type  path:       string
        @param recursive:  recursively look in all subdirs
        @type  recursive:  boolean
        @param filter:     unix-style wildcard (e.g. *.py) - this is not a regular expression
        @type  filter:     string
        @param minmtime:   if not None, only return files whose last modification time > minmtime (epoch in seconds)
        @type  minmtime:   integer
        @param maxmtime:   if not None, only return files whose last modification time < maxmtime (epoch in seconds)
        @Param depth: is levels deep wich we need to go
        @type  maxmtime:   integer
        @param type is string with f & d inside (f for when to find files, d for when to find dirs)
        @rtype: list
        """
        path = self.home_expand(path) 
        if depth is not None:
            depth = int(depth)
        self.logger.info('List files in directory with path: %s' % path, 9)
        if depth == 0:
            depth = None
        # if depth is not None:
        #     depth+=1
        filesreturn, depth = self._listAllInDir(
            path, recursive, filter, minmtime, maxmtime, depth, type=type, followSymlinks=followSymlinks, listSymlinks=listSymlinks)
        return filesreturn

    def _listAllInDir(
            self,
            path,
            recursive,
            filter=None,
            minmtime=None,
            maxmtime=None,
            depth=None,
            type="df",
            case_sensitivity='os',
            exclude=[],
            followSymlinks=True,
            listSymlinks=True):
        """
        # There are 3 possible options for case-sensitivity for file names
        # 1. `os`: the same behavior as the OS
        # 2. `sensitive`: case-sensitive comparison
        # 3. `insensitive`: case-insensitive comparison
        """
        path = self.home_expand(path) 

        dircontent = self._listInDir(path)
        filesreturn = []

        if case_sensitivity.lower() == 'sensitive':
            matcher = fnmatch.fnmatchcase
        elif case_sensitivity.lower() == 'insensitive':
            def matcher(fname, pattern):
                return fnmatch.fnmatchcase(fname.lower(), pattern.lower())
        else:
            matcher = fnmatch.fnmatch

        for direntry in dircontent:
            fullpath = self.joinPaths(path, direntry)

            if followSymlinks:
                if self.isLink(fullpath):
                    fullpath = self.readLink(fullpath)

            if self.isFile(fullpath) and "f" in type:
                includeFile = False
                if (filter is None) or matcher(direntry, filter):
                    if (minmtime is not None) or (maxmtime is not None):
                        mymtime = os.stat(fullpath)[ST_MTIME]
                        if (minmtime is None) or (mymtime > minmtime):
                            if (maxmtime is None) or (mymtime < maxmtime):
                                includeFile = True
                    else:
                        includeFile = True
                if includeFile:
                    if exclude != []:
                        for excludeItem in exclude:
                            if matcher(direntry, excludeItem):
                                includeFile = False
                    if includeFile:
                        filesreturn.append(fullpath)
            elif self.isDir(fullpath):
                if "d" in type:
                    if not(listSymlinks is False and self.isLink(fullpath)):
                        filesreturn.append(fullpath)
                if recursive:
                    if depth is not None and depth != 0:
                        depth = depth - 1
                    if depth is None or depth != 0:
                        exclmatch = False
                        if exclude != []:
                            for excludeItem in exclude:
                                if matcher(fullpath, excludeItem):
                                    exclmatch = True
                        if exclmatch is False:
                            if not(
                                    followSymlinks is False and self.isLink(fullpath)):
                                r, depth = self._listAllInDir(fullpath, recursive, filter, minmtime, maxmtime, depth=depth,
                                                              type=type, exclude=exclude, followSymlinks=followSymlinks, listSymlinks=listSymlinks)
                                if len(r) > 0:
                                    filesreturn.extend(r)
            elif self.isLink(fullpath) and followSymlinks is False and listSymlinks:
                filesreturn.append(fullpath)

        return filesreturn, depth



    # def expandTarGz(
    #         self,
    #         path,
    #         destdir,
    #         deleteDestFirst=True,
    #         deleteSourceAfter=False):
    #     import gzip

    #     self.lastdir = os.getcwd()
    #     os.chdir('/tmp')
    #     basename = os.path.basename(path)
    #     if basename.find(".tar.gz") == -1:
    #         raise RuntimeError("Can only expand a tar gz file now %s" % path)
    #     tarfilename = ".".join(basename.split(".gz")[:-1])
    #     self.delete(tarfilename)

    #     if deleteDestFirst:
    #         self.delete(destdir)

    #     if j.core.platformtype.myplatform.isWindows:
    #         cmd = "gzip -d %s" % path
    #         os.system(cmd)
    #     else:
    #         handle = gzip.open(path)
    #         with open(tarfilename, 'wb') as out:
    #             for line in handle:
    #                 out.write(line)
    #         out.close()
    #         handle.close()

    #     t = tarfile.open(tarfilename, 'r')
    #     t.extractall(destdir)
    #     t.close()

    #     self.delete(tarfilename)

    #     if deleteSourceAfter:
    #         self.delete(path)

    #     os.chdir(self.lastdir)
    #     self.lastdir = ""

    def getParent(self, path):
        """
        Returns the parent of the path:
        /dir1/dir2/file_or_dir -> /dir1/dir2/
        /dir1/dir2/            -> /dir1/
        TODO: why do we have 2 implementations which are almost the same see getParentDirName()
        """
        path = self.home_expand(path) 
        parts = path.split(os.sep)
        if parts[-1] == '':
            parts = parts[:-1]
        parts = parts[:-1]
        if parts == ['']:
            return os.sep
        return os.sep.join(parts)

    def getFileExtension(self, path):
        path = self.home_expand(path) 
        extcand = path.split(".")
        if len(extcand) > 0:
            ext = extcand[-1]
        else:
            ext = ""
        return ext

    def chown(self, path, user):

        from pwd import getpwnam
        path = self.home_expand(path) 

        getpwnam(user)[2]
        uid = getpwnam(user).pw_uid
        gid = getpwnam(user).pw_gid
        os.chown(path, uid, gid)
        for root, dirs, files in os.walk(path):
            for ddir in dirs:
                path = os.path.join(root, ddir)
                try:
                    os.chown(path, uid, gid)
                except Exception as e:
                    if str(e).find("No such file or directory") == -1:
                        raise RuntimeError("%s" % e)
            for file in files:
                path = os.path.join(root, file)
                try:
                    os.chown(path, uid, gid)
                except Exception as e:
                    if str(e).find("No such file or directory") == -1:
                        raise RuntimeError("%s" % e)

    def chmod(self, path, permissions):
        """
        @param permissions e.g. 0o660 (USE OCTAL !!!)
        """
        path = self.home_expand(path)
        os.chmod(path, permissions)
        for root, dirs, files in os.walk(path):
            for ddir in dirs:
                path = os.path.join(root, ddir)
                try:
                    os.chmod(path, permissions)
                except Exception as e:
                    if str(e).find("No such file or directory") == -1:
                        raise RuntimeError("%s" % e)

            for file in files:
                path = os.path.join(root, file)
                try:
                    os.chmod(path, permissions)
                except Exception as e:
                    if str(e).find("No such file or directory") == -1:
                        raise RuntimeError("%s" % e)

    def home_expand(self, path):
        """
        Expands ~ prefix in paths to their full path equivalent.

        @param path Path to expand
        @raises RuntimeError when HOME environment variable is not set
        """
        if path and path.startswith("~%s" % os.sep):
            if not os.environ['HOME']:
                raise RuntimeError("Cannot expand directory when HOME environment variable is not set!")
            return os.path.expanduser(path)
        return path

    def getTmpPath(self, filename):
        return "%s/jumpscaleinstall/%s" % ('/tmp', filename)


    # def getWalker(self):
    #     self._initExtra()
    #     return self.extra.getWalker(self)


class ExecutorMethods():

    def executeBashScript(
            self,
            content="",
            path=None,
            die=True,
            remote=None,
            sshport=22,
            showout=True,
            outputStderr=True,
            sshkey="",
            timeout=600,
            executor=None):
        """
        @param remote can be ip addr or hostname of remote, if given will execute cmds there
        """
        if path is not None:
            content = self.readFile(path)
        if content[-1] != "\n":
            content += "\n"

        if remote is None:
            tmppath = self.getTmpPath("")
            content = "cd %s\n%s" % (tmppath, content)
        else:
            content = "cd /tmp\n%s" % content

        if die:
            content = "set -ex\n%s" % content

        path2 = self.getTmpPath("do.sh")
        self.writeFile(path2, content, strip=True)

        if remote is not None:
            tmppathdest = "/tmp/do.sh"
            if sshkey:
                if not self.SSHKeyGetPathFromAgent(sshkey, die=False) is None:
                    self.execute('ssh-add %s' % sshkey)
                sshkey = '-i %s ' % sshkey.replace('!', '\!')
            self.execute(
                "scp %s -oStrictHostKeyChecking=no -P %s %s root@%s:%s " %
                (sshkey, sshport, path2, remote, tmppathdest), die=die, executor=executor)
            rc, res, err = self.execute(
                "ssh %s -oStrictHostKeyChecking=no -A -p %s root@%s 'bash %s'" %
                (sshkey, sshport, remote, tmppathdest), die=die, timeout=timeout, executor=executor)
        else:
            rc, res, err = self.execute(
                "bash %s" %
                path2, die=die, showout=showout, outputStderr=outputStderr, timeout=timeout, executor=executor)
        return rc, res, err

    def executeCmds(
            self,
            cmdstr,
            showout=True,
            outputStderr=True,
            useShell=True,
            log=True,
            cwd=None,
            timeout=120,
            captureout=True,
            die=True,
            executor=None):
        rc_ = []
        out_ = ""
        for cmd in cmdstr.split("\n"):
            if cmd.strip() == "" or cmd[0] == "#":
                continue
            cmd = cmd.strip()
            rc, out, err = self.execute(cmd, showout, outputStderr, useShell, log, cwd,
                                        timeout, captureout, die, executor=executor)
            rc_.append(str(rc))
            out_ += out

        return rc_, out_

    def executeInteractive(self, command, die=True):
        exitcode = os.system(command)
        if exitcode != 0 and die:
            raise RuntimeError("Could not execute %s" % command)
        return exitcode

    def checkInstalled(self, cmdname):
        """
        @param cmdname is cmd to check e.g. curl
        """
        rc, out, err = self.execute(
            "which %s" %
            cmdname, die=False, showout=False, outputStderr=False)
        if rc == 0:
            return True
        else:
            return False

    def execute(
            self,
            command,
            showout=True,
            outputStderr=True,
            useShell=True,
            log=True,
            cwd=None,
            timeout=0,
            errors=[],
            ok=[],
            captureout=True,
            die=True,
            async=False,
            executor=None):
        """
        @param errors is array of statements if found then exit as error
        return rc,out,err
        """

        command = self.textstrip(command)
        if executor:
            return executor.execute(
                command,
                die=die,
                checkok=False,
                showout=True,
                timeout=timeout)
        else:
            return j.tools.executorLocal.execute(
                command,
                showout=showout,
                outputStderr=outputStderr,
                die=die)

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
            self.execute("kill -9 %s" % pid, showout=False)
        if self.psfind(name):
            raise RuntimeError("stop debug here")
            raise RuntimeError(
                "Could not kill:%s, is still, there check if its not autorestarting." %
                name)


class InstallTools(ExecutorMethods, FSMethods):
    def __init__(self, debug=False):

        self.__jslocation__ = "j.core.installtools"

        self._asyncLoaded = False
        self._deps = None
        self._config = None

        self.debug=False

        self.platformtype = j.core.platformtype

        self.logger = j.logger.get("installtools")


    # def linkJSCommandsToSystem(self):
    #     src = "%s/github/jumpscale/core9/cmds/" % j.core.state.config["dirs"]["CODEDIR"]
    #     self.symlinkFilesInDir(src, "/usr/local/bin", delete=True, includeDirs=False, makeExecutable=True)
        

    @property
    def mascot(self):
        mascotpath = "%s/.mascot.txt" % os.environ["HOME"]
        if not j.sal.fs.exists(mascotpath):
            print("env has not been installed properly (missing mascot), please follow init instructions on https://github.com/Jumpscale/core9")
            sys.exit(1)
        return self.readFile(mascotpath)



    @property
    def epoch(self):
        '''
        Get epoch timestamp (number of seconds passed since January 1, 1970)
        '''
        return int(time.time())

    @property
    def whoami(self):
        if self._whoami is not None:
            return self._whoami
        rc, result, err = self.execute(
            "whoami", die=False, showout=False, outputStderr=False)
        if rc > 0:
            # could not start ssh-agent
            raise RuntimeError(
                "Could not call whoami,\nstdout:%s\nstderr:%s\n" %
                (result, err))
        else:
            self._whoami = result.strip()
        return self._whoami


do = InstallTools()
