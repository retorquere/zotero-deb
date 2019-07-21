# Packaged version of Zotero and Juris-M.

These packages are "fat installers" -- the debs include the Zotero/Juris-M binaries, as built by Zotero/Juris-M themselves. One-time installation of the repo:

If you have `wget` installed:

```
$ wget -qO- https://github.com/retorquere/zotero-deb/releases/download/apt-get/install.sh | sudo bash
```

or if you have `curl` installed:

```
$ curl -sL https://github.com/retorquere/zotero-deb/releases/download/apt-get/install.sh | sudo bash
```

after this you can install in the usual way:

```
$ sudo apt-get update
$ sudo apt-get install zotero # if you want Zotero
$ sudo apt-get install jurism # if you want Juris-M
```

and consequently update to later versions:

```
$ sudo apt-get update
$ sudo apt-get upgrade
```

Or you can use the visual tools that do the same that come with your distro.

After installation, Zotero can be found in /usr/lib/zotero.

This repository updates to new releases within 24 hours, usually faster.

## Unofficial Global Menu support for Ubuntu 19.04+

For Global Menu support (which will *only* work on Ubuntu 19.04+ x64), change the installation url to https://github.com/retorquere/zotero-deb/releases/download/global-menu/install.sh

Note that whereas the packaged version above are the official binaries from Zotero/Juris-M, the global-menu versions have changes applied not supported by the Zotero/Juris-M teams; specifically, the CSS of the client has been changed, and a custom libxul.so has replaced the ones that are in the official Zotero/Juris-M releases.

# For developers -- Updating the packages

The update script expects a gpg key by the name `dpkg` to be available:

Set up gpg

```
cat << EOF | gpg --gen-key --batch
%no-protection
Key-Type: RSA
Key-Length: 4096
Key-Usage: sign
Name-Real: dpkg
Name-Email: dpkg@iris-advies.com
Expire-Date: 0
%commit
EOF
```

For Travis builds, you can do the following:

```
$ gpg --export-secret-keys dpkg > dpkg.priv.key
$ travis encrypt-file dpkg.priv.key --add
```
