#!/usr/bin/env bash

############ CODE

ZCodeConfig() {
    if [ -e /opt/code ] && [ "$(uname)" != "Darwin" ] ; then
        export ZCODEDIR=${ZCODEDIR:-/opt/code}
    else
        export ZCODEDIR=${ZCODEDIR:-~/code}
    fi

}

ZCodeGetJSUsage() {
   cat <<EOF
Usage: ZCodeGet [-r reponame] [-g giturl] [-a account] [-b branch]
   -r reponame: name or repo which is being downloaded
   -b branchname: defaults to development
   -h: help

check's out jumpscale repo to $ZCODEDIR/github/jumpscale/$reponame
branchname can optionally be specified.

if specified but repo exists then a pull will be done & branch will be ignored !!!

if reponame not specified then will checkout
- bash
- lib9
- core9
- ays9
- prefab

EOF
}


ZCodeGetJS() {
    echo FUNCTION: ${FUNCNAME[0]} >> $ZLogFile
    ZCodeConfig || return 1
    local OPTIND
    local account='jumpscale'
    local reponame=''
    local branch=${JS9BRANCH:-development}
    while getopts "r:b:h" opt; do
        case $opt in
           r )  reponame=$OPTARG ;;
           b )  branch=$OPTARG ;;
           h )  ZCodeGetJSUsage ; return 0 ;;
           \? )  ZCodeGetJSUsage ; return 1 ;;
        esac
    done

    if [ -z "$reponame" ]; then
        ZCodeGetJS -r core9  -b $branch || return 1
        ZCodeGetJS -r lib9 -b $branch || return 1
        ZCodeGetJS -r bash -b $branch || return 1
        ZCodeGetJS -r ays9 -b $branch || return 1
        ZCodeGetJS -r prefab9 -b $branch || return 1
        return 0
    fi

    # local giturl="git@github.com:Jumpscale/$reponame.git"
    local githttpsurl="https://github.com/jumpscale/$reponame.git"

    # check if specificed branch or $JS9BRANCH exist, if not then fallback to development
    JS9BRANCHExists ${githttpsurl} ${branch} || branch=development

    # ZCodeGet -r $reponame -a $account -u $giturl -b $branch  || ZCodeGet -r $reponame -a $account -u $githttpsurl -b $branch || return 1
    ZCodeGet -r $reponame -a $account -u $githttpsurl -b $branch || return 1

}

ZCodeGetUsage() {
   cat <<EOF
Usage: ZCodeGet [-r reponame] [-g giturl] [-a account] [-b branch]
   -t type: default is github but could be e.g. gitlab, ...
   -a account: will default to 'varia', but can be account name
   -r reponame: name or repo which is being downloaded
   -u giturl: e.g. git@github.com:mathieuancelin/duplicates.git
   -b branchname: defaults to development
   -k sshkey: path to sshkey to use for authorization when connecting to the repository.
   -h: help

check's out any git repo repo to $ZCODEDIR/$type/$account/$reponame
branchname can optionally be specified.

if specified but repo exists then a pull will be done & branch will be ignored !!!

EOF
}
#to return to original dir do Z_pushd
ZCodeGet() {
    echo FUNCTION: ${FUNCNAME[0]} > $ZLogFile
    ZCodeConfig || return 1
    local OPTIND
    local type='github'
    local account='varia'
    local reponame=''
    local giturl=''
    local branch=${JS9BRANCH:-development}
    local sshkey=''
    while getopts "a:r:u:b:t:k:h" opt; do
        case $opt in
           a )  account=$OPTARG ;;
           t )  type=$OPTARG ;;
           r )  reponame=$OPTARG ;;
           u )  giturl=$OPTARG ;;
           b )  branch=$OPTARG ;;
           k )  sshkey=$OPTARG ;;
           h )  ZCodeGetUsage ; return 0 ;;
           \? )  ZCodeGetUsage ; return 1 ;;
        esac
    done
    if [ -z "$giturl" ]; then
        ZCodeGetUsage
        return 0
    fi

    if [ -z "$reponame" ]; then
        ZCodeGetUsage
        return 0
    fi

    echo "[+] get code $giturl ($branch)"

    Z_mkdir_pushd $ZCODEDIR/$type/$account || return 1

    # check if docs.greenitglobe.com (gogs) in the url
    if grep -q docs.greenitglobe.com <<< $giturl; then
        ssh-keyscan -t rsa docs.greenitglobe.com >> ~/.ssh/known_hosts 2>&1 >> $ZLogFile || die "ssh keyscan" || return 1
    fi

    if ! grep -q ^github.com ~/.ssh/known_hosts 2> /dev/null; then
        ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts 2>&1 >> $ZLogFile || die "ssh keyscan" || return 1
    fi

    if [ ! -e $ZCODEDIR/$type/$account/$reponame ]; then
        echo " [+] clone"
        git clone -b ${branch} $giturl $reponame 2>&1 >> $ZLogFile || die "git clone" || return 1
    else
        Z_pushd $ZCODEDIR/$type/$account/$reponame || return 1
        echo " [+] pull"
        echo 'git pull' >> $ZLogFile
        git pull  2>&1 >> $ZLogFile || die "could not git pull" || return 1
        Z_popd || return 1
    fi
    Z_popd || return 1
}

