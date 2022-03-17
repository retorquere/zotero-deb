#!/bin/bash

export DEBS=$1
export CODENAME=$2

if [ -d "$CODENAME" ]; then
  echo "${CODENAME} already exists!"
  exit 1
fi

cp -r $DEBS $CODENAME
# https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=299035
apt-ftparchive packages $CODENAME > $CODENAME/Packages | awk 'BEGIN{ok=1} { if ($0 ~ /^E: /) { ok = 0 }; print } END{exit !ok}'

cd $CODENAME
rm -rf by-hash
bzip2 -kf Packages
apt-ftparchive -o APT::FTPArchive::AlwaysStat="true" -o APT::FTPArchive::Release::Codename=$CODENAME/ -o APT::FTPArchive::Release::Acquire-By-Hash="yes" release . > Release
gpg --export dpkg > zotero-archive-keyring.gpg
gpg --armor --export dpkg > zotero-archive-keyring.asc
gpg --yes -abs -u dpkg -o Release.gpg --digest-algo sha256 Release
gpg --yes -abs -u dpkg --clearsign -o InRelease --digest-algo sha256 Release

mkdir -p by-hash/MD5Sum
cp Packages by-hash/MD5Sum/`md5sum Packages  | awk '{print $1}'`
cp Packages.bz2 by-hash/MD5Sum/`md5sum Packages  | awk '{print $1}'`

mkdir -p by-hash/SHA1
cp Packages by-hash/SHA1/`sha1sum Packages  | awk '{print $1}'`
cp Packages.bz2 by-hash/SHA1/`sha1sum Packages  | awk '{print $1}'`

mkdir -p by-hash/SHA256
cp Packages by-hash/SHA256/`sha256sum Packages  | awk '{print $1}'`
cp Packages.bz2 by-hash/SHA256/`sha256sum Packages  | awk '{print $1}'`

mkdir -p by-hash/SHA512
cp Packages by-hash/SHA512/`sha512sum Packages  | awk '{print $1}'`
cp Packages.bz2 by-hash/SHA512/`sha512sum Packages  | awk '{print $1}'`
