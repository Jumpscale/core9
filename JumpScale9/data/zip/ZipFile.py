

'''The ZipFile class provides convenience methods to work with zip archives'''

import sys
import os.path
import zipfile

from js9 import j


class ZipFileFactory:
    READ = 'r'
    WRITE = 'w'
    APPEND = 'a'

    def __init__(self):
        self.__jslocation__ = 'j.tools.zipfile'

    def get(self, path, mode=READ):
        return ZipFile(path, mode)


class ZipFile:
    '''Handle zip files'''

    def __init__(self, path, mode=ZipFileFactory.READ):
        '''Create a new ZipFile object

        @param path: Path to target zip file
        @type path: string
        @prarm mode: Action to perform on the zip file
        @type mode: ZipFileFactory Action
        '''
        self.logger = j.logger.get('j.tools.zipfile')

        if not j.data.types.path.check(path):
            raise ValueError('Provided string %s is not a valid path' % path)
        if mode is ZipFileFactory.READ:
            if not j.do.isFile(path):
                raise ValueError(
                    'Provided path %s is not an existing file' % path)
            if not zipfile.is_zipfile(path):
                raise ValueError(
                    'Provided path %s is not a valid zip archive' % path)
            self._zip = zipfile.ZipFile(path, 'r')
            # TODO Make this optional?
            result = self._zip.testzip()
            if result is not None:
                raise j.exceptions.RuntimeError('Trying to open broken zipfile, first broken file is %s' %
                                                result)

        else:
            raise ValueError('Invalid mode')

        self.path = path
        self.mode = mode

    def extract(self, destination_path, files=None, folder=None):
        '''Extract all or some files from the archive to destination_path

        The files argument can be a list of names (relative from the root of
        the archive) to extract. If no file list is provided, all files
        contained in the archive will be extracted.

        @param destination_path: Extraction output folder
        @type destination_path: string
        @param files: Filenames to extract
        @type files: iterable
        @param folder: Folder to extract
        @type folder: string
        '''
        if files and folder:
            raise ValueError('Only files or folders can be provided, not both')

        if not files:
            files = self._zip.namelist()

        if folder:
            files = (f for f in files if os.path.normpath(f).startswith(folder))

        # normpath to strip occasional ./ etc
        for f in (os.path.normpath(_f) for _f in files if not _f.endswith('/')):
            dirname = os.path.dirname(f)
            basename = os.path.basename(f)

            outdir = j.do.joinPaths(destination_path, dirname)
            j.do.createDir(outdir)
            outfile_path = j.do.joinPaths(outdir, basename)

            # On Windows we get some \ vs / in path issues. Check whether the
            # provided filename works, if not, retry replacing \ with /, and use
            # this one if found.
            try:
                self._zip.getinfo(f)
            except KeyError:
                if not j.core.platformtype.myplatform.isWindows:
                    raise
                f_ = f.replace('\\', '/')
                try:
                    self._zip.getinfo(f_)
                except KeyError:
                    pass
                else:
                    f = f_

            data = self._zip.read(f)
            # We need binary write
            self.logger.info('Writing file %s' % outfile_path)
            fd = open(outfile_path, 'wb')
            fd.write(data)
            fd.close()
            del data

    def close(self):
        '''Close the backing zip file'''
        self._zip.close()
