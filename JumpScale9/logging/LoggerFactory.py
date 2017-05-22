from JumpScale9 import j
import logging
import time
import os
from colorlog import ColoredFormatter
from logging.handlers import TimedRotatingFileHandler
from logging.handlers import MemoryHandler
from JumpScale9.logging.JSLogger import JSLogger
from JumpScale9.logging.Filter import ModuleFilter


FILE_FORMAT = '%(asctime)s - %(pathname)s:%(lineno)d - %(levelname)-8s - %(message)s'
CONSOLE_FORMAT = '%(cyan)s[%(asctime)s]%(reset)s - %(filename)-20s:%(lineno)-4d:%(name)-30s - %(log_color)s%(levelname)-8s%(reset)s - %(message)s'

# Modes
PRODUCTION = 0  # use NullHander, let the application configure the logging
DEV = 10  # use predefine handlers for console and file.

_mode_to_name = {
    PRODUCTION: "PRODUCTION",
    DEV: "DEV"
}
_name_to_mode = {
    "PRODUCTION": PRODUCTION,
    "DEV": DEV
}


class Handlers():

    def __init__(self):
        self._fileRotateHandler = None
        self._consoleHandler = None
        self._memoryHandler = None
        self._all = []

    @property
    def fileRotateHandler(self, name='jumpscale'):
        if self._fileRotateHandler is None:
            if not j.do.exists("%s/log/" % j.dirs.VARDIR):
                j.do.createDir("%s/log/" % j.dirs.VARDIR)
            filename = "%s/log/%s.log" % (j.dirs.VARDIR, name)
            formatter = logging.Formatter(FILE_FORMAT)
            fh = TimedRotatingFileHandler(
                filename, when='D', interval=1, backupCount=7, encoding=None, delay=False, utc=False, atTime=None)
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            self._fileRotateHandler = fh
            self._all.append(self._fileRotateHandler)
        return self._fileRotateHandler

    @property
    def consoleHandler(self):
        if self._consoleHandler is None:
            formatter = LimitFormater(
                fmt=CONSOLE_FORMAT,
                datefmt="%a%d %H:%M",
                reset=True,
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                },
                secondary_log_colors={},
                style='%',
                lenght=37
            )
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            ch.setFormatter(formatter)
            self._consoleHandler = ch
            self._all.append(self._consoleHandler)
        return self._consoleHandler

    @property
    def memoryHandler(self):
        if self._memoryHandler is None:
            self._memoryHandler = MemoryHandler(capacity=10000)
            self._all.append(self._memoryHandler)
        return self._memoryHandler


