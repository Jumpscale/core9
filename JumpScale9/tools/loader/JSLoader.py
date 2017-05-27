from JumpScale9 import j
import os
import sys

# corepackages = """
# j.core.platformtype
# j.core.state
# j.sal.fs
# j.sal.process
# j.sal.fswalker
# j.tools.executorLocal
# j.tools.jsloader
# j.tools.tmux
# j.data.serializer
# j.data.text
# j.data.tags
# j.data.idgenerator
# j.data.time
# j.data.types
# j.clients.redis
# j.clients.git
# j.clients.email
# j.core.dirs
# j.core.application
# j.logger
# j.errorhandler
# """

GEN_START = """
from JumpScale9.core.JSBase import JSBase
import os
os.environ["LC_ALL"]='en_US.UTF-8'
"""

GEN = """
{{#locationerr}}
{{classname}}=JSBase
{{/locationerr}}

class {{jname}}:

    def __init__(self):
        {{#location}}
        self.__{{name}} = None
        {{/location}}

    {{#location}}
    @property
    def {{name}}(self):
        if self.__{{name}} == None:
            from {{importlocation}} import {{classname}} as {{classname}}
            self.__{{name}} = {{classname}}()
        return self.__{{name}}

    {{/location}}

"""

GEN2 = """
{{#locationerr}}
{{classname}}=JSBase
{{/locationerr}}

{{#location}}
from {{importlocation}} import {{classname}}
{{/location}}

class {{jname}}:

    def __init__(self):
        {{#location}}
        self.{{name}} = {{classname}}()
        {{/location}}

"""

GEN_END = """

class Jumpscale9():

    def __init__(self):
        {{#locations}}
        self.{{name}}={{name}}()
        {{/locations}}

j = Jumpscale9()
j.logger=j.core.logger
j.application=j.core.application
j.do = j.core.installtools
j.dirs = j.core.dirs
j.errorhandler = j.core.errorhandler
j.exceptions = j.core.errorhandler.exceptions
j.events = j.core.events

"""

import pystache


