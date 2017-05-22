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


class Jumpscale9():

    def __init__(self):
        self.tools = Tools()
        self.sal = Sal()
        self.data = Data()
        self.clients = Clients()
        self.core = Core()
        self.exceptions = None


j = Jumpscale9()

from .data.text.Text import Text
j.data.text = Text()

from .data.types.Types import Types
j.data.types = Types()

from .logging.LoggerFactory import LoggerFactory
j.logger = LoggerFactory()
j.logger.enableConsoleHandler()


from .sal.process.SystemProcess import SystemProcess
j.sal.process = SystemProcess()

from .tools.executor.ExecutorLocal import ExecutorLocal
j.tools.executorLocal = ExecutorLocal()  # needed in platformtypes

from .core.PlatformTypes import PlatformTypes
j.core.platformtype = PlatformTypes()

# from .data.cache.Cache import Cache
# j.data.cache = Cache()

from .clients.redis.RedisFactory import RedisFactory
j.clients.redis = RedisFactory()

from .core.State import State
j.core.state = State()

from .core.InstallTools import InstallTools
j.do = InstallTools()

if "dirs" not in j.core.state.config:
    j.do.initEnv()

from .core.Dirs import Dirs
j.dirs = Dirs()
j.core.dirs = j.dirs

from .data.idgenerator.IDGenerator import IDGenerator
j.data.idgenerator = IDGenerator()

from .data.time.Time import Time_
j.data.time = Time_()

from .errorhandling.ErrorHandler import ErrorHandler
j.errorhandler = ErrorHandler()
j.core.errorhandler = j.errorhandler


from .core.Application import Application
j.application = Application()
j.core.application = Application()

j.logger.set_mode("DEV")


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

j.core.logger = j.logger
logging_cfg = j.application.config.get('logging')
if logging_cfg:
    level = logging_cfg.get('level', 'DEBUG')
    mode = logging_cfg.get('mode', 'DEV')
    filter_module = logging_cfg.get('filter', [])
    j.logger.init(mode, level, filter_module)
else:
    j.logger.init('DEV', 'DEBUG', ['j.sal.fs', 'j.application'])
# j.clients.redis.start4core()
