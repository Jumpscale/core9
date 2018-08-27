


ZInstall_host_code_jumpscale() {
    if ZDoneCheck "ZInstall_host_code_jumpscale" ; then
        echo "[+] update jumpscale code was already done."
       return 0
    fi

    local branch='development'
    if [ ! -z $1 ]
    then
        branch=$1
    elif [ ! -z ${JS9BRANCH} ]
    then
        branch=${JS9BRANCH}
    fi
    echo "[+] loading or updating jumpscale source code (branch:$branch)"
    ZCodeGetJS -r core9 -b $branch || return 1
    ZCodeGetJS -r lib9 -b $branch  || return 1
    ZCodeGetJS -r prefab9 -b $branch || return 1
    echo "[+] update jumpscale code done"
    ZDoneSet "ZInstall_host_code_jumpscale"
}


ZInstall_host_js9() {

    if ZDoneCheck "ZInstall_host_js9" ; then
        echo "[+] Host jumpscale installation already done."
       return 0
    fi

    ZCodeConfig

    ZInstall_host_base || die "Could not ZInstall_host_base" || return 1

    ZInstall_host_code_jumpscale || die "Could not ZInstall_host_code_jumpscale" || return 1

    ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts > ${ZLogFile} 2>&1

    mkdir -p $HOME/js9host

    echo "[+] clean previous js9 install"
    rm -rf /usr/local/lib/python3.6/site-packages/JumpScale9*
    rm -rf /usr/local/lib/python3.6/site-packages/js9*

    echo "[+] install js9"
    pushd $ZCODEDIR/github/jumpscale/core9
    cp /$ZCODEDIR/github/jumpscale/core9/mascot $HOMEDIR/.mascot.txt || die "Could not copy mascot" || return 1
    pip3 install -e . > ${ZLogFile} 2>&1 || die "Could not install core9 of js9" || return 1
    popd
    # pip3 install -e $ZCODEDIR/github/jumpscale/core9 || die "could not install core9 of js9" || return 1

    echo "[+] load env"
    python3 -c 'from JumpScale9 import j;j.tools.executorLocal.initEnv()' > ${ZLogFile} 2>&1 || die "Could not install core9 of js9, initenv" || return 1
    python3 -c 'from JumpScale9 import j;j.tools.jsloader.generate()'  > ${ZLogFile} 2>&1  || die "Could not install core9 of js9, jsloader" || return 1

    echo "[+] installing jumpscale lib9"
    pushd $ZCODEDIR/github/jumpscale/lib9
    pip3 install docker
    pip3 install --no-deps -e .  > ${ZLogFile} 2>&1 || die "Coud not install lib9 of js9" || return 1
    popd


    echo "[+] installing jumpscale prefab9"
    pushd $ZCODEDIR/github/jumpscale/prefab9
    pip3 install -e .  > ${ZLogFile} 2>&1 || die "Coud not install prefab9" || return 1
    popd
    # pip3 install -e $ZCODEDIR/github/jumpscale/prefab9 || die "could not install prefab9" || return 1

    # echo "[+] installing binaries files"
    # find  $ZCODEDIR/github/jumpscale/core9/cmds -exec ln -s {} "/usr/local/bin/" \; || die || return 1
    #
    # rm -rf /usr/local/bin/cmds
    # rm -rf /usr/local/bin/cmds_guest

    echo "[+] initializing jumpscale"
    python3 -c 'from JumpScale9 import j;j.tools.jsloader.generate()' > ${ZLogFile} 2>&1  || die "Could not install core9 of js9, jsloader" || return 1

    echo "[+] js9 installed (OK)"

    ZDoneSet "ZInstall_host_js9"

}

ZInstall_host_docker() {
    ZDockerInstallLocal
}

