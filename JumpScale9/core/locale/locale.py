import os
import re
from JumpScale9 import j
KEYP = re.compile("(\w+(\.\w+)*)\s*=\s*(.*)", re.DOTALL)

DEFAULTLOCALE = 'en'


class Domain:

    def __init__(self, key):
        self._value_ = None
        self.__key = key
        self.__dict = dict()

    @property
    def _key_(self):
        return self.__key

    def __getattr__(self, attr):
        d = self.__dict
        if attr in d:
            domain = d[attr]
        else:
            domain = Domain("%s.%s" % (self._key_, attr))
            d[attr] = domain

        return domain

    def __call__(self, **args):
        return str(self) % args

    def __repr__(self):
        return str(self)

    def __str__(self):
        return str(self._value_) if self._value_ is not None else self._key_


class Localizer:

    def __init__(self, tdirs):
        self.__domains = self.__load(tdirs)

    def __load(self, tdirs):
        domains = {}
        for path in j.do.listFilesInDir(tdirs, filter="*.l"):
            locale = os.path.splitext(j.do.getBaseName(path))[0]
            locale = locale.partition("-")[0]  # remove any packaging suffix
            if locale not in domains:
                domains[locale] = Domain(locale)
            domain = domains[locale]
            with open(path) as f:
                l = 0
                append = False
                lastdomain = domain
                for line in f:
                    l += 1
                    line = line.rstrip()
                    if append:
                        lastdomain._value_ += "\n" + line.rstrip("\\")
                        if not line.endswith("\\"):
                            append = False
                        continue

                    line = line.strip()
                    if not line or line.startswith("#"):
                        append = False
                        continue

                    append = line.endswith("\\")
                    line = line.rstrip("\\")
                    m = re.match(KEYP, line)
                    if not m:
                        raise j.exceptions.RuntimeError(
                            "Invalid line at '%s:%d'" % (path, l))
                    k = m.group(1)
                    v = m.group(3)

                    d = domain
                    for kp in k.split("."):
                        d = getattr(d, kp)
                    d._value_ = v
                    lastdomain = d

        return domains

    def __call__(self, locale):
        if locale in self.__domains:
            return self.__domains[locale]
        elif DEFAULTLOCALE in self.__domains:
            return self.__domains[DEFAULTLOCALE]
        else:
            raise j.exceptions.RuntimeError(
                "Can't find locale '%s' or the default '%s' locale" % (locale, DEFAULTLOCALE))
