from JumpScale9 import j
import time
import libtmux as tmuxp
import os


class Session:

    def __init__(self, session):

        self.id = session.get("session_id")
        self.name = session.get("session_name")
        self.mgmt = session
        self.reload()

    def reload(self):
        self.windows = []
        for w in self.mgmt.list_windows():
            self.windows.append(Window(self, w))

    def delWindow(self, name):
        windows = self.mgmt.list_windows()
        if len(windows) < 2:
            self.getWindow(name="ignore", removeIgnore=False)
        for w in self.mgmt.windows:
            wname = w.get("window_name")
            if name == wname:
                w.kill_window()
        j.core.db.delete("tmux:pane:%s" % self.name)
        self.reload()

    def existsWindow(self, name):
        for window in self.windows:
            if window.name == name:
                return True
        return False

    def getWindow(self, name, start_directory=None, attach=False, reset=False, removeIgnore=True):

        # from pudb import set_trace; set_trace()
        if reset:
            self.delWindow(name)

        for window in self.windows:
            if window.name == name:
                # is right construct, means we found a window, now we can safely remove ignore
                if self.existsWindow("ignore") and removeIgnore:
                    self.delWindow("ignore")
                return window

        print("create window:%s" % name)
        j.core.db.delete("tmux:pane:%s" % name)
        res = self.mgmt.new_window(name, start_directory=start_directory, attach=attach)

        window = Window(self, res)
        self.windows.append(window)
        window.select()

        # when only 1 pane then ignore had to be created again
        if self.existsWindow("ignore") and removeIgnore:
            self.delWindow("ignore")

        return window

    def kill(self):
        raise j.exceptions.RuntimeError("kill")

    def __repr__(self):
        return ("session:%s:%s" % (self.id, self.name))

    __str__ = __repr__


class Window:

    def __init__(self, session, window):
        self.name = window.get("window_name")
        self.session = session
        self.mgmt = window
        self.panes = []
        self.id = window.get("window_id")
        self._reload()

    @property
    def paneNames(self):
        names = [pane.name for pane in self.panes]
        return names

    def _reload(self):
        if len(self.mgmt.panes) == 1:
            self.panes = [Pane(self, self.mgmt.panes[0])]
        else:
            self.panes = []
            for pane in self.mgmt.panes:
                self.panes.append(Pane(self, pane))

    def existsPane(self, name="", id=0):
        """
       if there is only 1 and name is not same then name will be set
        """
        for pane in self.panes:
            if pane.name == name:
                return True
            if pane.id == id:
                return True
        return False

    def getPane(self, name, killothers=False, clear=False):
        """
       if there is only 1 and name is not same then name will be set
        """
        if len(self.panes) == 1:
            self.panes[0].name = name
            if clear:
                self.panes[0].mgmt.send_keys("clear")
            return self.panes[0]
        for pane in self.panes:
            if pane.name == name:
                if killothers:
                    for pane2 in self.panes:
                        if pane2.name != name:
                            pane2.kill()
                if clear:
                    pane.mgmt.send_keys("clear")
                return pane
        raise j.exceptions.RuntimeError("Could not find pane:%s.%s" % (self.name, name))

    def select(self):
        self.mgmt.select_window()

    def kill(self):
        if len(self.session.windows.keys()) < 2:
            self.session.getWindow(name="ignore")
        print("KILL %s" % self.name)
        self.mgmt.kill_window()

    def __repr__(self):
        return ("window:%s:%s" % (self.id, self.name))

    __str__ = __repr__


