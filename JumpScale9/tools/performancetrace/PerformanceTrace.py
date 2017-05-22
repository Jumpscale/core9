from js9 import j


class PerformanceTraceFactory:
    """
    """

    def __init__(self):
        self.__jslocation__ = "j.tools.performancetrace"

    def profile(self, methodstatement, locals={}, globals={}):
        """
        create a wrapper method which has no args and then pass that wrapper method to this method as first arg
        method is passed as a string e.g. 'listDirTest()'
        it remove stats is False the path where the stats are will be returned
        make sure that whatever arguments used in the statement are passed to the globals

        example:

        import JumpScale9.tools.performancetrace
        do=j.tools.performancetrace.profile('test0b()', globals=globals())

        """
        import cProfile
        import pstats
        path = j.do.joinPaths(j.dirs.TMPDIR, "perftest", "%s.log" % j.data.idgenerator.generateRandomInt(1, 10000))
        j.do.createDir(j.do.joinPaths(j.dirs.TMPDIR, "perftest"))
        globs = {
            '__file__': "afile",
            '__name__': '__main__',
            '__package__': None,
        }
        globals.update(globs)
        cProfile.runctx(methodstatement, globals, locals, path)
        p1 = pstats.Stats(path)

        # p1.strip_dirs().sort_stats('cum').print_stats(100)
        p1.strip_dirs().sort_stats('time').print_stats(100)
        j.do.removeDirTree(path)
        return p1
