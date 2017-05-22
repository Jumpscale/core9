from js9 import j

from .NodeBase import NodeBase
from .MonitorTools import MonitorTools
from .PerfTestTools import *
from .MonitorTools import *
from .Disk import *


class NodeNas(NodeBase):

    def __init__(self, ipaddr, sshport=22, nrdisks=0, fstype="xfs", debugdisk="", name=""):
        """
        nbrdisk: if > 0, looks for default disks  at /dev/sdx
        e.g : if nbrdisk=3, use disks /dev/sdb, /dev/sdc, /dev/sdd
        """
        super(NodeNas, self).__init__(ipaddr=ipaddr, sshport=sshport, role="nas", name=name)

        self.debugdisk = debugdisk
        if self.debugdisk != "":
            self.debug = True
        self.nrdisks = int(nrdisks)
        self.disks = []
        self.fstype = fstype

        self.perftester = PerfTestTools(self)

        if self.nrdisks > 0:
            self.autoInitDisks()

    def ready(self):
        """
        Call this methods when all disks are ready.
        So after
        """
        disks = [item.devnameshort for item in self.disks]
        self.startMonitor(disks=disks)

        self.initTest()

    def initTest(self):
        screens = []
        for i in range(self.nrdisks):
            screens.append("ptest%s" % i)
        if len(screens) > 0:
            self.prepareTmux("perftest", screens)

    def autoInitDisks(self):
        if self.debug is False:
            diskids = "bcdefghijklmnopqrstuvwxyz"
            for i in range(self.nrdisks):
                diskname = "/dev/vd%s" % diskids[i]
                disk = Disk(diskname, node=self, disknr=i + 1, screenname="ptest%s" % (i))
                self.disks.append(disk)

            # check mounts
            print("check disks are mounted and we find them all")
            result = self.ssh.run("mount")
            for line in result.split("\n"):
                if line.find(" on ") != -1 and line.startswith("/dev/v"):  # and line.find(self.fstype)!=-1:
                    # found virtual disk
                    devname = line.split(" ")[0]
                    if devname.startswith("/dev/vda"):
                        continue
                    disk = self.findDisk(devname)
                    if disk is not None:
                        disk.mounted = True
                        disk.mountpath = line.split(" on ")[1].split(" type")[0].strip()
                        disk.node = self

            for disk in self.disks:
                if disk.mounted is False:
                    disk.initDisk(fs=self.fstype)

                    # raise j.exceptions.RuntimeError("Could not find all disks mounted, disk %s not mounted on %s"%(disk,self))

            print("all disks mounted")

        else:
            i = 0
            disk = Disk(self.debugdisk)
            self.disks.append(disk)
            disk.screenname = "ptest%s" % i
            disk.disknr = i + 1
            disk.mountpath = "/tmp/dummyperftest/%s" % i
            j.do.createDir(disk.mountpath)
            disk.node = self

    def createLoopDev(self, size, backend_file):
        """
        Create a file at backend_file location, then bind a create a loop device with backend_file as backend.
        usefull when monitoring virtual Filesystem that doesn't have real block device.

        size : size of the disk to create in MB
        backend_file : path to the backend_file the loop device will use
        """
        def checkLoopExists(lines):
            dev = ""
            for line in lines.splitlines():
                if line.find(backend_file):
                    dev = line.split(':')[0]
                    break
            return dev

        # test if loop device existe already
        cmd = "losetup -a"
        out = self.execute(cmd, env={}, dieOnError=False, report=True)
        dev = checkLoopExists(out)
        if dev == "":
            # dont' exists yet
            # create backend file
            count = int(size) / 4
            cmd = 'dd if=/dev/zero of=%s bs=4MB count=%d' % (backend_file, int(count))
            print("creation of the backend file %s, size %sMB. This can takes a while" % (backend_file, size))
            self.execute(cmd, env={}, dieOnError=False, report=True)

            # create loop device
            print("create loop device")
            cmd = 'losetup -f %s;losetup -a' % backend_file
            out = self.execute(cmd, env={}, dieOnError=True, report=True)
            dev = checkLoopExists(out)
            if dev == '':
                raise j.exceptions.RuntimeError("fail to create loop dev on %s" % backend_file)

        # add new dev to known disks
        diskNr = len(self.disks)
        disk = Disk(dev, node=self, disknr=diskNr, screenname="ptest%s" % diskNr)
        self.disks.append(disk)
        self.nrdisks += 1

        disk.initDisk(fs=self.fstype)

    def findDisk(self, devname):
        for disk in self.disks:
            if disk.devname == devname:
                return disk
        return None
