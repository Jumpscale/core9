from js9 import j


class RsyncInstance:

    def __init__(self):
        self.name
        self.secret
        self.users = []
        self.readonly = True
        self.exclude = "*.pyc .git"


class RsyncServer:

    """
    """

    def __init__(self, root, port=873, distrdir=""):
        self._local = j.tools.executorLocal
        self.root = root
        self.port = port
        self.pathsecrets = j.tools.path.get("%s/secrets.cfg" % self.root)
        self.pathusers = j.tools.path.get("%s/users.cfg" % self.root)
        if distrdir == "":
            distrdir = "%s/apps/agentcontroller/distrdir/" % j.dirs.JSBASEDIR

        self.distrdir = j.tools.path.get(distrdir)

        self.rolesdir = j.tools.path.get(self.root).joinpath("roles")

        j.tools.path.get("/etc/rsync").mkdir_p()

        if self.pathsecrets.exists():
            self.secrets = j.data.serializer.toml.loads(self.pathsecrets.text())
        else:
            self.secrets = {}

        if self.pathusers.exists():
            self.users = j.data.serializer.toml.loads(self.pathusers.text())
        else:
            self.users = {}

    def addUserAccessUpload(self, user, passwd):
        self.users.append([user, passwd])

    def addSecret(self, name, secret=""):
        if name in self.secrets and secret == "":
            # generate secret
            secret = self.secrets[name]
        if secret == "":
            secret = j.data.idgenerator.generateGUID().replace("-", "")

        self.secrets[name.strip()] = secret.strip()
        self.pathsecrets.write_text(j.data.serializer.toml.dumps(self.secrets))

    def addUser(self, name, passwd):
        self.users[name.strip()] = passwd.strip()
        self.pathusers.write_text(j.data.serializer.toml.dumps(self.users))

    def saveConfig(self):

        C = """
#motd file = /etc/rsync/rsyncd.motd
port = $port
log file=/var/log/rsync
max verbosity = 1

[upload]
exclude = *.pyc .git
path = $root/root
comment = upload
uid = root
gid = root
read only = false
auth users = $users
secrets file = /etc/rsync/users

"""
        D = """
[$secret]
exclude = *.pyc .git
path = $root/root/$name
comment = readonlypart
uid = root
gid = root
read only = true
list = no

"""
        users = ""
        for name, secret in list(self.users.items()):
            users += "%s," % name
        users.rstrip(",")

        for name, secret in list(self.secrets.items()):
            path = j.tools.path.get("%s/root/%s" % (self.root, name))
            path.mkdir_p()
            D2 = D.replace("$secret", secret)
            D2 = D2.replace("$name", name)
            C += D2

        C = C.replace("$root", self.root)
        C = C.replace("$users", users)
        C = C.replace("$port", str(self.port))

        j.tools.path.get("/etc/rsync/rsyncd.conf").write_text(C)

        path = j.tools.path.get("/etc/rsync/users")
        out = ""
        for name, secret in list(self.users.items()):
            out += "%s:%s\n" % (name, secret)

        path.write_text(out)

        path.chmod(0o600)

        # with bindmounts
        # cmd="mount | grep /tmp/server"

        # rc,out=j.sal.process.execute(cmd,die=False)
        # if rc==0:
        #     for line in out.split("\n"):
        #         if line=="":
        #             continue
        #         cmd="umount %s"%line.split(" ",1)[0]
        #         # print cmd
        #         j.sal.process.execute(cmd)

        # for name,passwd in self.secrets.iteritems():
        #     src="%s/download/%s"%(self.root,passwd)
        #     dest="%s/upload/%s"%(self.root,name)
        #     j.do.createDir(src)
        #     j.do.createDir(dest)
        #     # j.do.symlink(dest, src, overwriteTarget=True)

        #     cmd="mount --bind %s %s"%(src,dest)
        #     j.sal.process.execute(cmd)

    def start(self, background=False):
        self.saveConfig()
        self.prepareroles()

        j.sal.process.killProcessByPort(self.port)

        if background:
            cmd = "rsync --daemon --config=/etc/rsync/rsyncd.conf"
        else:
            cmd = "rsync -v --daemon --no-detach --config=/etc/rsync/rsyncd.conf"
        # print cmd

    def prepareroles(self):
        for catpath in self.distrdir.dirs():
            for path in catpath.walkdirs():
                rolepath = path.joinpath(".roles")
                if rolepath.exists():
                    # found dir with role
                    relpath = path.lstrip(catpath)
                    roles = rolepath.text().strip()
                    roles = [item.strip() for item in roles.split(",")]
                    for role in roles:
                        destdir = self.rolesdir.joinpath(role, catpath.basename(), relpath)
                        print(("link: %s->%s" % (path, destdir)))
                        path.symlink(destdir)
                        # j.do.createDir(destdir)
                        # for item in j.do.listFilesInDir(path, recursive=False, exclude=["*.pyc",".roles"], followSymlinks=False, listSymlinks=False):
                        #     relpath=j.do.pathRemoveDirPart(item,path)
                        #     destpathfile=j.do.joinPaths(destdir,relpath)
                        #     j.do.createDir(j.do.getDirName(destpathfile))
                        #     j.do.symlink(item, destpathfile, overwriteTarget=True)


class RsyncClient:

    """
    """

    def __init__(self):
        self.options = "-r --delete-after --modify-window=60 --compress --stats  --progress"

    def _pad(self, dest):
        if len(dest) != 0 and dest[-1] != "/":
            dest += "/"
        return dest

    def syncFromServer(self, src, dest):
        src = self._pad(src)
        dest = self._pad(dest)
        if src == dest:
            return
        j.tools.path.get(dest).mkdir_p()
        cmd = "rsync -av %s %s %s" % (src, dest, self.options)
        print(cmd)
        self._local.execute(cmd)

    def syncToServer(self, src, dest):
        src = self._pad(src)
        dest = self._pad(dest)
        if src == dest:
            return
        cmd = "rsync -av %s %s %s" % (src, dest, self.options)
        print(cmd)
        self._local.execute(cmd)


class RsyncClientSecret(RsyncClient):

    """
    """

    def __init__(self):
        self.options = "-r --delete-after --modify-window=60 --compress --stats --progress"

    def sync(self, src, dest):
        """
        can only sync from server to client
        """
        src = self._pad(src)
        dest = self._pad(dest)
        if src == dest:
            return
        cmd = "rsync %s %s %s" % (src, dest, self.options)
        print(cmd)
        self._local.execute(cmd)
