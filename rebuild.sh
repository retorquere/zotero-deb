#!/bin/bash

if [ "$3" != "" ]; then
  for beta in $1/zotero-beta*; do
    mv $beta `echo $beta | awk sed "s/+/$3/"`
  done
fi

apt-ftparchive packages $1 > $1/Packages

cd $1
bzip2 -kf Packages
apt-ftparchive -o APT::FTPArchive::AlwaysStat="true" -o APT::FTPArchive::Release::Codename=apt-package-archive/ -o APT::FTPArchive::Release::Acquire-By-Hash="yes" release . > Release
#(cd repo/$1 && gpg --export dpkg > zotero-archive-keyring.gpg)
#(cd repo/$1 && gpg --armor --export dpkg > zotero-archive-keyring.asc)
gpg --yes -abs -u dpkg -o Release.gpg --digest-algo sha256 Release
gpg --yes -abs -u dpkg --clearsign -o InRelease --digest-algo sha256 Release

cp Packages by-hash/MD5Sum/`md5sum Packages | awk '{print $1}'`
cp Packages.bz2 by-hash/MD5Sum/`md5sum Packages.bz2 | awk '{print $1}'`
cp Packages by-hash/SHA1/`sha1sum Packages | awk '{print $1}'`
cp Packages.bz2 by-hash/SHA1/`sha1sum Packages.bz2 | awk '{print $1}'`
cp Packages by-hash/SHA256/`sha256sum Packages | awk '{print $1}'`
cp Packages.bz2 by-hash/SHA256/`sha256sum Packages.bz2 | awk '{print $1}'`
cp Packages by-hash/SHA512/`sha512sum Packages | awk '{print $1}'`
cp Packages.bz2 by-hash/SHA512/`sha512sum Packages.bz2 | awk '{print $1}'`

awk "{ switch (\$0) { case /^BASEURL=/: print(\"BASEURL=$2\"); break; case /^CODENAME=/: print(\"CODENAME=$1\"); break; default: print; break; } }" install.sh | sponge install.sh

