

ZInstall_DMG() {
    #@TODO: *1 check input
    echo "[+] install dmg $2"

    Z_mkdir_pushd /tmp/zdownloads || return 1

    Z_exists_file "$1" || return 1

    if [ ! -n "$2" ]; then
        die "specify name for ZInstall DMG" || return 1
    fi

    VOLUME=`hdiutil attach "$1" | grep Volumes | awk '{print $3}'` >> ${ZLogFile} 2>&1  || die || return 1
    RSync  "$VOLUME/$2.app/" "/Applications/$2.app/"/ || return 1
    # cp -rf $VOLUME/*.app /Applications >> ${ZLogFile} 2>&1  || die "cp" || return 1
    hdiutil detach $VOLUME >> ${ZLogFile} 2>&1

    Z_popd || return 1
}

IPFS_get_install_zip() {
    echo "[+] install $2"
    if [ ! -n "$2" ]; then
        die "specify name for IPFS_get_install_zip as 2nd arg" || return 1
    fi
    #@TODO: *1 check input
    Z_mkdir_pushd /tmp/zdownloads || return 1
    rm -rf "$2.app"
    rm -f "$2.zip"
    IPFS_get $1 "$2.zip" || return 1
    unzip "$2.zip" >> ${ZLogFile} 2>&1 || die "unzip $1 $2" || return 1
    RSync_move "$2.app"/ "/Applications/$2.app/" || return 1
    Z_popd || return 1
}

IPFS_get_install_deb() {
  echo "[+] install $2"
  if [ ! -n "$2" ]; then
      die "specify name for IPFS_get_install_deb as 2nd arg" || return 1
  fi
  Z_mkdir_pushd /tmp/zdownloads || return 1
  IPFS_get $1 "$2.deb" || return 1
  dpkg -i "$2.deb"
  Z_popd || return 1
}

IPFS_get() {
    #@TODO: *1 check input
    if [ ! -n "$2" ]; then
        die "specify name for IPFS_get as 2nd arg" || return 1
    fi
    Z_mkdir_pushd /tmp/zdownloads || return 1

    ipfs get $1 -o "$2" >> ${ZLogFile} 2>&1 || die "could not ipfs download $2" || return 1

    Z_popd || return 1
}


IPFS_get_install_dmg() {
    echo "[+] install $2"
    #@TODO: *1 check input
    if [ ! -n "$2" ]; then
        die "specify name for IPFS_get_install_dmg as 2nd arg" || return 1
    fi
    Z_mkdir_pushd /tmp/zdownloads || return 1
    IPFS_get $1 "$2.dmg" || return 1
    # VOLUME=`hdiutil attach "$2.dmg" | grep Volumes | awk '{print $3}'` >> ${ZLogFile} 2>&1 || die "hdutil mount" || return 1
    # cp -rf $VOLUME/*.app /Applications >> ${ZLogFile} 2>&1 || die "cp" || return 1
    # hdiutil detach $VOLUME >> ${ZLogFile} 2>&1
    ZInstall_DMG "$2.dmg" $2 || return 1
    rm -f "$2.dmg"
    Z_popd || return 1
}

IPFS_get_mount_dmg() {
    #@TODO: *1 check input
    if [ ! -n "$2" ]; then
        die "specify name for IPFS_get_mount_dmg as 2nd arg" || return 1
    fi
    Z_mkdir_pushd /tmp/zdownloads || return 1
    IPFS_get $1 "$2.dmg" || die || return 1
    VOLUME=`hdiutil attach "$2.dmg" | grep Volumes | awk '{print $3}'`  >> ${ZLogFile} 2>&1 || die "hdutil mount" || return 1
    Z_popd || return 1
}


#args: $hash $name $dest
#will use rsync to sync remotely
IPFS_get_dir(){
    #@TODO: *1 check input
    if [ ! -n "$2" ]; then
        die "specify name for IPFS_get_dir as 2nd arg" || return 1
    fi
    Z_mkdir_pushd /tmp/zdownloads || return 1
    ipfs get $1 -o "$2"  >> ${ZLogFile} 2>&1 || die "cannot get IPFS $1 to output $2" || return 1
    Z_mkdir "$3" || return 1
    RSync  "/tmp/zdownloads/$2/" "$3/" || return 1
    Z_popd || return 1

}

Z_pushd(){
    echo "pushd to: $1" >> $ZLogFile
    pushd "$1" >> $ZLogFile 2>&1 || die "could not pushd to $1" || return 1
}

Z_popd(){
    popd > /dev/null || die "could not popd" || return 1
}

Z_mkdir(){
    echo "mkdir: $1" >> $ZLogFile
    mkdir -p "$1" >> $ZLogFile 2>&1 || die "could not mkdir $1" || return 1
}

Z_mkdir_pushd(){
    Z_mkdir "$1" || return 1
    Z_pushd "$1" || return 1
}

Z_brew_install(){
    echo "brew install: $@" >> $ZLogFile
    brew install  $@ >> $ZLogFile 2>&1 || die "could not brew install $@" || return 1
}

Z_apt_install(){
  echo "apt-get install: $@" >> $ZLogFile
  sudo apt-get -y install $@ >> $ZLogFile 2>&1 || die "could not install package $@" || return 1
}

Z_exists_dir(){
    if [ ! -d "$1" ]; then
        die "dir $1 not found" || return 1
    fi
}

Z_exists_file(){
    if [ ! -f "$1" ]; then
        die "file $1 not found" || return 1
    fi
}

Z_transcode_mp4(){
    local pathbase="${1%.*}"
    local extension="${1##*.}"
    ffmpeg -i "$1" -movflags faststart -acodec copy -vcodec copy "$pathbase_.$extension"  || die || return 1
    rm -f $1
}
