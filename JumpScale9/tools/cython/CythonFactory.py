import time
import inspect
from js9 import j
import sys

import pyximport


class CythonFactory:
    """
    example:
        '''
        j.core.cython.addCodePath("/tmp")
        #there need to be a helloworld.pyx in that path
        import helloworld
        helloworld.echo()
        '''
    """

    def __init__(self):
        self.__jslocation__ = "j.tools.cython"
        self.__imports__ = "cython"
        self.__path = ""
        self._currentPath

    @property
    def _currentPath(self):
        if self.__path == "":
            self.__path = j.do.getDirName(inspect.getsourcefile(self.__init__))
            sys.path.append(self.__path)
            pyximport.install()
        return self.__path

    def addCodePath(self, path):
        if path not in sys.path:
            sys.path.append(path)

    def test(self):
        import helloworld
        helloworld.echo()
        # helloworld.spam(10, bytearray("this is a test: int:\n".encode()))
        # helloworld.spam(10, b"this is a test: int:\n")
