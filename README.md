# Packaged version of Zotero and Juris-M.

These packages are "fat installers" -- the debs include the Zotero/Juris-M binaries. One-time installation of the repo:

If you have `wget` installed:

```
$ wget -qO- https://github.com/retorquere/zotero-deb/releases/download/apt-get/install.sh | sudo bash
```

or if you have `curl` installed:

```
$ curl -sL https://github.com/retorquere/zotero-deb/releases/download/apt-get/install.sh | sudo bash
```

after this you can install and update in the usual way:

```
$ sudo apt-get update
$ sudo apt-get install zotero # if you want Zotero
$ sudo apt-get install jurism # if you want Juris-M
```

## PPA's

Some may prefer the [PPA packages](https://github.com/retorquere/zotero-jurism-ppa). These PPA's do not include Zotero/Juris-M, but only a lightweight downloader that fetches the official binaries and installs them on your system. To use these, remove the file `/etc/apt/sources.list.d/zotero.list` if you previously used the instructions above, and then follow the instruction on https://github.com/retorquere/zotero-jurism-ppa. This will replace your Zotero/Juris-M binaries -- it will *not* touch your Zotero library.