class Pane:

    def __init__(self, window, pane):
        self.mgmt = pane
        self.id = pane.get("pane_id")
        self.window = window

    @property
    def name(self):
        res = j.core.db.hget("tmux:%s:name" % self.window.name, str(self.id))
        if res is None:
            return ""
        else:
            res = res.decode()
            return res

    @name.setter
    def name(self, name):
        j.core.db.hset("tmux:%s:name" % self.window.name, str(self.id), name)

    def select(self):
        self.mgmt.select_pane()

    def _split(self, name, ext="-v"):
        self.select()
        j.sal.tmux.execute("split-window %s" % ext)
        # look for pane who is not found yet
        panefound = None
        for pane2 in self.window.mgmt.panes:
            if not self.window.existsPane(id=pane2.get("pane_id")):
                if panefound is not None:
                    raise j.exceptions.RuntimeError("can only find 1 pane, bug")
                panefound = pane2
        pane = Pane(self.window, panefound)
        pane.name = name
        self.window.panes.append(pane)
        return pane

    def splitVertical(self, name2, name1="", clear=False):
        res = self._split(name2, "-v")
        if name1 != "":
            self.name = name1
        if clear:
            res.mgmt.send_keys("clear")
        return res

    def splitHorizontal(self, name2, name1="", clear=False):
        res = self._split(name2, "-h")
        if name1 != "":
            self.name = name1
        if clear:
            res.mgmt.send_keys("clear")
        return res

    def execute(self, cmd, wait=False):
        j.core.db.hset("tmux:%s:exec" % self.window.name, self.name, "%s" % j.data.time.getTimeEpoch())
        # set exit code and date in front
        cmd2 = "echo HSET tmux:%s:exec %s %s:$? | redis-cli -s /tmp/redis.sock -x > /dev/null 2>&1" %\
            (self.window.name, self.name, j.data.time.getTimeEpoch())
        cmdall = cmd + ";" + cmd2
        # print (cmd)
        self.mgmt.send_keys(cmdall)
        if wait:
            return self.wait()

    def resetState(self):
        """
        make sure that previous exit code is removed and all is clean for next run
        """
        j.core.db.hset("tmux:%s:exec" % self.window.name, self.name, "")

    def check(self):
        res = j.core.db.hget("tmux:%s:exec" % self.window.name, self.name)
        if res == "":
            return ""
        res = res.decode()
        if ":" in res:
            epoch, rc = res.split(":")
            state = "OK"
        else:
            state = "INIT"
            rc = 0
            epoch = res

        epoch = int(epoch)
        rc = int(rc)
        if rc > 0:
            state = "ERROR"

        # duration=j.data.time.getTimeEpoch()-epoch
        return state, epoch, rc

    def wait(self):
        while True:
            state, epoch, rc = self.check()
            if state != "INIT":
                return state, epoch, rc
            time.sleep(0.1)

    def __repr__(self):
        return ("panel:%s:%s" % (self.id, self.name))

    __str__ = __repr__


class Tmux:

    def __init__(self):
        self.__jslocation__ = "j.tools.tmux"
        self.__imports__ = "libtmux"
        self.sessions = {}
        # tmuxpath=j.do.joinPaths(j.dirs.TMPDIR,"tmux")
        # os.environ["TMUX_TMPDIR"]=tmuxpath
        # j.do.createDir(tmuxpath)

    def _getServer(self, name, firstWindow="ignore"):
        try:
            s = tmuxp.Server()
            s.list_sessions()
        except Exception as e:
            session1 = s.new_session(firstWindow)
        return s

    def getSession(self, name, reset=False, attach=False, firstWindow="ignore"):
        if reset and name in self.sessions:
            self.sessions[name].kill()

        if name in self.sessions:
            return self.sessions[name]

        print("create session:%s" % name)

        s = self._getServer(name, firstWindow=firstWindow)

        if reset:
            res = s.new_session(session_name=name, kill_session=kill_session, attach=attach)
        else:
            res = None
            for se in s.list_sessions():
                sname = se.get("session_name")
                if name == sname:
                    res = se
            if res is None:
                res = s.new_session(session_name=name, kill_session=False, attach=attach)

        self.sessions[name] = Session(res)
        return self.sessions[name]

    def execute(self, cmd, session="main", window="main", pane="main"):
        """
        """
        s = self.getSession(session)
        w = s.getWindow(window)
        p = w.getPane(pane)
        p.execute(cmd)

    def createPanes4x4(self, sessionName="main", windowName="actions", reset=True):
        session = self.getSession(sessionName, firstWindow=windowName)
        window = session.getWindow(windowName, reset=reset)

        if len(window.panes) == 16 and reset is False:
            return window

        a = window.getPane(name=windowName, killothers=True)
        b = a.splitVertical("b")
        a.splitVertical("2", "1")
        b.splitVertical("4", "3")

        for paneName in window.paneNames:
            a = window.getPane(paneName)
            try:
                count = int(a.name.decode())
            except BaseException:
                count = int(a.name)
            b = a.splitHorizontal("b")  # first split
            a.splitHorizontal("P%s2" % count, "P%s1" % count)
            b.splitHorizontal("P%s4" % count, "P%s3" % count)

        for pane in window.panes:
            pane.execute("clear;echo %s" % pane.name)

        return window
