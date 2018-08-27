#!/bin/bash

PS4='(${BASH_SOURCE}:${LINENO}): ${FUNCNAME[0]} - [${SHLVL},${BASH_SUBSHELL}, $?]'

if [ -d "/opt/code/github/jumpscale" ] && [ "$(uname)" != "Darwin" ] ; then
    export ZUTILSDIR='/opt/code/github/jumpscale'
else
    export ZUTILSDIR=${ZUTILSDIR:-~/code/github/jumpscale}
fi

export ZLogFile='/tmp/zutils.log'

die() {
    set +x
    rm -f /tmp/sdwfa #to remove temp passwd for restic, just to be sure
    echo
    echo "**** ERRORLOG ****"
    cat $ZLogFile
    echo
    echo "[-] something went wrong: $1"
    echo
    echo
    # set -x
    return 1
}

# catcherror_handler() {
#     if [ "${ZLogFile}" != "" ]; then
#         echo "[-] line $1: script error, backlog from ${ZLogFile}:"
#         cat ${ZLogFile}
#         return 1
#     fi

#     echo "[-] line $1: script error, no logging file defined"
#     return 1
# }

ZDoneSet() {
    mkdir -p /tmp/zutils_done
    touch /tmp/zutils_done/$1
}

ZDoneUnset() {
    rm -f /tmp/zutils_done/$1*
}

ZDoneCheck() {
    if [ -f /tmp/zutils_done/$1 ]; then
       return 0
    fi
    return 1
}

ZDoneReset() {
    rm -rf /tmp/zutils_done
    mkdir -p /tmp/zutils_done
}


# catchfatal_handler() {
#     if [ "${ZLogFile}" != "" ]; then
#         echo "[-] script error, backlog from ${ZLogFile}:"
#         cat ${ZLogFile}
#         exit 1
#     fi
#
#     echo "[-] script error, no logging file defined"
#     exit 1
# }


echo "init" >> $ZLogFile

if [ ! -d "${ZUTILSDIR}/bash" ]; then
    echo "[-] ${ZUTILSDIR}/bash: directory not found"
    return 1
fi

set +e

pushd $ZUTILSDIR/bash > /dev/null 2>&1
. lib/code_lib.sh
. lib/docker_lib.sh
. lib/restic_lib.sh
. lib/ssh_lib.sh
. lib/installers.sh
. lib/tmux.sh
. lib/rsync.sh
. lib/installers_host.sh
. lib/base_lib.sh

set +e

if [ -z "$HOMEDIR" ] ; then
    export HOMEDIR="$HOME"
fi

if [ -z "$LC_ALL" ] ; then
    export LC_ALL="C.UTF-8"
fi

if [ -z "$HOMEDIR" ] || [ ! -d "$HOMEDIR" ]; then
    echo "[-] ERROR, could not find homedir $HOMEDIR"
    return 1
fi

if [ -d "/opt/bin" ]; then
    export PATH=/opt/bin:$PATH
fi

if [ -d "/opt/go/bin" ]; then
    export PATH=/opt/go/bin:$PATH
fi

# if [ ! -e ~/.iscontainer ]; then
#     ZKeysLoad
# fi

echo "[+] zlibs enabled." >>${ZLogFile}

popd > /dev/null 2>&1