class LoggerFactory:

    def __init__(self):
        self.__jslocation__ = "j.core.logger"
        self.root_logger_name = 'j'
        self.handlers = Handlers()

        self.PRODUCTION = PRODUCTION
        self.DEV = DEV
        self._quiet = False

        self.root_logger = logging.getLogger(self.root_logger_name)

    def test(self):

        logger = self.get("loggerTest")

        self.enableConsoleMemHandler()

        logger.info("a test")

    def testPerformance(self):
        logger = self.get("loggerTest")

        self.enableMemHandler()

        def perftest(logger):
            print("start perftest logger")
            start = time.time()
            nr = 30000
            for i in range(nr):
                logger.info("this is an info message")
                # self.getActionObjFromMethod(test)
            stop = time.time()
            print("nr of logs per sec:%s" % int(nr / (stop - start)))

        perftest(logger)

        # FOLLOWING PROVES THAT THE LOOKING FOR FILE & PATH INFO IS THE SLOWING DOWN FACTOR
        # j.tools.performancetrace.profile("perftest(logger)", globals=locals())  # {"perftest": perftest}

    def init(self, mode="DEV", level=10, filter=[]):
        self.set_mode(mode.upper())
        self.set_level(level.upper())
        if filter:
            self.handlers.consoleHandler.addFilter(ModuleFilter(filter))

    def get(self, name=None, enable_only_me=False) -> JSLogger:
        """
        Return a logger with the given name. Name will be prepend with 'j.' so
        every logger return by this function is a child of the jumpscale root logger 'j'

        Usage:
            self.root_logger = j.logger.get(__name__)
        in library module always pass __name__ as argument.
        """

        name = name.strip()
        name = name.lower()

        # if len(name) > 22:
        #     name = name[-22:]

        if not name:
            path, ln, name, info = logging.root.findCaller()
            if path.startswith(j.dirs.LIBDIR):
                path = path.lstrip(j.dirs.LIBDIR)
                name = path.replace(os.sep, '.')
        if not name.startswith(self.root_logger_name):
            name = "%s.%s" % (self.root_logger_name, name)

        logger = logging.getLogger(name)

        if enable_only_me:
            logger = JSLogger(name)
            logger.enable_only_me()

        return logger

    def set_quiet(self, quiet):
        self._quiet = quiet

    def set_mode(self, mode):
        if isinstance(mode, str):
            if mode in _name_to_mode:
                mode = _name_to_mode[mode]
            else:
                raise j.exceptions.Input("mode %s doesn't exist" % mode)

        if mode == self.PRODUCTION:
            self._enable_production_mode()
        elif mode == self.DEV:
            self._enable_dev_mode()

    def set_level(self, level):
        """
        level 0 to 10
        10 being most verbose (need to verify this)
        """
        for handler in self.handlers._all:
            handler.setLevel(level)

    def enableMemHandler(self):
        self.root_logger.handlers = []
        # self.root_logger.propagate = True
        self.root_logger.addHandler(self.handlers.memoryHandler)

    def enableConsoleHandler(self):
        self.root_logger.handlers = []
        # self.root_logger.propagate = True
        self.root_logger.addHandler(self.handlers.consoleHandler)

    def enableConsoleMemHandler(self):
        self.root_logger.handlers = []
        # self.root_logger.propagate = True
        self.root_logger.addHandler(self.handlers.memoryHandler)
        self.root_logger.addHandler(self.handlers.consoleHandler)

    def _enable_production_mode(self):
        self.root_logger.handlers = []
        self.root_logger.addHandler(logging.NullHandler())
        # self.root_logger.propagate = True

    def _enable_dev_mode(self):
        logging.setLoggerClass(JSLogger)
        self.root_logger.setLevel(logging.DEBUG)
        self.root_logger.propagate = False
        logging.lastResort = None
        self.enableConsoleHandler()
        self.root_logger.addHandler(self.handlers.fileRotateHandler)

    def __fileRotateHandler(self, name='jumpscale'):
        if not j.do.exists("%s/log/" % j.dirs.VARDIR):
            j.do.createDir("%s/log/" % j.dirs.VARDIR)
        filename = "%s/log/%s.log" % (j.dirs.VARDIR, name)
        formatter = logging.Formatter(FILE_FORMAT)
        fh = logging.handlers.TimedRotatingFileHandler(
            filename, when='D', interval=1, backupCount=7, encoding=None, delay=False, utc=False, atTime=None)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        return fh

    def __consoleHandler(self):
        formatter = LimitFormater(
            fmt=CONSOLE_FORMAT,
            datefmt="%a%d %H:%M",
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            },
            secondary_log_colors={},
            style='%',
            lenght=37
        )
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        return ch

    def __redisHandler(self, redis_client=None):
        if redis_client is None:
            self.redis_client = j.core.db


class LimitFormater(ColoredFormatter):

    def __init__(self, fmt, datefmt, reset, log_colors, secondary_log_colors, style, lenght):
        super(LimitFormater, self).__init__(
            fmt=fmt,
            datefmt=datefmt,
            reset=reset,
            log_colors=log_colors,
            secondary_log_colors=secondary_log_colors,
            style=style)
        self.lenght = lenght

    def format(self, record):
        if len(record.pathname) > self.lenght:
            record.pathname = "..." + record.pathname[-self.lenght:]
        return super(LimitFormater, self).format(record)
