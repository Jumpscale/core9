# ACTIVE DEVELOPMENT CONTINUES IN: 
# https://github.com/threefoldtech

# JumpScale 9

[![Join the chat at https://gitter.im/Jumpscale/jumpscale_core9](https://badges.gitter.im/Jumpscale/jumpscale_core9.svg)](https://gitter.im/Jumpscale/jumpscale_core9?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge) ![travis](https://travis-ci.org/Jumpscale/core9.svg?branch=master)

JumpScale is a cloud automation product and a branch from what used to be Pylabs. About 9 years ago Pylabs was the basis of a cloud automation product which was acquired by SUN Microsystems from Q-Layer. In the mean time we are 4 versions further and we have rebranded it to JumpScale.

- [JumpScale 9](#jumpscale-9)
    - [About JumpScale9 Core](#about-jumpscale9-core)
    - [Installing JumpScale9 Core](#installing-jumpscale9-core)
        - [install using bash tools](#install-using-bash-tools)
        - [Install using pip3](#install-using-pip3)
    - [Usage](#usage)
    - [Tutorials](#tutorials)

## About JumpScale9 Core

The core module provides the bare framework into which other modules of JumpScale plug into.

Of these provided tools are, most notably:

* [Config Manager](docs/config/configmanager.md)
  The config manager is a secure way to manage configuration instances. Anything saved to the file system is NACL encrypted and only decrypted on the fly when accessed.

- [Executors](docs/Internals/Executors.md)
  JumpScale comes with its own executors that abstract working locally or remotely.
  Of these executors:

  * SSH Executor (for remote execution)
  * Local Executor (for local execution)
  * Docker Executor (for executing on dockers)

* [JSLoader](docs/JSLoader/JSLoader.md)
* [Node Manager]()

## Installing JumpScale9 Core

_tested on osx, ubuntu 16.04, ubuntu 17.04
(will upgrade brew as part of the process on OSX)_

### install using [bash tools](https://github.com/Jumpscale/bash)

```bash
#to define branch:
export JS9BRANCH="development"
curl https://raw.githubusercontent.com/Jumpscale/core9/$JS9BRANCH/install.sh?$RANDOM > /tmp/install_js9.sh;bash /tmp/install_js9.sh
```

to follow the install

```bash
tail -f /tmp/zutils.log
```

to test that it worked:

```bash
js9
```

### Install using pip3

```
mkdir -p /opt/code/github/jumpscale
pip3 install -e git+https://github.com/Jumpscale/core9@development#egg=core9 --src /opt/code/github/jumpscale/
```

## Usage

* The jsshell
  in your terminal, type `js9`

- In Python

  ```bash
  python3 -c 'from js9 import j;print(j.application.getMemoryUsage())'
  ```

  the default mem usage < 23 MB and lazy loading of the modules.

## Tutorials
How to run a sandbox of jumpscale and python  [Check Documentation](docs/howto/sandbox_python_zeroos_container.md)
<!TODO>
