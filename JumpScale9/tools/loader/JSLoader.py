from JumpScale9 import j
import os
import sys
import importlib
import json

GEN_START = """
from JumpScale9.core.JSBase import JSBase
import os
os.environ["LC_ALL"]='en_US.UTF-8'
from JumpScale9 import j
"""

GEN = """
{{#locationsubserror}}
{{classname}}=JSBase
{{/locationsubserror}}

class {{jname}}:

    def __init__(self):
        {{#locationsubs}}
        self._{{name}} = None
        {{/locationsubs}}

    {{#locationsubs}}
    @property
    def {{name}}(self):
        if self._{{name}} is None:
            # print("PROP:{{name}}")
            from {{importlocation}} import {{classname}} as {{classname}}
            self._{{name}} = {{classname}}()
        return self._{{name}}

    {{/locationsubs}}

{{#locationsubs}}
if not hasattr(j.{{jname}},"{{name}}"):
    j.{{jname}}._{{name}} = None
    j.{{jname}}.__class__.{{name}} = {{jname}}.{{name}}
{{/locationsubs}}


 """

GEN2 = """
{{#locationsubserror}}
{{classname}}=JSBase
{{/locationsubserror}}

{{#locationsubs}}
from {{importlocation}} import {{classname}}
{{/locationsubs}}

class {{jname}}:

    def __init__(self):
        {{#locationsubs}}
        self.{{name}} = {{classname}}()
        {{/locationsubs}}

"""


# Nothing needed at end for when used interactively
GEN_END = """

"""

# CODE GENERATION ONLY
GEN_END2 = """

class Jumpscale9():

    def __init__(self):
        {{#locations}}
        self.{{name}}={{name}}()
        {{/locations}}

j = Jumpscale9()

j.logger=j.core.logger
j.application=j.core.application
j.dirs = j.core.dirs
j.errorhandler = j.core.errorhandler
j.exceptions = j.core.errorhandler.exceptions
j.events = j.core.events
j.core.db = j.clients.redis.get4core()
from JumpScale9.tools.loader.JSLoader import JSLoader
j.tools.jsloader = JSLoader()

"""

import pystache


