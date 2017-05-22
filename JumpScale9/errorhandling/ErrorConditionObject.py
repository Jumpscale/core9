
try:
    import pygments.lexers
    from pygments.formatters import get_formatter_by_name
    pygmentsObj = True
except BaseException:
    pygmentsObj = False

import copy
import unicodedata
from JumpScale9 import j
import sys
import colored_traceback
colored_traceback.add_hook(always=True)
import traceback

LEVELMAP = {1: 'CRITICAL', 2: 'WARNING', 3: 'INFO', 4: 'DEBUG'}


class ErrorConditionObject(BaseException):
    """
    @param type #BUG,INPUT,MONITORING,OPERATIONS,PERFORMANCE,UNKNOWN
    @param level #1:critical, 2:warning, 3:info see j.enumerators.ErrorConditionLevel
    """

    def __init__(self, ddict={}, msg="", msgpub="", category="", level=1,
                 type="UNKNOWN", tb=None, data=None, tags="", limit=30):
        if ddict != {}:
            self.__dict__ = ddict
        else:

            btkis, filename0, linenr0, func0 = j.errorhandler.getErrorTraceKIS(
                tb=tb)

            # if len(btkis)>1:
            #     self.backtrace=self.getBacktrace(btkis,filename0,linenr0,func0)

            # is for default case where there is no redis
            self.guid = j.data.idgenerator.generateGUID()
            self.category = category  # is category in dot notation
            self.errormessage = msg
            self.errormessagePub = msgpub
            # 1:critical, 2:warning, 3:info see
            # j.enumerators.ErrorConditionLevel.
            self.level = int(level)
            self.data = data
            self.tags = tags
            self._limit = limit

            if len(btkis) > 0:
                self.code = btkis[-1][0]
                self.funcname = func0
                self.funcfilename = filename0
                self.funclinenr = linenr0
            else:
                self.code = ""
                self.funcname = ""
                self.funcfilename = ""
                self.funclinenr = ""

            self.appname = j.application.appname  # name as used by application
            self.gid = j.application.whoAmI.gid
            self.nid = j.application.whoAmI.nid
            # if hasattr(j, 'core') and hasattr(j.core, 'grid') and hasattr(j.core.grid, 'aid'):
            #     self.aid = j.core.grid.aid
            self.pid = j.application.whoAmI.pid
            self.jid = 0
            self.masterjid = 0

            self.epoch = j.data.time.getTimeEpoch()
            # BUG,INPUT,MONITORING,OPERATIONS,PERFORMANCE,UNKNOWN
            self.type = str(type)

            self._traceback = ""

            if tb is not None:
                self.tb = tb

            self.tags = ""  # e.g. machine:2323
            self.state = "NEW"  # ["NEW","ALERT","CLOSED"]

            self.lasttime = 0  # last time there was an error condition linked to this alert
            self.closetime = 0  # alert is closed, no longer active

            self.occurrences = 1  # nr of times this error condition happened

            self.uniquekey = ""

    @property
    def traceback(self):
        return self._traceback

    def tracebackSet(self, tb, exceptionObject):

        # tb=e.__traceback__
        type = None
        tblist = traceback.format_exception(type, exceptionObject, tb)

        self._traceback = ""

        ignore = ["click/core.py", "ipython"]

        if self._limit and len(tblist) > self._limit:
            tblist = tblist[-self._limit:]

        for item in tblist:
            for ignoreitem in ignore:
                if item.find(ignoreitem) != -1:
                    item = ""
            if item != "":
                self._traceback += "%s" % item

    def printTraceback(self):
        if pygmentsObj:
            formatter = pygments.formatters.Terminal256Formatter(
                style=pygments.styles.get_style_by_name("vim"))
            lexer = pygments.lexers.get_lexer_by_name(
                "pytb", stripall=True)  # pytb
            tb_colored = pygments.highlight(self.traceback, lexer, formatter)
            sys.stdout.write(tb_colored)
        else:
            print(self.traceback)

    @property
    def key(self):
        """
        return unique key for object, is used to define unique id
        """
        if self.category != "":
            C = "%s_%s_%s_%s_%s_%s_%s_%s" % (self.gid, self.nid, self.category, self.level,
                                             self.funcname, self.funcfilename, self.appname, self.type)
        else:
            C = "%s_%s_%s_%s_%s_%s_%s_%s" % (self.gid, self.nid, self.errormessage,
                                             self.level, self.funcname, self.funcfilename, self.appname, self.type)
        self.uniquekey = j.data.hash.md5_string(C)
        return self.uniquekey

    def _toAscii(self):

        def _toAscii(s):
            doagain = False
            try:
                if isinstance(s, str):
                    s = unicodedata.normalize('NFKD', s)
                return s.encode('utf-8', 'ignore')
            except Exception as e:
                # try default
                doagain = True
            if doagain:
                try:
                    s = str(s)
                except Exception as e2:
                    print("BUG in toascii in ErrorConditionObject")
                    import ipdb

        self.errormessage = _toAscii(self.errormessage)
        self.errormessagePub = _toAscii(self.errormessagePub)
        # self.errormessagePub=_toAscii(self.errormessagePub)
        self._traceback = _toAscii(self._traceback)
        # self.backtraceDetailed=_toAscii(self.backtraceDetailed)

        self.errormessage = self.errormessage.decode()
        self.errormessagePub = self.errormessagePub.decode()
        self._traceback = self._traceback.decode()

    def process(self):
        self._toAscii()

        if self.type in ["INPUT", "MONITORING", "OPERATIONS", "PERFORMANCE"] and j.application.debug is False:
            self.tb = ""
            self.code = ""
            self.backtrace = ""
            self.backtraceDetailed = ""

        # types=["INPUT","MONITORING","OPERATIONS","PERFORMANCE","BUG","UNKNOWN"]
        # if not self.type in types:
        #     j.events.inputerror_warning("Errorcondition was thrown with wrong type.\n%s"%str(self),"eco.check.type")

        if not j.data.types.int.check(self.level):
            try:
                self.level = int(self.level)
            except BaseException:
                pass
            if not j.data.types.int.check(param.level):
                self.level = 1
                j.events.inputerror_warning("Errorcondition was thrown with wrong level, needs to be int.\n%s" % str(
                    self.errormessage), "eco.check.level")

        if self.level > 4:
            raise RuntimeError(
                "Errorcondition was thrown with wrong level, needs to be max 4.")
            # j.events.inputerror_warning("Errorcondition was thrown with wrong level, needs to be max 4.\n%s"%str(self.errormessage),"eco.check.level")
            self.level = 4

        res = j.errorhandler._send2Redis(self)
        if res is not None:
            self.__dict__ = res

    def toJson(self):
        data = self.__dict__.copy()
        data.pop('tb', None)
        return j.data.serializer.json.dumps(data)

    def __str__(self):
        self.printTraceback()
        # self._toAscii()
        # content = "\n\n***ERROR***\n"
        # if self.type != "UNKNOWN":
        #     content += "  type/level: %s/%s\n" % (self.type, self.level)
        # if self.tags!="":
        #     content+="tags: %s\n" % self.tags
        # content += "%s\n" % self.errormessage
        # if self.errormessagePub != "" and self.errormessagePub is not None:
        #     content += "errorpub:\n%s\n\n" % self.errormessagePub
        return self.errormessage

    __repr__ = __str__

    def log2filesystem(self):
        """
        write errorcondition to filesystem
        """
        j.do.createDir(j.do.joinPaths(
            j.dirs.LOGDIR, "errors", j.application.appname))
        path = j.do.joinPaths(j.dirs.LOGDIR, "errors", j.application.appname, "backtrace_%s.log" % (
            j.data.time.getLocalTimeHRForFilesystem()))

        msg = "***ERROR BACKTRACE***\n"
        msg += "%s\n" % self.backtrace
        msg += "***ERROR MESSAGE***\n"
        msg += "%s\n" % self.errormessage
        if self.errormessagePub != "":
            msg += "%s\n" % self.errormessagePub
        if len(j.logger.logs) > 0:
            msg += "\n***LOG MESSAGES***\n"
            for log in j.logger.logs:
                msg += "%s\n" % log

        msg += "***END***\n"

        j.do.writeFile(path, msg)
        return path

    # def getBacktrace(self,btkis=None,filename0=None,linenr0=None,func0=None):
    #     if btkis==None:
    #         btkis,filename0,linenr0,func0=j.errorhandler.getErrorTraceKIS()
    #     out=""
    #     # out="File:'%s'\nFunction:'%s'\n"%(filename0,func0)
    #     # out+="Linenr:%s\n*************************************************************\n\n"%linenr0
    #     # btkis.reverse()
    #     for filename,func,linenr,code,linenrOverall in btkis:
    #         # print "AAAAAA:%s %s"%(func,filename)
    #         # print "BBBBBB:%s"%linenr
    #         # out+="%-15s : %s\n"%(func,filename)
    #         out+="  File \"%s\" Line %s, in %s\n"%(filename,linenrOverall,func)
    #         c=0
    #         code2=""
    #         for line in code.split("\n"):
    #             if c==linenr:
    #                 if len(line)>120:
    #                     line=line[0:120]
    #                 # out+="  %-13s :     %s\n"%(linenrOverall,line.strip())
    #                 out+="    %s\n"%line.strip()
    #             #     pre="  *** "
    #             # else:
    #             #     pre="      "
    #             # code2+="%s%s\n"%(pre,line)
    #             c+=1

    #         # for line in code2.split("\n"):
    #         #     if len(line)>90:
    #         #         out+="%s\n"%line[0:90]
    #         #         line=line[90:]
    #         #         while len(line)>90:
    #         #             line0=line[0:75]
    #         #             out+="                 ...%s\n"%line0
    #         #             line=line[75:]
    #         #         out+="                 ...%s\n"%line
    #         #     else:
    #         #         out+="%s\n"%line

    #         # out+="-------------------------------------------------------------------\n"
    #     self.backtraceDetailed=out

    #     return out

        # stack=""
        # if j.application.skipTraceback:
        #     return stack
        # for x in traceback.format_stack():
        #     ignore=False
        #     if x.find("IPython") != -1 or x.find("MessageHandler") != -1 \
        #       or x.find("EventHandler") != -1 or x.find("ErrorconditionObject") != -1 \
        #       or x.find("traceback.format") != -1 or x.find("ipython console") != -1:
        #        ignore=True
        #     stack = "%s"%(stack+x if not ignore else stack)
        #     if len(stack)>50:
        #         self.backtrace=stack
        #         return
        # self.backtrace=stack

    def _filterLocals(self, k, v):
        try:
            k = "%s" % k
            v = "%s" % v
            if k in ["re", "q", "jumpscale", "pprint", "qexec", "jshell", "Shell",
                     "__doc__", "__file__", "__name__", "__package__", "i", "main", "page"]:
                return False
            if v.find("<module") != -1:
                return False
            if v.find("IPython") != -1:
                return False
            if v.find("click") != -1:
                return False
            if v.find("<built-in function") != -1:
                return False
            if v.find("jumpscale.Shell") != -1:
                return False
        except BaseException:
            return False

        return True

    # def getBacktraceDetailed(self,tracebackObject=""):
    #     """
    #     Get stackframe log
    #     is a very detailed log with filepaths, code locations & global vars, this output can become quite big
    #     """
    #     import inspect
    #     if j.application.skipTraceback:
    #         return ""
    #     sep="\n"+"-"*90+"\n"
    #     result = ''
    #     if not tracebackObject:
    #         return "" #TODO: needs to be fixed so it does work
    #     if tracebackObject==None:
    #         tracebackObject = inspect.currentframe()  #TODO: does not work
    #     frames = inspect.getinnerframes(tracebackObject, 16)
    #     nrlines=0
    #     for (frame, filename, lineno, fun, context, idx) in frames:
    #         ##result = result + "-"*50 + "\n\n"
    #         nrlines+=1
    #         if nrlines>100:
    #             return result
    #         location=filename + "(line %d) (function %s)\n" % (lineno, fun)
    #         if location.find("EventHandler.py")==-1:
    #             result += "  " + sep
    #             result += "  " + location
    #             result += "  " + "========== STACKFRAME==========\n"
    #             if context:
    #                 l = 0
    #                 for line in context:
    #                     prefix = "    "
    #                     if l == idx:
    #                         prefix = "--> "
    #                     l += 1
    #                     result += prefix + line
    #                     nrlines+=1
    #                     if nrlines>100:
    #                         return result
    #             result += "  " + "============ LOCALS============\n"
    #             for (k,v) in sorted(frame.f_locals.items()):
    #                 if self._filterLocals(k,v):
    #                     try:
    #                         result += "    %s : %s\n" % (str(k), str(v))
    #                     except:
    #                         pass
    #                     nrlines+=1
    #                     if nrlines>100:
    #                         return result

    #                     ##result += "  " + "============ GLOBALS============\n"
    #             ##for (k,v) in sorted(frame.f_globals.iteritems()):
    #             ##    if self._filterLocals(k,v):
    #             ##        result += "    %s : %s\n" % (str(k), str(v))
    #     self.backtrace=result

    # def getCategory(self):
    #     return "eco"

    # def getObjectType(self):
    #     return 3

    # def getVersion(self):
    #     return 1

    # def getMessage(self):
    #     #[$objecttype,$objectversion,guid,$object=data]
    #     return [3,1,self.guid,self.__dict__]

    def getContentKey(self):
        """
        return unique key for object, is used to define unique id

        """
        dd = copy.copy(self.__dict__)
        if "_ckey" in dd:
            dd.pop("_ckey")
        if "id" in dd:
            dd.pop("id")
        if "guid" in dd:
            dd.pop("guid")
        if "sguid" in dd:
            dd.pop("sguid")
        return j.data.hash.md5_string(str(dd))