ZCodePushUsage(){
   cat <<EOF
Usage: ZCodePush [-r reponame] [-a account] [-m message]
   -t type: default is github but could be e.g. gitlab, ...
   -a account: will default to 'varia', but can be account name
   -r reponame: name or repo
   -m message for commit: required !
   -h: help

   will add/remove files, commit, pull & push

EOF
}

ZCodePush() {
    echo FUNCTION: ${FUNCNAME[0]} >> $ZLogFile
    ZCodeConfig || return 1
    local OPTIND
    local type='github'
    local account='varia'
    local reponame=''
    local message=''
    while getopts "a:r:m:t:h" opt; do
        case $opt in
           t )  type=$OPTARG ;;
           a )  account=$OPTARG ;;
           r )  reponame=$OPTARG ;;
           m )  message=$OPTARG ;;
           h )  ZCodePushUsage ; return 0 ;;
           \? )  ZCodePushUsage ; return 1 ;;
        esac
    done
    if [ -z "$message" ]; then
        ZCodePushUsage
        return
    fi

    if [ -z "$account" ]; then
        ZCodePushUsage
        return
    fi
    if [ -z "$reponame" ]; then
        echo "[+] walk over directories: $ZCODEDIR/$type/$account"
        # Z_pushd $ZCODEDIR/$type/$account || return 1
        ls -d $ZCODEDIR/$type/$account/*/ | {
        # find . -mindepth 1 -maxdepth 1 -type d | {
            while read DIRPATH ; do
                DIRNAME=$(basename $DIRPATH) || die "basename" || return 1
                ZCodePush -a $account -r $DIRNAME -m $message || return 1
            done
        }
        # Z_popd || return 1
        return
    fi

    echo "[+] commit-pull-push  code $ZCODEDIR/$type/$account/$reponame"

    Z_pushd $ZCODEDIR/$type/$account > /dev/null 2>&1 || die || return 1

    if [ ! -e $ZCODEDIR/$type/$account/$reponame ]; then
        die "could not find $ZCODEDIR/$type/$account/$reponame" || return 1
    else
        Z_pushd $ZCODEDIR/$type/$account/$reponame || return 1
        echo " [+] add"
        git add . -A  2>&1 >> $ZLogFile #|| die "ZCodePush (add) $@" || return 1
        echo " [+] commit"
        git commit -m '$message'  2>&1 >> $ZLogFile #|| die "ZCodePush (commit) $@" || return 1
        echo " [+] pull"
        git pull  2>&1 >> $ZLogFile || die "ZCodePush (pull) $@" || return 1
        echo " [+] push"
        git push  2>&1 >> $ZLogFile || die "ZCodePush (push) $@" || return 1
        Z_popd || return 1
    fi
    Z_popd || return 1
}

ZCodePushJSUsage(){
    cat <<EOF
Usage: ZCodePushJS [-r reponame] [-a account] [-m message]
    -r reponame: name or repo
    -m message for commit: required !
    -h: help

    will add/remove files, commit, pull & push

EOF
}

ZCodePushJS(){
    echo FUNCTION: ${FUNCNAME[0]} >> $ZLogFile
    ZCodeConfig || return 1
    local OPTIND
    local reponame=''
    local message=''
    while getopts "r:m:h" opt; do
        case $opt in
           r )  reponame=$OPTARG ;;
           m )  message=$OPTARG ;;
           h )  ZCodePushJSUsage ; return 0 ;;
           \? )  ZCodePushJSUsage ; return 1 ;;
        esac
    done
    if [ -z "$message" ]; then
        ZCodePushJSUsage
        return
    fi

    if [ "$reponame" = "" ]; then
        ZCodePush -a jumpscale -m $message || die "$@" || return 1
    else
        ZCodePush -a jumpscale -r $reponame -m $message || die "$@" || return 1
    fi
}

JS9BRANCHExists() {
    local giturl="$1"
    local branch=${2:-${JS9BRANCH}}

    # remove the trailing .git from the giturl if exist
    giturl=${giturl%.git}

    echo "[+] Checking if ${giturl}/tree/${branch} exists"
    httpcode=$(curl -o /dev/null -I -s --write-out '%{http_code}\n' $giturl/tree/${branch})

    if [ "$httpcode" = "200" ]; then
        return 0
    else
      echo "[+] Error: ${giturl}/tree/${branch} does not exist"
        return 1
    fi
}