class JSLoader():

    def __init__(self):
        self.logger = j.logger.get("jsloader")
        self.__jslocation__ = "j.tools.jsloader"
        self.tryimport=False

    @property
    def autopip(self):
        return j.core.state.config["system"]["autopip"] in [True,"true","1",1]

    def _installDevelopmentEnv(self):
        cmd = "apt-get install python3-dev libssl-dev -y"
        j.sal.process.execute(cmd)
        j.sal.process.execute("pip3 install pudb")

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


    def processLocationSub(self,jlocationSubName,jlocationSubList):
        #import a specific location sub (e.g. j.clients.git)

        def removeDirPart(path):
            "only keep part after jumpscale9"
            state = 0
            res = []
            for item in path.split("/"):
                if state == 0 and item.lower().find("jumpscale9") != -1:
                    state = 1
                if state == 1:
                    res.append(item)

            if res[0] == res[1] and res[0].casefold().find("jumpscale9") !=-1:
                res.pop(0)
            return "/".join(res)

        classfile, classname, importItems = jlocationSubList

        generationParamsSub = {}
        generationParamsSub["classname"] = classname
        generationParamsSub["name"] = jlocationSubName
        importlocation = removeDirPart(classfile)[:-3].replace("//", "/").replace("/", ".")
        generationParamsSub["importlocation"] = importlocation

        rc=0

        ##TO BE FIXED TO DO THE IMPORT PROPERLY AND PASS RIGHT DETAILS
        # try:
        #     if self.try_import:
        #         exec("from %s import %s" % (importlocation, classname))
        # except ImportError as e:
        #     print("\n\nCOULD NOT IMPORT:%s (%s)\n" % (importlocation, classname))
        #     print("import error:\n%s\n" % e)
        #     if importItems == []:
        #         exec("from %s import %s" % (importlocation, classname))
        #     else:
        #         if not self.autopip:
        #             return

        #         if j.application.config['system']['debug']:
        #             pip_installed = self._pip_installed()
        #             for item in importItems:
        #                 if item not in pip_installed:
        #                     rc = self._pip(item)
        #                     if rc > 0:
        #                         if res3 not in generationParams["locationerr"]:
        #                             generationParams["locationerr"].append(res3)
        #                     else:
        #                         print("pip install ok")
        #                         if res3 not in generationParams["location"]:
        #                             generationParams["location"].append(res3)
        #             else:
        #                 if res3 not in generationParams["locationerr"]:
        #                     generationParams["locationerr"].append(res3)

        return rc,generationParamsSub


    def _generate(self):
        """
        generate's the jumpscale init file: js9
        as well as the one required for code generation

        to call:
        ipython -c 'from JumpScale9 import j;j.tools.jsloader.generate()'

        """
        # outCC = outpath for code completion
        # out = path for core of jumpscale

        j.tools.executorLocal.initEnv() #make sure the jumpscale toml file is set / will also link cmd files to system

        outCC = os.path.join(j.dirs.HOSTDIR,"autocomplete","js9.py")
        outJSON = os.path.join(j.dirs.HOSTDIR,"autocomplete","js9.json")
        j.sal.fs.createDir(os.path.join(j.dirs.HOSTDIR,"autocomplete"))

        out = self.initPath
        print("* js9 path:%s" % out)
        print("* js9 codecompletion path:%s" % outCC)
        self.initPath  # to make sure empty one is created

        content = GEN_START
        contentCC = GEN_START

        jlocations = {}
        jlocations["locations"] = []



        moduleList={}
        for name, path in j.core.state.configGet('plugins', {}).items():
            print("find modules in jumpscale for : '%s'" % path)
            if j.sal.fs.exists(path, followlinks=True):
                moduleList = self.findModules(path=path,moduleList=moduleList)
            else:
                raise RuntimeError("Could not find plugin dir:%s" % path)
                # try:
                #     mod_path = importlib.import_module(name).__path__[0]
                #     moduleList = self.findModules(path=mod_path)
                # except Exception as e:
                #     pass

        modlistout_json=json.dumps(moduleList,sort_keys=True,indent=4)
        j.sal.fs.writeFile(outJSON,modlistout_json)

        for jlocationRoot, jlocationRootDict in moduleList.items():

            #is per item under j e.g. j.clients

            if not jlocationRoot.startswith("j."):
                raise RuntimeError()

            jlocations["locations"].append({"name":jlocationRoot[2:]})

            generationParams = {}
            generationParams["locationsubserror"] = []
            generationParams["jname"] = jlocationRoot.split(".")[1].strip()                           #only name under j e.g. tools
            generationParams["locationsubs"]=[]


            #add per sublocation to the generation params
            for jlocationSubName, jlocationSubList in jlocationRootDict.items():

                rc,generationParamsSub=self.processLocationSub(jlocationSubName,jlocationSubList)

                if rc==0:
                    #need to add
                    generationParams["locationsubs"].append(generationParamsSub)

            #put the content in
            content0CC = pystache.render(GEN2, **generationParams)
            content0 = pystache.render(GEN, **generationParams)
            if len([item for item in content0CC.split("\n") if item.strip() != ""]) > 4:
                contentCC += content0CC
            if len([item for item in content0.split("\n") if item.strip() != ""]) > 4:
                content += content0

        contentCC += pystache.render(GEN_END2, **jlocations)
        content += pystache.render(GEN_END, **jlocations)


        j.sal.fs.writeFile(outCC, contentCC)

        j.sal.fs.writeFile(out, content)


    def _pip_installed(self):
        "return the list of all installed pip packages"
        import json
        _, out, _ = j.sal.process.execute('pip3 list --format json', die=False, showout=False)
        pip_list = json.loads(out)
        return [p['name'] for p in pip_list]

    def findJumpscaleLocationsInFile(self, path):
        """
        returns:
            [$classname]["location"] =$location
            [$classname]["import"] = $importitems
        """
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

    def findModules(self, path, moduleList=None):
        """
        walk over code files & find locations for jumpscale modules

        return as dict

        format

        [$rootlocationname][$locsubname]=(classfile,classname,importItems)

        """
        if moduleList is None:
            moduleList = {}

        self.logger.info("findmodules in %s" % path)

        for classfile in j.sal.fs.listFilesInDir(path, True, "*.py"):
            # print(classfile)
            basename = j.sal.fs.getBaseName(classfile)
            if basename.startswith("_"):
                continue
            if "jsloader" in basename.lower() or "actioncontroller" in basename.lower():
                continue
            # look for files starting with Capital
            if str(basename[0]) != str(basename[0].upper()):
                continue

            for classname, item in self.findJumpscaleLocationsInFile(classfile).items():
                #item has "import" & "location" as key in the dict
                if "location" in item:
                    location = item["location"]
                    if "import" in item:
                        importItems = item["import"]
                    else:
                        importItems = []

                    locRoot = ".".join(location.split(".")[:-1])
                    locSubName = location.split(".")[-1]
                    if locRoot not in moduleList:
                        moduleList[locRoot] = {}
                    moduleList[locRoot][locSubName]=(classfile,classname,importItems)
        return moduleList

    def removeEggs(self):
        for key, path in j.clients.git.getGitReposListLocal(account="jumpscale").items():
            for item in [item for item in j.sal.fs.listDirsInDir(path) if item.find("egg-info") != -1]:
                j.sal.fs.removeDirTree(item)

    def copyPyLibs(self, autocompletepath=None):
        """
        this looks for python libs (non jumpscale) and copies them to our gig lib dir
        which can be use outside of docker for e.g. code completiong
        """
        if autocompletepath is None:
            autocompletepath=os.path.join(j.dirs.HOSTDIR,"autocomplete")
            j.sal.fs.createDir(autocompletepath)

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

            if j.sal.fs.exists(item, followlinks=True):
                j.sal.fs.copyDirTree(item,
                              autocompletepath,
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

        j.sal.fs.writeFile(filename=os.path.join(autocompletepath, "__init__.py"), contents="")

    def generate(self,autocompletepath=None):
        """
        """

        if j.dirs.HOSTDIR=="":
            raise RuntimeError("dirs in your jumpscale9.toml not ok, hostdir cannot be empty")

        if autocompletepath==None:
            autocompletepath=os.path.join(j.dirs.HOSTDIR,"autocomplete")
            j.sal.fs.createDir(autocompletepath)

        for name, path in j.core.state.configGet('plugins', {}).items():
            if j.sal.fs.exists(path, followlinks=True):
                # link libs to location for hostos
                j.sal.fs.copyDirTree(path,
                                os.path.join(autocompletepath, name),
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


        j.sal.fs.touch( os.path.join(j.dirs.HOSTDIR, 'autocomplete',"__init__.py"))

        # DO NOT AUTOPIP the deps are now installed while installing the libs
        j.core.state.configSetInDictBool("system", "autopip", False)
        # j.application.config["system"]["debug"] = True

        self._generate()
