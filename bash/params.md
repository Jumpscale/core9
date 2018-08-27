
# generic

logfile

# node

RNODE
RPORT

# restic

RPASSWD
RSOURCE
RDEST

# docker=

initialization relevant for docker

```bash
ZCODEDIR=~/code
ZDockerName
CONTAINERDIR=~/docker

# private dir meant for private configuration
mkdir -p ${CONTAINERDIR}/private
# cache dir to speed up installation
mkdir -p ${CONTAINERDIR}/.cache/pip

```

# dir mappings

```
-v ${CONTAINERDIR}/:/host \
-v ${ZCODEDIR}/:/opt/code \
-v ${CONTAINERDIR}/private/:/optvar/private \
-v ${CONTAINERDIR}/.cache/pip/:/root/.cache/pip/ \
```
