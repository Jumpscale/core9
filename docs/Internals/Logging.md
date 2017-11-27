# Logging

When you create a new module in JumpScale add a `logger` in the module using `j.logger.get("module_name")` and use the proper verb when logging.

Example:

```python
class MyModule:
  self.logger = j.logger.get('j.tools.mymodule')

 def foo(self):
   # do something
   self.logger.debug("trace something")
   self.logger.info("notify normal execution")
   self.logger.warn("something fishy happend but I can continue")
   self.logger.error("error happend, stop execution")
   self.logger.critical("this is really bad. probably should raise exception")
```

# How it works

JumpScale use the standard Python logging module.

Logging modules organize the logger in a hierarchy based on their name. The root logger of JumpScale is called `j`.

When you need to log something in a module make sure you get a logger instance using `j.logger.get(name)`. The name should start with `j` in order for the logger to inheriht the properties defined in the root logger.<br>
A good practice is to use the same name as the jslocation of the module itself. So if you're module is plugged to `j.tools.mymodule`, you probably want to get a logger with the name `j.tools.mymodule` too.

This organization is useful when an application uses JumpScale and wants to have control on what logs get be printed or saved.

See handlers and filter for more informations:

- Handlers: <https://docs.python.org/3/howto/logging.html#handlers>
- Filter: <https://docs.python.org/3/library/logging.html#filter-objects>

# Logging mode

JumpScale supports two modes of logging, **Development** and **Production**.

## Development mode:

It is the default mode of JumpScale. In this mode the root logger has two handlers that write both to the console and to a logging file located at `/host/var/log/jumpscale.log`.<br>
By default the output level to the console is set to INFO and the output level to file is DEBUG.

Example of Development mode output:

```python
from js9 import j

class TestLog(object):
    def __init__(self):
        self.__jslocation__ = "j.testlog"
        self.logger = j.logger.get('j.testlog')

    def foo(self):
        path = "/tmp/empty"
        self.logger.info("start foo method")
        if j.sal.fs.exists(path):
            self.logger.debug("%s exists, remove it" % path)
            j.sal.fs.remove(path)
        j.sal.fs.createEmptyFile(path)
        self.logger.info("end foo method")
        self.logger.error("BIG ERROR !!!")
```

The output of the `foo()` method of this simple `TestLog` class will be:

- In the console (in a real terminal you would even see nice coloring):

  ```
  [Wed30 05:50] - /opt/jumpscale9//lib/JumpScale/baselib/testlog/Testlog.py:12 - INFO     - start foo method
  [Wed30 05:50] - /opt/jumpscale9//lib/JumpScale/baselib/testlog/Testlog.py:17 - INFO     - end foo method
  [Wed30 05:50] - /opt/jumpscale9//lib/JumpScale/baselib/testlog/Testlog.py:18 - ERROR    - BIG ERROR !!!
  ```

- In the log file:

  ```
  2016-03-30 05:51:11,967 - /opt/jumpscale9//lib/JumpScale/baselib/testlog/Testlog.py:12 - INFO     - start foo method
  2016-03-30 05:51:11,967 - /opt/jumpscale9//lib/JumpScale/sal/fs/SystemFS.py:1249 - DEBUG    - path /tmp/empty is not a link
  2016-03-30 05:51:11,967 - /opt/jumpscale9//lib/JumpScale/baselib/testlog/Testlog.py:14 - DEBUG    - /tmp/empty exists, remove it
  2016-03-30 05:51:11,968 - /opt/jumpscale9//lib/JumpScale/sal/fs/SystemFS.py:291 - DEBUG    - Remove file with path: /tmp/empty
  2016-03-30 05:51:11,968 - /opt/jumpscale9//lib/JumpScale/sal/fs/SystemFS.py:1249 - DEBUG    - path /tmp/empty is not a link
  2016-03-30 05:51:11,968 - /opt/jumpscale9//lib/JumpScale/sal/fs/SystemFS.py:303 - DEBUG    - Done removing file with path: /tmp/empty
  2016-03-30 05:51:11,968 - /opt/jumpscale9//lib/JumpScale/sal/fs/SystemFS.py:309 - DEBUG    - creating an empty file with name & path: /tmp/empty
  2016-03-30 05:51:11,969 - /opt/jumpscale9//lib/JumpScale/sal/fs/SystemFS.py:314 - DEBUG    - Empty file /tmp/empty has been successfully created
  2016-03-30 05:51:11,969 - /opt/jumpscale9//lib/JumpScale/baselib/testlog/Testlog.py:17 - INFO     - end foo method
  2016-03-30 05:51:11,969 - /opt/jumpscale9//lib/JumpScale/baselib/testlog/Testlog.py:18 - ERROR    - BIG ERROR !!!
  ```

  As you can see the log file is more verbose because the log level is set to DEBUG.

  ### Production Mode

  This mode is intented to configure JumpScale logging system to act as if JumpScale was a simple library.

  It remove all the predefined loggers, handlers and allow the application to fully configure how logging should behave.

  Example of an application using JumpScale in production mode:

```python
import logging
from js9 import j


def foo():
    path = "/tmp/empty"
    logger.info("info start foo")
    if j.sal.fs.exists(path):
        logger.debug("%s exists, remove it" % path)
        j.sal.fs.remove(path)
    j.sal.fs.createEmptyFile(path)
    logger.info("debug end foo")


if __name__ == '__main__':
    j.logger.set_mode("PRODUCTION")
    sh = logging.StreamHandler()
    logging.basicConfig(level="DEBUG", handlers=[sh])
    logger = logging.getLogger('myapp')

    foo()
```

This simple example shows how the main application configurea how logging should behave.

Here we attach a handler to output to the console and set the logging level to DEBUG. The ouput of this application is:

```
INFO:myapp:info start foo
DEBUG:j.sal.fs:path /tmp/empty is not a link
DEBUG:myapp:/tmp/empty exists, remove it
DEBUG:j.sal.fs:Remove file with path: /tmp/empty
DEBUG:j.sal.fs:path /tmp/empty is not a link
DEBUG:j.sal.fs:Done removing file with path: /tmp/empty
DEBUG:j.sal.fs:creating an empty file with name & path: /tmp/empty
DEBUG:j.sal.fs:Empty file /tmp/empty has been successfully created
INFO:myapp:debug end fo
```

As you can see the JumpScale module are properly shown and use the default logging format.

# Configuration

Logging configuration is located by default in jumpscale config file (`/root/js9host/cfg/jumpscale9.toml`).  
If the logging section doesn't exist in your config file, you can add it yourself.

There are 3 options you can configure.

- **Mode**: either 'DEV' or 'PRODUCTION'
- **level**: in case the mode is 'DEV', choose the level of the console handler. This means the level set here is the minimum level of logging you want to see output to the console.
- **filter**: Filter is a list of logger name you want to filter out. JumpScale is a big framework and console output can quickly become to verbose. Use this filter list to remove some of the module you don't want to see logged on the console. This filter only concern the console handler, log file will always contains logs from all modules.

Example logging configuration:

```toml
[logging]
mode = "DEV"
level = "INFO"
filter = ["j.sal.fs"]
```

```
!!!
title = "Logging"
date = "2017-04-08"
tags = []
```
