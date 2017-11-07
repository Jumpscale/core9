

class Sal():
    def __init__(self):
        pass


class Tools():
    def __init__(self):
        pass


class Data():
    def __init__(self):
        pass


class Clients():
    def __init__(self):
        pass


class Core():
    def __init__(self):
        pass


class Servers():
    def __init__(self):
        pass


class DataUnits():
    def __init__(self):
        pass


class Portal():
    def __init__(self):
        pass


class AtYourService():
    def __init__(self):
        pass


class Jumpscale9():

    def __init__(self):
        self.tools = Tools()
        self.sal = Sal()
        self.data = Data()
        self.clients = Clients()
        self.core = Core()
        self.servers = Servers()
        self.data_units = DataUnits()
        self.portal = Portal()
        self.atyourservice = AtYourService()
        self.exceptions = None


j = Jumpscale9()


class Empty():
    pass

j.dirs = Empty()
j.dirs.TMPDIR = "/tmp"

from .data.text.Text import Text
j.data.text = Text()

from .data.types.Types import Types
j.data.types = Types()

from .data.regex.RegexTools import RegexTools
j.data.regex = RegexTools()

from .logging.LoggerFactory import LoggerFactory
j.logger = LoggerFactory()
j.logger.enableConsoleHandler()

from .fs.SystemFS import SystemFS
j.sal.fs = SystemFS()

from .sal.process.SystemProcess import SystemProcess
j.sal.process = SystemProcess()

from .data.key_value_store.StoreFactory import StoreFactory
j.data.kvs = StoreFactory()

from .data.time.Time import Time_
j.data.time = Time_()

from .data.cache.Cache import Cache
j.data.cache = Cache()

from .tools.executor.ExecutorLocal import ExecutorLocal
j.tools.executorLocal = ExecutorLocal()  # needed in platformtypes

from .core.PlatformTypes import PlatformTypes
j.core.platformtype = PlatformTypes()

from .clients.redis.RedisFactory import RedisFactory
j.clients.redis = RedisFactory()

j.core.state = j.tools.executorLocal.state


if not j.core.state._configJS:
    j.tools.executorLocal.initEnv()

from .core.Dirs import Dirs
j.dirs = Dirs()
j.core.dirs = j.dirs

from .data.idgenerator.IDGenerator import IDGenerator
j.data.idgenerator = IDGenerator()


from .errorhandling.ErrorHandler import ErrorHandler
j.errorhandler = ErrorHandler()
j.core.errorhandler = j.errorhandler


from .core.Application import Application
j.application = Application()
j.core.application = j.application

j.logger.set_mode("DEV")

from .fs.SystemFSWalker import SystemFSWalker
j.sal.fswalker = SystemFSWalker

from .tools.loader.JSLoader import JSLoader
j.tools.jsloader = JSLoader()

from .tools.tmux.Tmux import Tmux
j.tools.tmux = Tmux()

from .clients.git.GitFactory import GitFactory
j.clients.git = GitFactory()

from .tools.path.PathFactory import PathFactory
j.tools.path = PathFactory()

from .tools.console.Console import Console
j.tools.console = Console()

from JumpScale9.errorhandling import JSExceptions
j.exceptions = JSExceptions
# j.events = j.core.events
j.core.db = j.clients.redis.get4core()

j.core.logger = j.logger
logging_cfg = j.core.state.configGet('logging', {})
if logging_cfg:
    level = logging_cfg.get('level', 'DEBUG')
    mode = logging_cfg.get('mode', 'DEV')
    filter_module = logging_cfg.get('filter', [])
    j.logger.init(mode, level, filter_module)
else:
    #DEV or PRODUCTION
    j.logger.init('DEV', 10, ['j.sal.fs',
                              'j.application', "j.sal.process"])

    j.logger.set_level(10)


# j.clients.redis.start4core()
