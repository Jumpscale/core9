from .GitClient import GitClient
from JumpScale9 import j
import os


class GitFactory:

    def __init__(self):
        self.logger = j.logger.get('j.clients.git')
        self.pullGitRepo = j.do.pullGitRepo
        self.getGitRepoArgs = j.do.getGitRepoArgs
        self.rewriteGitRepoUrl = j.do.rewriteGitRepoUrl
        self.getGitBranch = j.do.getGitBranch
        self.__jslocation__ = "j.clients.git"

    def parseUrl(self, url):
        """
        @return (repository_host, repository_type, repository_account, repository_name, repository_url,branch,gitpath, relpath)

        example Input
        - https://github.com/Jumpscale/NOS/blob/master/specs/NOS_1.0.0.md
        - https://github.com/Jumpscale/jumpscale_core9/blob/8.1.2/lib/JumpScale/tools/docgenerator/macros/dot.py
        - https://github.com/Jumpscale/jumpscale_core9/tree/8.2.0/lib/JumpScale/tools/docgenerator/macros
        - https://github.com/Jumpscale/jumpscale_core9/tree/master/lib/JumpScale/tools/docgenerator/macros

        """

        repository_host, repository_type, repository_account, repository_name, repository_url = self.rewriteGitRepoUrl(
            url)

        url_end = ""
        if "tree" in repository_url:
            # means is a directory
            repository_url, url_end = repository_url.split("tree")
        elif "blob" in repository_url:
            # means is a directory
            repository_url, url_end = repository_url.split("blob")
        if url_end != "":
            url_end = url_end.strip("/")
            if url_end.find("/") == -1:
                path = ""
                branch = url_end
                if branch.endswith(".git"):
                    branch = branch[:-4]
            else:
                branch, path = url_end.split("/", 1)
                if path.endswith(".git"):
                    path = path[:-4]
        else:
            path = ""
            branch = ""

        a, b, c, d, dest, e = self.getGitRepoArgs(url)

        if "tree" in dest:
            # means is a directory
            gitpath, ee = dest.split("tree")
        elif "blob" in repository_url:
            # means is a directory
            gitpath, ee = dest.split("blob")
        else:
            gitpath = dest

        return (
            repository_host,
            repository_type,
            repository_account,
            repository_name,
            repository_url,
            branch,
            gitpath,
            path)

    def getContentInfoFromURL(self, url):
        """
        @return (giturl,gitpath,relativepath)

        example Input
        - https://github.com/Jumpscale/NOS/blob/master/specs/NOS_1.0.0.md
        - https://github.com/Jumpscale/jumpscale_core9/blob/8.1.2/lib/JumpScale/tools/docgenerator/macros/dot.py
        - https://github.com/Jumpscale/jumpscale_core9/tree/8.2.0/lib/JumpScale/tools/docgenerator/macros
        - https://github.com/Jumpscale/jumpscale_core9/tree/master/lib/JumpScale/tools/docgenerator/macros

        """
        repository_host, repository_type, repository_account, repository_name, repository_url, branch, gitpath, relpath = j.clients.git.parseUrl(
            url)
        rpath = j.do.joinPaths(gitpath, relpath)
        if not j.do.exists(rpath, followlinks=True):
            j.clients.git.pullGitRepo(repository_url, branch=branch)
        if not j.do.exists(rpath, followlinks=True):
            raise j.exceptions.Input(message="Did not find path in git:%s" %
                                     rpath, level=1, source="", tags="", msgpub="")

        return (repository_url, gitpath, relpath)

    def pullGitRepoSubPath(self, urlOrPath):
        """
        @return path of the content found

        will find the right branch & will do a pull

        example Input
        - https://github.com/Jumpscale/NOS/blob/master/specs/NOS_1.0.0.md
        - https://github.com/Jumpscale/jumpscale_core9/blob/8.1.2/lib/JumpScale/tools/docgenerator/macros/dot.py
        - https://github.com/Jumpscale/jumpscale_core9/tree/8.2.0/lib/JumpScale/tools/docgenerator/macros
        - https://github.com/Jumpscale/jumpscale_core9/tree/master/lib/JumpScale/tools/docgenerator/macros

        """
        if not j.do.exists(urlOrPath, followlinks=True):
            repository_url, gitpath, relativepath = self.getContentInfoFromURL(urlOrPath)
        else:
            repository_host, repository_type, repository_account, repository_name, repository_url, branch, gitpath, relativepath = j.clients.git.parseUrl(
                urlOrPath)
            j.clients.git.pullGitRepo(repository_url, branch=branch)  # to make sure we pull the info

        path = j.do.joinPaths(gitpath, relativepath)
        return path

    def getContentPathFromURLorPath(self, urlOrPath):
        """

        @return path of the content found, will also do a pull to make sure git repo is up to date

        example Input
        - https://github.com/Jumpscale/NOS/blob/master/specs/NOS_1.0.0.md
        - https://github.com/Jumpscale/jumpscale_core9/blob/8.1.2/lib/JumpScale/tools/docgenerator/macros/dot.py
        - https://github.com/Jumpscale/jumpscale_core9/tree/8.2.0/lib/JumpScale/tools/docgenerator/macros
        - https://github.com/Jumpscale/jumpscale_core9/tree/master/lib/JumpScale/tools/docgenerator/macros

        """
        if j.do.exists(urlOrPath, followlinks=True):

            return urlOrPath
        repository_url, gitpath, relativepath = self.getContentInfoFromURL(urlOrPath)
        path = j.do.joinPaths(gitpath, relativepath)
        return path

    def get(self, basedir="", check_path=True):
        """
        PLEASE USE SSH, see http://gig.gitbooks.io/jumpscale/content/Howto/how_to_use_git.html for more details
        """
        if basedir == "":
            basedir = j.do.getcwd()
        return GitClient(basedir, check_path=check_path)

    def find(self, account=None, name=None, interactive=False, returnGitClient=False):  # NOQA
        """
        walk over repo's known on system
        2 locations are checked
            ~/code
            /opt/code
        """
        if name is None:
            name = ""
        if account is None:
            account = ""

        accounts = []
        accounttofind = account

        def checkaccount(account):
            # print accounts
            # print "%s %s"%(account,accounttofind)
            if account not in accounts:
                if accounttofind.find("*") != -1:
                    if accounttofind == "*" or account.startswith(accounttofind.replace("*", "")):
                        accounts.append(account)
                elif accounttofind != "":
                    if account.lower().strip() == accounttofind.lower().strip():
                        accounts.append(account)
                else:
                    accounts.append(account)
            # print accountsunt in accounts
            return account in accounts

        def _getRepos(codeDir, account=None, name=None):  # NOQA
            """
            @param interactive if interactive then will ask to select repo's out of the list
            @para returnGitClient if True will return gitclients as result

            returns (if returnGitClient)
            [[type,account,reponame,path]]

            the type today is git or github today
            all std git repo's go to git

            ```
            #example
            [['github', 'docker', 'docker-py', '/opt/code/github/docker/docker-py'],
            ['github', 'jumpscale', 'docs', '/opt/code/github/jumpscale/docs']]
            ```

            """
            repos = []
            for top in j.do.listDirsInDir(codeDir, recursive=False,
                                              dirNameOnly=True, findDirectorySymlinks=True):
                for account in j.do.listDirsInDir("%s/%s" % (j.dirs.CODEDIR, top), recursive=False,
                                                      dirNameOnly=True, findDirectorySymlinks=True):
                    if checkaccount(account):
                        accountdir = "%s/%s/%s" % (j.dirs.CODEDIR,
                                                   top, account)
                        if j.do.exists(path="%s/.git" % accountdir):
                            raise j.exceptions.RuntimeError(
                                "there should be no .git at %s level" % accountdir)
                        else:
                            for reponame in j.do.listDirsInDir("%s/%s/%s" % (j.dirs.CODEDIR, top, account),
                                                                   recursive=False, dirNameOnly=True,
                                                                   findDirectorySymlinks=True):
                                repodir = "%s/%s/%s/%s" % (
                                    j.dirs.CODEDIR, top, account, reponame)
                                if j.do.exists(path="%s/.git" % repodir):
                                    if name.find("*") != -1:
                                        if name == "*" or reponame.startswith(name.replace("*", "")):
                                            repos.append(
                                                [top, account, reponame, repodir])
                                    elif name != "":
                                        if reponame.lower().strip() == name.lower().strip():
                                            repos.append(
                                                [top, account, reponame, repodir])
                                    else:
                                        repos.append(
                                            [top, account, reponame, repodir])
            return repos

        j.do.createDir(j.do.joinPaths(os.getenv("HOME"), "code"))
        repos = _getRepos(j.dirs.CODEDIR, account, name)
        repos += _getRepos(j.do.joinPaths(os.getenv("HOME"),
                                              "code"), account, name)

        accounts.sort()

        if interactive:
            result = []
            if len(repos) > 20:
                print("Select account to choose from, too many choices.")
                accounts = j.tools.console.askChoiceMultiple(accounts)

            repos = [item for item in repos if item[1] in accounts]

            # only ask if * in name or name not specified
            if name.find("*") == -1 or name is None:
                repos = j.tools.console.askArrayRow(repos)

        result = []
        if returnGitClient:
            for top, account, reponame, repodir in repos:
                cl = self.get(repodir)
                result.append(cl)
        else:
            result = repos

        return result

    def findGitPath(self, path):
        while path != "":
            if j.do.exists(path=j.do.joinPaths(path, ".git")):
                return path
            path = j.do.getParent(path)
        raise j.exceptions.Input("Cannot find git path in:%s" % path)

    def parseGitConfig(self, repopath):
        """
        @param repopath is root path of git repo
        @return (giturl,account,reponame,branch,login,passwd)
        login will be ssh if ssh is used
        login & passwd is only for https
        """
        path = j.do.joinPaths(repopath, ".git", "config")
        if not j.do.exists(path=path):
            raise RuntimeError("cannot find %s" % path)
        config = j.do.readFile(path)
        state = "start"
        for line in config.split("\n"):
            line2 = line.lower().strip()
            if state == "remote":
                if line.startswith("url"):
                    url = line.split("=", 1)[1]
                    url = url.strip().strip("\"").strip()
            if line2.find("[remote") != -1:
                state = "remote"
            if line2.find("[branch"):
                branch = line.split(" \"")[1].strip("]\" ").strip("]\" ").strip("]\" ")

    def getGitReposListLocal(self, provider="", account="", name="", errorIfNone=True):
        repos = {}
        for top in j.do.listDirsInDir(
                j.dirs.CODEDIR,
                recursive=False,
                dirNameOnly=True,
                findDirectorySymlinks=True):
            if provider != "" and provider != top:
                continue
            for accountfound in j.do.listDirsInDir("%s/%s" % (j.dirs.CODEDIR, top),
                                                       recursive=False, dirNameOnly=True, findDirectorySymlinks=True):
                if account != "" and account != accountfound:
                    continue
                accountfounddir = "/%s/%s/%s" % (j.dirs.CODEDIR, top, accountfound)
                for reponame in j.do.listDirsInDir(
                    "%s/%s/%s" %
                    (j.dirs.CODEDIR,
                     top,
                     accountfound),
                    recursive=False,
                    dirNameOnly=True,
                        findDirectorySymlinks=True):
                    if name != "" and name != reponame:
                        continue
                    repodir = "%s/%s/%s/%s" % (j.dirs.CODEDIR, top, accountfound, reponame)
                    if j.do.exists(path="%s/.git" % repodir):
                        repos[reponame] = repodir
        if len(list(repos.keys())) == 0:
            raise RuntimeError("Cannot find git repo '%s':'%s':'%s'" % (provider, account, name))
        return repos

    def pushGitRepos(self, message, name="", update=True, provider="", account=""):
        """
        if name specified then will look under code dir if repo with path can be found
        if not or more than 1 there will be error
        @param provider e.g. git, github
        """
        # TODO: make sure we use gitlab or github account if properly filled in
        repos = self.getGitReposListLocal(provider, account, name)
        for name, path in list(repos.items()):
            print(("push git repo:%s" % path))
            cmd = "cd %s;git add . -A" % (path)
            j.sal.process.executeInteractive(cmd)
            cmd = "cd %s;git commit -m \"%s\"" % (path, message)
            j.sal.process.executeInteractive(cmd)
            branch = self.getGitBranch(path)
            if update:
                cmd = "cd %s;git pull origin %s" % (path, branch)
                j.sal.process.executeInteractive(cmd)
            cmd = "cd %s;git push origin %s" % (path, branch)
            j.sal.process.executeInteractive(cmd)

    def updateGitRepos(self, provider="", account="", name="", message=""):
        repos = self.getGitReposListLocal(provider, account, name)
        for name, path in list(repos.items()):
            print(("push git repo:%s" % path))
            branch = self.getGitBranch(path)
            cmd = "cd %s;git add . -A" % (path)
            j.sal.process.executeInteractive(cmd)
            cmd = "cd %s;git commit -m \"%s\"" % (path, message)
            j.sal.process.executeInteractive(cmd)
            cmd = "cd %s;git pull origin %s" % (path, branch)
            j.sal.process.executeInteractive(cmd)

    def changeLoginPasswdGitRepos(self, provider="", account="", name="",
                                  login="", passwd="", ssh=True, pushmessage=""):
        """
        walk over all git repo's found in account & change login/passwd
        """
        if ssh is False:
            for reponame, repopath in list(self.getGitReposListLocal(provider, account, name).items()):
                import re
                configpath = "%s/.git/config" % repopath
                text = j.do.readFile(configpath)
                text2 = text
                for item in re.findall(re.compile(r'//.*@%s' % provider), text):
                    newitem = "//%s:%s@%s" % (login, passwd, provider)
                    text2 = text.replace(item, newitem)
                if text2.strip() != text:
                    j.do.writeFile(configpath, text2)
        else:
            for reponame, repopath in list(self.getGitReposListLocal(provider, account, name).items()):
                configpath = "%s/.git/config" % repopath
                text = j.do.readFile(configpath)
                text2 = ""
                change = False
                for line in text.split("\n"):
                    if line.replace(" ", "").find("url=") != -1:
                        # print line
                        if line.find("@git") == -1:
                            # print 'REPLACE'
                            provider2 = line.split("//", 1)[1].split("/", 1)[0].strip()
                            account2 = line.split("//", 1)[1].split("/", 2)[1]
                            name2 = line.split("//", 1)[1].split("/", 2)[2].replace(".git", "")
                            line = "\turl = git@%s:%s/%s.git" % (provider2, account2, name2)
                            change = True
                        # print line
                    text2 += "%s\n" % line

                if change:
                    # print text
                    # print "===="
                    # print text2
                    # print "++++"
                    print(("changed login/passwd/git on %s" % configpath))
                    j.do.writeFile(configpath, text2)

        if pushmessage != "":
            self.pushGitRepos(pushmessage, name=name, update=True, provider=provider, account=account)