ZInstall_host_base(){

    if ZDoneCheck "ZInstall_host_base" ; then
        echo "[+] ZInstall_host_base already installed"
       return 0
    fi

    if [ "$(uname)" == "Darwin" ]; then
        # echo "[+] upgrade brew"
        # brew upgrade  >> ${ZLogFile} 2>&1 || die "could not upgrade all brew installed components" || return 1

        echo "[+] installing git, python3, mc, tmux, curl"
        Z_brew_install mc wget python3 git unzip rsync tmux curl || return 1

        echo "[+] set system config params"
        echo kern.maxfiles=65536 | sudo tee -a /etc/sysctl.conf >> ${ZLogFile} 2>&1 || die || return 1
        echo kern.maxfilesperproc=65536 | sudo tee -a /etc/sysctl.conf >> ${ZLogFile} 2>&1 || die || return 1
        sudo sysctl -w kern.maxfiles=65536 >> ${ZLogFile} 2>&1 || die || return 1
        sudo sysctl -w kern.maxfilesperproc=65536 >> ${ZLogFile} 2>&1 || die || return 1
        ulimit -n 65536 >> ${ZLogFile} 2>&1 || die || return 1


    elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
        dist=''
        dist=`grep DISTRIB_ID /etc/*-release | awk -F '=' '{print $2}'`
        if [ "$dist" == "Ubuntu" ]; then
            echo "[+] updating packages"
            sudo apt-get update >> ${ZLogFile} 2>&1 || die "could not update packages" || return 1

            echo "[+] installing git, python, mc, tmux, curl"
            Z_apt_install mc wget python3 git unzip rsync tmux curl build-essential python3-dev || return 1

        fi
    else
        die "platform not supported"
    fi

    if [ "$(uname)" == "Darwin" ]; then
        echo "no need to install pip, should be installed already"
    else
        curl -sk https://bootstrap.pypa.io/get-pip.py > /tmp/get-pip.py || die "could not download pip" || return 1
        python3 /tmp/get-pip.py  >> ${ZLogFile} 2>&1 || die "pip install" || return 1
        rm -f /tmp/get-pip.py
    fi

    echo "[+] upgrade pip"
    pip3 install --upgrade pip >> ${ZLogFile} 2>&1 || die "pip upgrade" || return 1

    ZDoneSet "ZInstall_host_base"
}



# ZInstall_host_ipfs() {
#     if ZDoneCheck "ZInstall_host_ipfs" ; then
#         echo "[+] ZInstall_host_ipfs already installed"
#        return 0
#     fi
#
#     # container "cd tmp; mkdir -p ipfs; cd ipfs; wget --inet4-only https://dist.ipfs.io/go-ipfs/v0.4.10/go-ipfs_v0.4.10_linux-amd64.tar.gz"
#     if [ "$(uname)" == "Darwin" ]; then
#         rm -rf /tmp/ipfs
#         mkdir -p /tmp/ipfs
#         Z_pushd /tmp/ipfs
#         wget --inet4-only https://dist.ipfs.io/go-ipfs/v0.4.10/go-ipfs_v0.4.10_darwin-amd64.tar.gz
#         ipfs daemon --init &
#         Z_popd || return 1
#
#     elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
#         dist=''
#         dist=`grep DISTRIB_ID /etc/*-release | awk -F '=' '{print $2}'`
#         if [ "$dist" == "Ubuntu" ]; then
#             rm -rf /tmp/ipfs
#             mkdir -p /tmp/ipfs
#             Z_pushd /tmp/ipfs
#             wget https://dist.ipfs.io/go-ipfs/v0.4.10/go-ipfs_v0.4.10_linux-amd64.tar.gz --output-document go-ipfs.tar.gz
#             tar xvfz go-ipfs.tar.gz
#             mv go-ipfs/ipfs /usr/local/bin/ipfs
#             ipfs daemon --init &
#
#             Z_popd || return 1
#
#         fi
#     else
#         die "platform not supported"
#     fi
#
#     ZDoneSet "ZInstall_host_ipfs"
#
# }


# ZCodePluginInstall(){
#     Z_mkdir ~/.code_data_dir || return 1
#     code --install-extension $1 --user-data-dir=~/.code_data_dir >> ${ZLogFile} 2>&1 || die  "could not code install extension $1" || return 1
# }

ZInstall_host_docgenerator() {

    # ZInstall_base_host || return 1

    if [ ! "$(uname)" == "Darwin" ]; then
        die "only osx supported for now"
    fi

    js9 "j.tools.docgenerator.install()"

}

