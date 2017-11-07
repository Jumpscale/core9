from js9 import j


class CodeDirs():
    def __init__(self):
        self.path = j.dirs.CODEDIR

        self.load()

    def load(self):
        data=j.core.state.stateGetFromDict("develop","codedirs","")
        self.tree = j.data.treemanager.get(data=data)
        self.tree.setDeleteState() #set all on deleted state
        types = j.sal.fs.listDirsInDir(j.dirs.CODEDIR, False, True)
        # types2 = []
        for ttype in types:
            self.tree.set(ttype, cat="type")
            # types2.append(currootTree)
            if ttype[0]=="." or ttype[0]=="_":
                continue
            accounts = j.sal.fs.listDirsInDir("%s/%s" % (j.dirs.CODEDIR, ttype), False, True)
            for account in accounts:
                if account[0]=="." or account[0]=="_":
                    continue
                path = "%s.%s" % (ttype, account)
                self.tree.set(path, cat="account")
                repos = j.sal.fs.listDirsInDir("%s/%s/%s" % (j.dirs.CODEDIR, ttype, account), False, True)
                for repo in repos:
                    if not repo.startswith(".") and not account.startswith("."):
                        path = "%s.%s.%s" % (ttype, account, repo)
                        self.tree.set(path, cat="repo", item=CodeDir(self, ttype, account, repo))

        self.tree.removeDeletedItems() #make sure that the ones no longer there are deleted

    # @property
    # def codedirs(self):
    #     return self.tree.find("", getItems=True)

    # def codeDirsGetAsStringList(self):
    #     res = []
    #     for codedir in self.codedirs:
    #         res.append(str(codedir))
    #     res.sort()
    #     return res


    def getActiveCodeDirs(self):
        res=[]
        for item in self.tree.find(cat="repo"):
            if item.selected:
                # path=j.dirs.CODEDIR+"/"+item.path.replace(".","/")
                ttype, account, name=item.path.split(".")
                res.append(CodeDir(self,ttype=ttype, account=account, name=name))
        return res

    def codeDirGet(self, reponame, account=None, die=True):
        res = []
        for item in self.self.tree.find("", getItems=True):
            if account is None or item.account == account:
                if item.name == reponame:
                    print(codedirget in develtools)
                    from IPython import embed;embed(colors='Linux')
                    CodeDir(self,ttype,account,reponame)
                    res.append(item)
        if len(res) == 0:
            if die is False:
                return None
            raise j.exceptions.Input("did not find codedir: %s:%s" % (account, reponame))
        if len(res) > 1:
            raise j.exceptions.Input("found more than 1 codedir: %s:%s" % (account, reponame))

        return res[0]

    def save(self):
        j.core.state.stateSetInDict("develop","codedirs", self.tree.dumps())


    # def selectionGet(self):
    #     coderepos = j.core.state.configGetFromDict("developtools", "coderepos", default=[])
    #     res = []
    #     for account, reponame in coderepos:
    #         res.append(self.codeDirGet(account=account, reponame=reponame))
    #     return res

    # def _selectionGet(self):
    #     """
    #     will return as position in list e.g. [2,3] would mean position 3&4 in sorted list of the coderepo's
    #     """
    #     sel0 = self.codeDirsGetAsStringList()
    #     sel = [str(item) for item in self.selectionGet()]
    #     res = []
    #     for item in sel:
    #         # is string in selection
    #         try:
    #             col = sel0.index(item)
    #             # means it exists
    #             res.append(col)
    #         except:
    #             pass
    #     return res
    #
    # def _selectionSet(self, selection):
    #     slist = self.codeDirsGetAsStringList()
    #     res = []
    #     for item in selection:
    #         selectedItem = slist[item]
    #         account, name = selectedItem.split(":", 1)
    #         account = account.strip()
    #         name = name.strip()
    #         res.append([account, name])
    #     j.core.state.configSetInDict("developtools", "coderepos", res)

    # def selectionSet(self, codedir):
    #     """
    #     will set the code dir as selected in the jumpscale config file
    #     """
    #     if not self.selectionExists(codedir):
    #         items = j.core.state.configGetFromDict("developtools", "coderepos", default=[])
    #         items.append([codedir.account, codedir.name])
    #         j.core.state.configSetInDict("developtools", "coderepos", items)
    #         j.core.state.configSave()
    #
    # def selectionExists(self, codedir):
    #     return str(codedir) in self.codeDirsGetAsStringList()

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return ("%s"%self.tree)


class CodeDir():
    def __init__(self, codedirs, ttype, account, name):
        self.path = j.sal.fs.joinPaths(codedirs.path, ttype, account, name)
        self.account = account
        self.type = ttype
        self.name = name

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return ("%-22s :    %s" % (self.account, self.name))
