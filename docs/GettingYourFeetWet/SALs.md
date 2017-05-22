# SALs

SALs are system abstraction layers. They provide a unified interface to system operations. You can use the different available SALs to create powerful scripts that can monitor and manage your services.

<!-- @todo: Provide more simple examples of how to use SALS, just to introduce the concept   -->

A SAL can for instance be used to check if the `.ssh` directory exists and create it if not:
```
if not j.do.exists("/root/.ssh"):
    j.sal.createDir("/root/.ssh")
```

For a detailed discussion of SALs go to the [SALs documentation](../../SAL/SAL.md).