ZInstall_host_editor() {

    ZInstall_host_js9 || return 1
    # ZInstall_host_base || return 1


    if [ "$(uname)" == "Darwin" ]; then
        echo "[+] upgrade brew"
        brew upgrade  >> ${ZLogFile} 2>&1 || die "could not upgrade all brew installed components" || return 1

        echo "[+] installing git, python3, mc, tmux, curl"
        Z_brew_install pdf2svg graphviz phantomjs ipfs || return 1

        echo "[+] set system config params"
        echo kern.maxfiles=65536 | sudo tee -a /etc/sysctl.conf >> ${ZLogFile} 2>&1 || die || return 1
        echo kern.maxfilesperproc=65536 | sudo tee -a /etc/sysctl.conf >> ${ZLogFile} 2>&1 || die || return 1
        sudo sysctl -w kern.maxfiles=65536 >> ${ZLogFile} 2>&1 || die || return 1
        sudo sysctl -w kern.maxfilesperproc=65536 >> ${ZLogFile} 2>&1 || die || return 1
        ulimit -n 65536 >> ${ZLogFile} 2>&1 || die || return 1

        echo "[+] start ipfs"
        ipfs init > /dev/null 2>&1
        ipfs config --json API.HTTPHeaders '{"Access-Control-Allow-Origin": ["*"]}'
        brew services start ipfs  >> ${ZLogFile} 2>&1 || die "could not autostart ipfs" || return 1

    elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
        dist=''
        dist=`grep DISTRIB_ID /etc/*-release | awk -F '=' '{print $2}'`
        if [ "$dist" == "Ubuntu" ]; then
            echo "[+] updating packages"
            apt-get update >> ${ZLogFile} 2>&1 || die "could not update packages" || return 1

            echo "[+] installing git, python, mc, tmux, curl"
            Z_apt_install mc wget python3 git pdf2svg unzip rsync graphviz tmux curl phantomjs python3-psutil || return 1

            echo "[+] installing and starting ipfs"
            ZInstall_ipfs_host
        fi
    else
        die "platform not supported"
    fi

    if [ "$(uname)" == "Darwin" ]; then
      echo "[+] download visual studio code"
      IPFS_get_install_zip Qmd4d6Keiis5Br1XZckrA1SHWfhgBag3MDwbjxCM7wbuba 'Visual Studio Code' || return 1
      rm -f /usr/local/bin/code
      ln -s '/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code' /usr/local/bin/code || die "could not link vscode" || return 1
      brew install ctags > /dev/null 2>&1

      echo "[+] Code Editor Installed"

      echo "[+] install jumpscale python snippets"
      ZCodeGetJS -r python-snippets -b development || return 1
      RSync ~/code/github/jumpscale/python-snippets/ ~/.vscode/extensions/python-snippets-js9 || return 1

      echo "[+] download sourcetree"
      IPFS_get_install_zip QmYtc2oowycqNXeedNbu9jLyDba4okTmnK5b1MoMuaNj6C sourcetree || return 1

      echo "[+] installing node"
      Z_brew_install node || return 1

      echo "[+] installing cakebrew"
      IPFS_get_install_dmg QmbCWrGrRL8aaZYMxSym4H9mhFbuUbFhfKT3uZnxPGvhoe Cakebrew  || return 1

      echo "[*] Get Java JDK"
      IPFS_get_mount_dmg QmPqvfiX1aUj9Nyo74qa47j9kPgEtKMbQLBaxTyT9F1fTV  java_jdk || return 1
      echo "[*] Install Java JDK"
      sudo installer -pkg '/Volumes/Java 8 Update 144/Java 8 Update 144.app/Contents/Resources/JavaAppletPlugin.pkg' -target / >> ${ZLogFile} 2>&1 || die "could not install java" || return 1
      hdiutil detach '/Volumes/Java 8 Update 144'  >> ${ZLogFile} 2>&1 || die || return 1

      echo "[*] Install Trolcommander"
      brew cask install trolcommander  >> ${ZLogFile} 2>&1 || die || return 1

      echo "[*] Install Calibre"
      IPFS_get_install_dmg QmRV3g2Sy49MdKKEDE2m5WUY7CzFPRC7VsGX8jtwfofEEb calibre || return 1
      sudo ln -s /Applications/calibre.app/Contents/MacOS/ebook-convert /usr/local/bin  >> ${ZLogFile} 2>&1

      echo "[*] install iterm"
      IPFS_get_install_zip QmddU7hgKMMsZbCHKiNgQrHyGRRbahGNNeJuo2r89CZE1z iterm || return 1

      echo "[*] install onlyoffice"
      IPFS_get_install_dmg QmQTVVtY2c2GvYRXkgW1z2kgYHfaLRDBjc13qoAS7DimNp ONLYOFFICE

    elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then

      echo "[+] installing visual studio code ubuntu"
      IPFS_get_install_deb QmYWKEEzyDTjrA4LTDVUukLkzd51JdvYtLyFqwAyYfdeJm vscode || return 1

      echo "[+] installing Java JDK"
      Z_apt_install default-jdk || apt-get -fy install && Z_apt_install default-jdk

      echo "[+] installing node"
      IPFS_get_install_deb QmSWXLZZVbHtBsUH4ja6x1UXd5EzVv5gTKYMz9RzDyPJR6 node || return 1

      echo "[+] installing Trolcommander"
      IPFS_get_install_deb QmfEjsjogYER9nijJHWNFSi4uuuuVVE2WszzNwYXXz89Y9 trolcommander || return 1

      echo "[+] installing Calibre"
      Z_mkdir_pushd /tmp/calibre-installer-cache || return 1
      IPFS_get QmYj4fqrmyxsaVMDnZ5ZqjgNeVDmA6MZm7z75EYwjXdMp1 calibre-3.6.0-x86_64.txz
      Z_popd || return 1
      wget -nv -O- https://download.calibre-ebook.com/linux-installer.py | python3 -c "import sys; main=lambda:sys.stderr.write('Download failed\n'); exec(sys.stdin.read()); main()"
    fi

    #TODO: *1 need to make this multi platform

    # if [  -d "~/Applications/Visual Studio Code.app" ]; then
    #     echo "[+] no need to install visual studio code, already exists"
    # elif [  -d "/Applications/Visual Studio Code.app" ]; then
    #     echo "[+] no need to install visual studio code, already exists"
    # else

    echo "[+] installing some python pips (pylint, flake, ...)"
    pip3 install --upgrade pylint autopep8 flake8 tmuxp gitpython >> ${ZLogFile} 2>&1 || die || return 1



    echo "[+] installing mermaid"
    sudo npm install -g mermaid  >> ${ZLogFile} 2>&1 || die "could not install mermaid" || return 1


    echo "[+] Installing Code Editor Extensions"
    ZCodePluginInstall donjayamanne.python || return 1
    ZCodePluginInstall tushortz.python-extended-snippets  || return 1
    ZCodePluginInstall himanoa.python-autopep8 || return 1
    ZCodePluginInstall magicstack.magicpython || return 1
    ZCodePluginInstall abronan.capnproto-syntax || return 1
    ZCodePluginInstall eriklynd.json-tools || return 1
    ZCodePluginInstall MariusAlchimavicius.json-to-ts || return 1
    ZCodePluginInstall tuxtina.json2yaml || return 1
    ZCodePluginInstall adamvoss.yaml || return 1
    ZCodePluginInstall kosz78.nim || return 1
    ZCodePluginInstall lukehoban.go || return 1
    ZCodePluginInstall shd101wyy.markdown-preview-enhanced || return 1
    ZCodePluginInstall josa.markdown-table-formatter || return 1
    ZCodePluginInstall telesoho.vscode-markdown-paste-image || return 1
    ZCodePluginInstall darkriszty.markdown-table-prettify || return 1
    ZCodePluginInstall johnpapa.angular2 || return 1
    ZCodePluginInstall rbbit.typescript-hero || return 1
    ZCodePluginInstall esbenp.prettier-vscode || return 1
    ZCodePluginInstall msjsdiag.debugger-for-chrome || return 1
    ZCodePluginInstall donjayamanne.githistory || return 1
    ZCodePluginInstall PeterJausovec.vscode-docker || return 1
    ZCodePluginInstall waderyan.gitblame || return 1
    ZCodePluginInstall christian-kohler.npm-intellisense || return 1
    # ZCodePluginInstall DavidAnson.vscode-markdownlint || return 1
    ZCodePluginInstall felipecaputo.git-project-manager || return 1
    ZCodePluginInstall christian-kohler.path-intellisense || return 1
    ZCodePluginInstall wayou.vscode-todo-highlight || return 1
    ZCodePluginInstall bungcip.better-toml || return 1
    ZCodePluginInstall webfreak.debug || return 1
    ZCodePluginInstall ms-vscode.node-debug2 || return 1
    ZCodePluginInstall rogalmic.bash-debug || return 1
    ZCodePluginInstall actboy168.lua-debug || return 1
    ZCodePluginInstall keyring.lua || return 1
    ZCodePluginInstall gccfeli.vscode-lua || return 1
    ZCodePluginInstall trixnz.vscode-lua || return 1
    ZCodePluginInstall vitorsalgado.vscode-redis || return 1
    ZCodePluginInstall blzjns.vscode-raml || return 1
    ZCodePluginInstall donjayamanne.git-extension-pack || return 1
    ZCodePluginInstall alefragnani.project-manager || return 1
    ZCodePluginInstall Shan.code-settings-sync || return 1
    ZCodePluginInstall liximomo.sftp || return 1
    ZCodePluginInstall lamartire.git-indicators || return 1
    ZCodePluginInstall eamodio.gitlens || return 1
    ZCodePluginInstall KnisterPeter.vscode-github || return 1
    ZCodePluginInstall streetsidesoftware.code-spell-checker || return 1
    ZCodePluginInstall yzhang.markdown-all-in-one || return 1
    ZCodePluginInstall mdickin.markdown-shortcuts || return 1

    echo "[+] editor tools MAC installed (OK) !!!!"

}

