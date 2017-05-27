from js9 import j
from .ExecutorBase import ExecutorBase
try:
    import g8core
except ImportError:
    logger = j.logger.get("g8core")
    logger.error("cannot find g8core")


class ExecutorG8Core(ExecutorBase):
    """Executor that talks with a g8os/core0 node"""

    def __init__(self, host, port=6369, password=None, container_id=None, debug=False, checkok=False):
        super().__init__(debug=debug, checkok=checkok)
        self.host = host
        self.port = port
        self._password = password
        self._core0_cient = g8core.Client(host=host, port=port, password=password)
        self._id = 'core0_{}_{}'.format(host, port)
        if container_id:
            self._core0_cient = self._core0_cient.container.client(container_id)
            self._id += '_container_{}'.format(container_id)

    def execute(self, cmds, die=True, checkok=None, showout=True, timeout=10, env={}):
        if env:
            self.env.update(env)

        if self.debug:
            print("EXECUTOR:%s" % cmds)

        if checkok is None:
            checkok = self.checkok

        cmds2 = self._transformCmds(cmds, die=die, checkok=checkok, env=env)

        resp = self._core0_cient.bash(cmds2).get(timeout=timeout)

        if checkok:
            out = self.docheckok(cmds, resp.stdout)
        else:
            out = resp.stdout

        rc = 0 if resp.state == 'SUCCESS' else 1

        return rc, out, resp.stderr

    def executeRaw(self, cmd, die=True, showout=False):
        resp = self._core0_cient.bash(cmd).get(timeout=10)
        rc = 0 if resp.state == 'SUCCESS' else 1

        if die and rc != 0:
            raise RuntimeError(resp.stderr)

        return rc, resp.stdout, resp.stderr
