'''The TarFile class provides convenience methods to work with tar archives'''

from js9 import j
import tarfile

# NOTE: When implementing, see documentation on the 'errorlevel' attribute of
# the Python TarFile object


class TarFileFactory:
    READ = 'r'
    WRITE = 'w'
    APPEND = 'a'

    def __init__(self):
        self.__jslocation__ = "j.tools.tarfile"

    def get(self, path, mode=READ):
        return TarFile(path, mode)


class TarFile:
    '''Handle tar files'''

    def __init__(self, path, mode=TarFileFactory.READ):
        '''Create a new TarFile object

        @param path: Path to target tar file
        @type path: string
        @prarm mode: mode to perform on the tar file
        @type mode: TarFilemode
        '''
        if not j.data.types.path.check(path):
            raise ValueError('Provided string "%s" is not a valid path' % path)

        if mode is TarFileFactory.READ:
            if not j.do.isFile(path):
                raise ValueError('Provided path "%s" is not an existing file' % path)

            if not tarfile.is_tarfile(path):
                raise ValueError('Provided path "%s" is not a valid tar archive' % path)

            self._tar = tarfile.open(path, 'r')

        elif mode is TarFileFactory.WRITE:
            self._tar = tarfile.open(path, 'w')

        else:
            raise ValueError('Invalid mode')

        self.path = path
        self.mode = mode

    def add(self, file, name=None):
        """
        Add a file to the tarball, if name is specified, this name
        will be used on the archive (alternative name)
        """
        self._tar.add(file, arcname=name)

    def addFiltered(self, file, name=None, filtering=None):
        """
        Add a file to the tarball, if name is specified, this name
        will be used on the archive (alternative name)
        This method accept a filter functions which can manipulate the TarInfo
        This function need to take TarInfo in argument and return the modified object
        """
        self._tar.add(file, arcname=name, recursive=True, exclude=None, filter=filtering)

    def get(self, name):
        """
        Return a tarinfo about a file in the tar
        """
        return self._tar.getmember(name)

    def extract(self, destination_path, files=None):
        '''Extract all or some files from the archive to destination_path

        The files argument can be a list of names (relative from the root of
        the archive) to extract. If no file list is provided, all files
        contained in the archive will be extracted.

        @param destination_path: Extrmode output folder
        @type destination_path: string
        @param files: Filenames to extract
        @type files: iterable
        '''
        if self.mode is not TarFileFactory.READ:
            raise j.exceptions.RuntimeError('Can only extract archives opened for reading')

        if not j.data.types.path.check(destination_path):
            raise ValueError('Not a valid folder name provided')

        if not j.do.exists(destination_path):
            raise ValueError('Destination folder "%s" does not exist' % destination_path)

        members = list()
        if files:
            all_members = self._tar.getmembers()
            for member in all_members:
                if member.name in files:
                    members.append(member)

        if members:
            self._tar.extractall(destination_path, members)
        else:
            self._tar.extractall(destination_path)

    def close(self):
        '''Close the backing tar file'''
        self._tar.close()
