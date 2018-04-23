from JumpScale9 import j

import logging
from .Handlers import *

from .JSLogger import JSLogger
from .JSLoggerDefault import JSLoggerDefault
import sys


class LoggerFactory():

    def __init__(self):
        self.__jslocation__ = "j.core.logger"
        self.logger_name = 'j'
        self.handlers = Handlers()
        self.loggers = {}

        self._default = JSLoggerDefault("default")

        self.logger = JSLogger("logger")
        self.logger.addHandler(self.handlers.consoleHandler)

        self.enabled = True
        self.filter = ["*"]  # default filter to see which loggers will be attached needs to have * or j.sal... inside

        # self.logger.debug("started logger factory")

    def _getName(self, name):

        name = name.strip().lower()

        if name == "":
            path, ln, name, info = logging.root.findCaller()
            if path.startswith(j.dirs.LIBDIR):
                path = path.lstrip(j.dirs.LIBDIR)
                name = path.replace(os.sep, '.')

        if not name.startswith(self.logger_name):
            name = "%s.%s" % (self.logger_name, name)

        if len(name) > 22:
            name = name[-22:]

        return name

    def get(self, name="", force=False):# -> JSLogger:
        """
        Return a logger with the given name. Name will be prepend with 'j.' so
        every logger return by this function is a child of the jumpscale root logger 'j'

        """

        name = self._getName(name)

        def check_(name):
            # print("check %s"%name)
            for item in self.exclude:                
                # print("check exclude:%s"%item)
                if item == "*":
                    # print("exclude %s:%s" % (item, name))
                    return False
                if name.find(item) != -1:
                    # print("exclude %s:%s" % (item, name))
                    return False
            for item in self.filter:   
                # print("check include:%s"%item)             
                if item == "*":
                    # print("include: %s:%s" % (item, name))
                    return True
                if name.find(item) != -1:
                    # print("include: %s:%s" % (item, name))
                    return True
            return False

        if force == False and self.enabled is False:
            self.loggers[name] = self._default
            # print("DEFAULT LOGGER (disabledlogger):%s" % name)
        else:
            if force or check_(name):
                # print("JSLOGGER:%s" % name)
                # logger = logging.getLogger(name)
                logger = JSLogger(name)
                logger.level = j.core.state.configGetFromDict("logging", "level", 'DEBUG')

                for handler in self.handlers._all:
                    logger.handlers = []
                    logger.addHandler(handler)

                self.loggers[name] = logger
            else:
                # print("DEFAULT LOGGER:%s" % name)
                self.loggers[name] = self._default

        return self.loggers[name]

    def disable(self):
        """
        will transform all loggers to empty loggers which only act on errors, but ignore logs
        """
        if self.enabled:
            self.enabled = False
            self.filter = []

            # for key, logger in self.loggers.items():
            #     # print("disable logger: %s"%key)
            #     logger.setLevel(20)
            j.application.debug = False

            self.logger_filters_add()

    def enable(self):
        """
        """
        if self.enabled is False:
            self.enabled = True
            self.filter = []
            self.init()

    # def set_quiet(self, quiet):
    #     self._quiet = quiet

    # def set_mode(self, mode):
    #     if isinstance(mode, str):
    #         if mode in _name_to_mode:
    #             mode = _name_to_mode[mode]
    #         else:
    #             raise j.exceptions.Input("mode %s doesn't exist" % mode)

    #     if mode == self.PRODUCTION:
    #         self._enable_production_mode()
    #     elif mode == self.DEV:
    #         self._enable_dev_mode()

    # def set_level(self, level=10):
    #     """
    #     Set logging levels on all loggers and handlers
    #     Added to support backward compatability
    #     """
    #     self.loggers_level_set(level=level)

    def handlers_level_set(self, level=10):
        """

        sets level in all handlers

        10=debug
        20=info

        info see:
        https://docs.python.org/3/library/logging.html#levels

        """
        for handler in self.handlers._all:
            handler.setLevel(level)

    def loggers_level_set(self, level='DEBUG'):
        """

        sets level in all handlers & loggers

        10=debug
        20=info

        info see:
        https://docs.python.org/3/library/logging.html#levels

        """
        for key, logger in self.loggers.items():
            logger.setLevel(level)
        self.handlers_level_set(level)

    def handlers_attach(self):
        """
        walk over all loggers, attach the handlers
        """
        for key, logger in self.loggers.items():
            for handler in self.handlers._all:
                logger.handlers = []
                logger.addHandler(handler)

    def memhandler_enable(self):
        # self.logger.propagate = True
        self.logger.addHandler(self.handlers.memoryHandler)

    def consolehandler_enable(self):
        # self.logger.propagate = True
        self.logger.addHandler(self.handlers.consoleHandler)

    def telegramhandler_enable(self, client, chat_id):
        """
        Enable a telegram handler to forward logs to a telegram group.
        @param client: A jumpscale telegram_bot client 
        @param chat_id: Telegram chat id to which logs need to be forwarded
        """
        self.logger.addHandler(self.handlers.telegramHandler(client, chat_id))     

    def handlers_reset(self):
        self.logger.handlers = []

    def logger_filters_get(self):
        return j.core.state.config_js["logging"]["filter"]

    def logger_filters_add(self, items=[],exclude=[], level=10, save=False):
        """
        items is list or string e.g. prefab, exec
        will add the filters to the logger and save it in the config file

        """
        items = j.data.types.list.fromString(items)
        exclude = j.data.types.list.fromString(exclude)
        if save:
            new = False
            for item in items:
                if item not in j.core.state.config_js["logging"]["filter"]:
                    j.core.state.config_js["logging"]["filter"].append(item)
                    new = True
            for item in exclude:
                if item not in j.core.state.config_js["logging"]["exclude"]:
                    j.core.state.config_js["logging"]["exclude"].append(item)
                    new = True
            if new:
                j.core.state.configSave()
                self.init()

        for item in items:
            item = item.strip().lower()
            if item not in self.filter:
                self.filter.append(item)

        for item in exclude:
            item = item.strip().lower()
            if item not in self.exclude:
                self.exclude.append(item)

        self.logger.debug("start re-init for logging")

        self.handlers_level_set(level)

        # make sure all loggers are empty again
        j.dirs._logger = None
        j.core.platformtype._logger = None
        j.core.state._logger = None
        j.core.dirs._logger = None
        j.core.application._logger = None
        for cat in [j.data, j.clients, j.tools, j.sal]:
            for key, item in cat.__dict__.items():
                if item is not None:
                    # if hasattr(item, '__jslocation__'):
                    #     print (item.__jslocation__)
                    if 'logger' in item.__dict__:                        
                        item.__dict__["logger"] = self.get(item.__jslocation__)
                    item._logger = None
        self.loggers = {}

        
        # print(j.tools.jsloader._logger)
        # print(j.tools.jsloader.logger)

    def init(self):
        """
        get info from config file & make sure all logging is done properly
        """
        self.enabled = j.core.state.configGetFromDict("logging", "enabled", True)
        level = j.core.state.configGetFromDict("logging", "level", 'DEBUG')
        self.loggers_level_set(level)
        self.handlers_level_set(level)
        self.filter = []
        self.exclude = []
        self.loggers = {}
        items = j.core.state.configGetFromDict("logging", "filter", [])
        exclude = j.core.state.configGetFromDict("logging", "exclude", [])
        self.logger_filters_add(items=items, exclude=exclude, save=False)

    # def enableConsoleMemHandler(self):
    #     self.logger.handlers = []
    #     # self.logger.propagate = True
    #     self.logger.addHandler(self.handlers.memoryHandler)
    #     self.logger.addHandler(self.handlers.consoleHandler)

    # def _enable_production_mode(self):
    #     self.logger.handlers = []
    #     self.logger.addHandler(logging.NullHandler())
    #     # self.logger.propagate = True

    # def _enable_dev_mode(self):
    #     logging.setLoggerClass(JSLogger)
    #     self.logger.setLevel(logging.DEBUG)
    #     self.logger.propagate = False
    #     logging.lastResort = None
    #     self.enableConsoleHandler()
    #     self.logger.addHandler(self.handlers.fileRotateHandler)

    def test(self):

        logger = self.get("loggerTest")

        self.enableConsoleMemHandler()

        logger.info("a test")

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