# this will install a full js9 with all required system dependencies
ZInstall_host_js9_full() {

    if ZDoneCheck "ZInstall_host_js9_full" ; then
        echo "[+] Host jumpsacle full isntallation already done."
       return 0
    fi

    ZCodeConfig

    ZInstall_host_base

    ZInstall_host_code_jumpscale

    ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts

    echo "[+] install js9"
    pushd $ZCODEDIR/github/jumpscale/core9
    /bin/bash install.sh || die "Could not install core9 of js9" || return 1
    popd
    # pip3 install -e $ZCODEDIR/github/jumpscale/core9 || die "could not install core9 of js9" || return 1

    echo "[+] installing jumpscale lib9"
    pushd $ZCODEDIR/github/jumpscale/lib9
    /bin/bash install.sh || die "Coud not install lib9 of js9" || return 1
    popd
    # pip3 install --no-deps -e $ZCODEDIR/github/jumpscale/lib9 || die "could not install lib9 of js9" || return 1

    echo "[+] installing jumpscale prefab9"
    pushd $ZCODEDIR/github/jumpscale/prefab9
    /bin/bash install.sh || die "Coud not install prefab9" || return 1
    popd

    echo "[+] initializing jumpscale"
    python3 -c 'from JumpScale9 import j;j.tools.jsloader.generate()' || die "js9 generate" || return 1

    echo "[+] js9 installed (OK)"

    ZDoneSet "ZInstall_host_js9_full"

}

ZInstall_host_ays9(){
    if ZDoneCheck "ZInstall_host_ays9" ; then
        echo "[+] Jumpsacle with AYS installation already done."
       return 0
    fi

    ZInstall_host_js9_full

    echo "[+] getting ays code"
    ZCodeGetJS -r ays9 || return 1

    echo "[+] installing ays"
    pushd $ZCODEDIR/github/jumpscale/ays9
    /bin/bash install.sh || die "Coud not install ays9" || return 1
    popd

    echo "[+] ays9 installed (OK)"

    ZDoneSet "ZInstall_host_ays9"

}

ZInstall_host_portal9(){
    if ZDoneCheck "ZInstall_host_portal9" ; then
        echo "[+] Jumpsacle with portal installation already done."
       return 0
    fi

    ZInstall_host_js9_full

    echo "[+] getting portal code"
    ZCodeGetJS -r portal9 || return 1

    echo "[+] installing portal"
    pushd $ZCODEDIR/github/jumpscale/portal9
    /bin/bash install.sh ${JS9BRANCH} || die "Coud not install portal9" || return 1
    popd

    echo "[+] portal9 installed (OK)"

    ZDoneSet "ZInstall_host_portal9"

}