class JSLoader():

    def __init__(self):
        self.logger = j.logger.get("jsloader")
        self.__jslocation__ = "j.tools.jsloader"

    @property
    def autopip(self):
        return j.application.config["system"].get("autopip") == True

    def _installDevelopmentEnv(self):
        cmd = "apt-get install python3-dev libssl-dev -y"
        j.do.execute(cmd)
        j.do.execute("pip3 install pudb")

    def _findSitePath(self):
        res = ""
        for item in sys.path:
            if "/site-packages" in item:
                if res == "" or len(item) < len(res):
                    res = item
        if res != "":
            return res
        for item in sys.path:
            if "/dist-packages" in item:
                if res == "" or len(item) < len(res):
                    res = item
        if res == "":
            raise RuntimeError("Could not find sitepath")
        return res

    @property
    def initPath(self):
        path = self._findSitePath() + "/js9.py"
        # print("initpath:%s" % path)
        j.sal.fs.remove(path)
        # if not j.sal.fs.exists(path, followlinks=True):
        j.sal.fs.writeFile(filename=path, contents="from JumpScale9 import j\n", append=False)

        return path

    def _pip(self, item):
        rc, out, err = j.sal.process.execute("pip3 install %s" % item, die=False)
        if rc > 0:
            if "gcc' failed" in out:
                self._installDevelopmentEnv()
                rc, out, err = j.sal.process.execute("pip3 install %s" % item, die=False)
        if rc > 0:
            print("WARNING: COULD NOT PIP INSTALL:%s\n\n" % item)
        return rc

    def generate(self, path="", out="", moduleList={}, codecompleteOnly=False):
        # basedir = j.sal.fs.getParent(j.sal.fs.getDirName(j.sal.fs.getPathOfRunningFunction(j.application.__init__)))
        gigdir = os.environ.get('GIGDIR', '/root/gig')
        if out == "" or out is None:
            if codecompleteOnly:
                out = os.path.join(gigdir, "python_libs/js9.py")
            else:
                out = self.initPath
                print("* js9 path:%s" % out)
        else:
            self.initPath  # to make sure empty one is created

        content = GEN_START

        jlocations = {}
        jlocations["locations"] = []

        def removeDirPart(path):
            state = 0
            res = []
            for item in path.split("/"):
                if state == 0 and item.lower().find("jumpscale9") != -1:
                    state = 1
                if state == 1:
                    res.append(item)
            return "/".join(res)

        if moduleList == {}:
            moduleList = self.findModules(path=path)

        for jlocation, items in moduleList.items():
            if jlocation.strip() in ["", "j"]:
                continue
            res2 = {}
            res2["location"] = []
            res2["locationerr"] = []
            jname = jlocation.split(".")[1]
            res2["jname"] = jname
            toadd = {"name": jname}
            if toadd not in jlocations["locations"]:
                jlocations["locations"].append(toadd)
            res2["jlocation"] = jlocation

            for classfile, classname, item, importItems in items:
                res3 = {}
                res3["classname"] = classname
                res3["name"] = item
                importlocation = removeDirPart(classfile)[:-3].replace("//", "/").replace("/", ".")
                res3["importlocation"] = importlocation
                print ("**** in path {} generating {} classname {} file {}".format(path, importlocation, classname, classfile))

                try:
                    exec("from %s import %s" % (importlocation, classname))
                    res2["location"].append(res3)
                except ImportError as e:
                    print("\n\nCOULD NOT IMPORT:%s (%s)\n" % (importlocation, classname))
                    print("import error:\n%s\n" % e)
                    if importItems == []:
                        exec("from %s import %s" % (importlocation, classname))
                    else:
                        if not self.autopip:
                            continue

                        if j.application.config['system']['debug']:
                            pip_installed = self._pip_installed()
                            for item in importItems:
                                if item not in pip_installed:
                                    rc = self._pip(item)
                                    if rc > 0:
                                        if res3 not in res2["locationerr"]:
                                            res2["locationerr"].append(res3)
                                    else:
                                        print("pip install ok")
                                        if res3 not in res2["location"]:
                                            res2["location"].append(res3)
                            else:
                                if res3 not in res2["locationerr"]:
                                    res2["locationerr"].append(res3)

            if codecompleteOnly:
                content0 = pystache.render(GEN2, **res2)
            else:
                content0 = pystache.render(GEN, **res2)
            if len([item for item in content0.split("\n") if item.strip() != ""]) > 4:
                content += content0

            # print(res2)

        content += pystache.render(GEN_END, **jlocations)
        j.sal.fs.writeFile(out, content)

    def _pip_installed(self):
        "return the list of all installed pip packages"
        import json
        _, out, _ = j.sal.process.execute('pip3 list --format json', die=False, showout=False)
        pip_list = json.loads(out)
        return [p['name'] for p in pip_list]

    def findJumpscaleLocationsInFile(self, path):
        res = {}
        C = j.sal.fs.readFile(path)
        classname = None
        for line in C.split("\n"):
            if line.startswith("class "):
                classname = line.replace("class ", "").split(":")[0].split("(", 1)[0].strip()
            if line.find("self.__jslocation__") != -1:
                if classname is None:
                    raise RuntimeError(
                        "Could not find class in %s while loading jumpscale lib." % path)
                location = line.split("=", 1)[1].replace("\"", "").replace("'", "").strip()
                if location.find("self.__jslocation__") == -1:
                    if classname not in res:
                        res[classname] = {}
                    res[classname]["location"] = location
            if line.find("self.__imports__") != -1:
                if classname is None:
                    raise RuntimeError(
                        "Could not find class in %s while loading jumpscale lib." % path)
                importItems = line.split("=", 1)[1].replace("\"", "").replace("'", "").strip()
                importItems = [item.strip() for item in importItems.split(",") if item.strip() != ""]
                if classname not in res:
                    res[classname] = {}
                res[classname]["import"] = importItems

        return res

    # import json

    def findModules(self, path="", moduleList={}):
        """
        walk over code files & find locations for jumpscale modules

        return as dict
        """
        if path == "":
            path = j.sal.fs.getParent(j.sal.fs.getDirName(j.sal.fs.getPathOfRunningFunction(j.application.__init__)))

        result = moduleList

        self.logger.info("findmodules in %s" % path)

        for classfile in j.sal.fs.listFilesInDir(path, True, "*.py"):
            # print(classfile)
            basename = j.do.getBaseName(classfile)
            if basename.startswith("_"):
                continue
            # look for files starting with Capital
            if str(basename[0]) != str(basename[0].upper()):
                continue

            for classname, item in self.findJumpscaleLocationsInFile(classfile).items():
                if "location" in item:
                    location = item["location"]
                    if "import" in item:
                        importItems = item["import"]
                    else:
                        importItems = []

                    loc = ".".join(location.split(".")[:-1])
                    item = location.split(".")[-1]
                    if loc not in result:
                        result[loc] = []
                    result[loc].append((classfile, classname, item, importItems))
        return result


    def copyPyLibs(self):

        for item in sys.path:
            if item.endswith(".zip"):
                continue
            if "jumpscale" in item.lower() or "dynload" in item.lower():
                continue
            if 'home' in sys.path:
                continue
            if item.strip() in [".", ""]:
                continue
            if item[-1] != "/":
                item += "/"

            gigdir = os.environ.get('GIGDIR', '/root/gig')
            mounted_lib = os.path.join(gigdir, 'python_libs')

            if j.sal.fs.exists(item, followlinks=True):
                j.do.copyTree(item,
                              mounted_lib,
                              overwriteFiles=True,
                              ignoredir=['*.egg-info',
                                         '*.dist-info',
                                         "*JumpScale*",
                                         "*Tests*",
                                         "*tests*"],

                              ignorefiles=['*.egg-info',
                                           "*.pyc",
                                           "*.so",
                                           ],
                              rsync=True,
                              recursive=True,
                              rsyncdelete=False,
                              createdir=True)

        j.sal.fs.writeFile(filename=os.path.join(mounted_lib, "__init__.py"), contents="")

    def generatePlugins(self):
        moduleList = {}
        gigdir = os.environ.get('GIGDIR', '/root/gig')
        mounted_lib_path = os.path.join(gigdir, 'python_libs')

        plugins = j.application.config['plugins'] or []
        for plugin in plugins:
            print ('***************', plugin)
            for name, path in plugin.items():
                if j.sal.fs.exists(path, followlinks=True):
                    moduleList = self.findModules(path=path, moduleList=moduleList)
                    # link libs to location for hostos
                    j.do.copyTree(path,
                                  os.path.join(mounted_lib_path, name),
                                  overwriteFiles=True,
                                  ignoredir=['*.egg-info',
                                             '*.dist-info',
                                             "*JumpScale*",
                                             "*Tests*",
                                             "*tests*"],

                                  ignorefiles=['*.egg-info',
                                               "*.pyc",
                                               "*.so",
                                               ],
                                  rsync=True,
                                  recursive=True,
                                  rsyncdelete=True,
                                  createdir=True)

            # DO NOT AUTOPIP the deps are now installed while installing the libs
            j.application.config["system"]["autopip"] = False
            j.application.config["system"]["debug"] = True

            self.generate(path=path, moduleList=moduleList)
            self.generate(path=path, moduleList=moduleList, codecompleteOnly=True)
