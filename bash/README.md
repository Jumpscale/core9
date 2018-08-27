# Bash

Bash utilities, are a set of utilities to let you install & play around with jumpscale 9.3+.

The main install happens by means of docker.

## Install
 
### Install from development

copy/paste into your terminal: 

```bash 
curl https://raw.githubusercontent.com/Jumpscale/bash/development/install.sh?$RANDOM > /tmp/install.sh;bash /tmp/install.sh
```

### Install from branch

```
export ZUTILSBRANCH=something
curl https://raw.githubusercontent.com/Jumpscale/bash/${ZUTILSBRANCH}/install.sh?$RANDOM > /tmp/install.sh;bash /tmp/install.sh
```

where `ZUTILSBRANCH` is branch of these utilies you want to install

what happens:

- xcode-tools will be installed & then brew (https://brew.sh/) (osx only)
- ssh-key will be looked for & created if it doesn't exist yet
- the basic init script will be added to ~/bashrc

- If everything installed correctly result should show `[+] Install OK`

- If install failed with `(13: Permission denied)` you need to install as root. Type `sudo -s` then try install again with the curl command from above.

### OSX: hard reset (DANGEROUS)

```bash 
curl https://raw.githubusercontent.com/Jumpscale/bash/development/hardreset.sh?$RANDOM > /tmp/hardreset.sh;bash /tmp/hardreset.sh
```

This will 

- remove brew
- reinstall brew
- remove all content from ~/opt
- remove all content from ~/code/github/jumpscale
- remove all old config files

do not forget to reset docker, can do this in preferences and ask hard reset.



## Make sure your the bash tools are available

do this by starting new terminal or executing `source ~/.bashrc`

After this you should be able to type Z and press [TAB] to see a list of commands. (NOTE: the Z is uppercase)

```
kristofs-MBP:~ kristofdespiegeleer$ Z
ZBranchExists                 ZDockerCommit                 ZDockerSSHAuthorize           ZInstall_host_editor          ZNodeSet                      ZSSH_RFORWARD_Usage
ZCodeConfig                   ZDockerCommitUsage            ZDoneCheck                    ZInstall_host_js9             ZNodeUbuntuPrepare            Z_apt_install
ZCodeGet                      ZDockerConfig                 ZDoneReset                    ZInstall_host_js9_full        ZResticBackup                 Z_brew_install
ZCodeGetJS                    ZDockerEnableSSH              ZDoneSet                      ZInstall_issuemanager         ZResticBuild                  Z_exists_dir
ZCodeGetJSUsage               ZDockerImageExist             ZDoneUnset                    ZInstall_js9                  ZResticCheck                  Z_exists_file
ZCodeGetUsage                 ZDockerInstallLocal           ZEXEC                         ZInstall_js9_full             ZResticEnv                    Z_mkdir
ZCodePluginInstall            ZDockerInstallSSH             ZEXECUsage                    ZInstall_js9_node             ZResticEnvReset               Z_mkdir_pushd
ZCodePush                     ZDockerRemove                 ZInstall_DMG                  ZInstall_portal9              ZResticEnvSet                 Z_popd
ZCodePushJS                   ZDockerRemoveImage            ZInstall_ays9                 ZInstall_python               ZResticInit                   Z_pushd
ZCodePushJSUsage              ZDockerRemoveImagesAll        ZInstall_docgenerator         ZInstall_zerotier             ZResticMount                  Z_transcode_mp4
ZCodePushUsage                ZDockerRun                    ZInstall_host_base            ZKeysLoad                     ZResticSnapshots
ZDockerActive                 ZDockerRunSomethingUsage      ZInstall_host_code_jumpscale  ZNodeEnv                      ZSSH
ZDockerActiveUsage            ZDockerRunUbuntu              ZInstall_host_docgenerator    ZNodeEnvDefaults              ZSSHTEST
ZDockerBuildUbuntu            ZDockerRunUsage               ZInstall_host_docker          ZNodePortSet                  ZSSH_RFORWARD
```
*Sometimes the bash profile doesn't load (especially on [Ubuntu](https://askubuntu.com/questions/121413/understanding-bashrc-and-bash-profile)). If that happens type this in a the terminal under root:
```
. ~/.bashrc
```

## Use the bash utlities!

### install jumpscale

```bash
##optional change the branch for js9
#export JS9BRANCH=9.3.0
ZInstall_host_js9
```

### To install full jumpscale on host machine

```bash
##optional change the branch for js9
#export JS9BRANCH=development
ZInstall_host_js9_full
```
This will install the following:
- Jumpscale core9
- Jumpscale libs9
- Jumpscale prefab9

### Installing ays and portal on host machine

To install ays on host:

```bash
ZInstall_host_ays9
```

To install portal on host:

```bash
ZInstall_host_portal9
```
In both cases the following will be installed in addition to the chosen component( if they are not already installed):
- Jumpscale core9
- Jumpscale libs9
- Jumpscale prefab9


### To install full jumpscale in a docker container

- For OSX make sure docker has been installed !!!
    - https://docs.docker.com/docker-for-mac/install/

- To make sure your sshkeys are loaded/generated

```bash
ZKeysLoad
```
- To get basic jumpscale (core + lib + prefab with all their dependencies)
```bash
ZInstall_js9_full
```
This might take a while! Don't panic! Wait.
- To get an AYS docker (core + lib + prefab + ays with all their dependencies)
```bash
ZInstall_ays9
```
- To get a portal as well (core + lib + prefab + portal with all their dependencies)
```bash
ZInstall_portal9
```

- To get a complete installation(core + lib + prefab + ays + portal with all their dependencies)
```bash
ZInstall_js9_all
```

Then start with
```bash
ZDockerActive -b jumpscale/<imagename> -i <name of your docker>
```

To expose ports from container use the `-a` option to specify your portforwards.For example for AYS installation you might want to expose the port on which the server is running on to allow access from outside the container. This is done as follows:
```bash
ZDockerActive -b jumpscale/ays9 -i <name of your docker> -a "-p 5000:5000"
```

### To install all editor tools for local machine (OSX & Ubuntu only)

```bash
ZInstaller_editor_host
```

### To get docker on ubuntu

```bash
ZDockerInstallLocal
```

### SSH Tools

```bash
#set node we will work on
ZNodeSet 192.168.10.1

#if different port
ZNodePortSet 2222

#to see which env has been set
ZNodeEnv

#to sync local install bash tools to the remote node
RSync_bash

#to remote execute something
ZEXEC ls /

#to remote execute multiple commands, do not forget the `` IMPORTANT
ZEXEC 'mkdir -p /tmp/1;mkdir -p /tmp/2'

#to remote execute something and make sure bash tools are there & loaded
ZEXEC -b ls /

```


