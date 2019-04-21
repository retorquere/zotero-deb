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

# Updating the packages

The update script expects a gpg key by the name `dpkg` to be available. For Travis builds, you can do the following:

```
$ gpg --export-secret-keys dpkg > dpkg.priv.key
$ travis encrypt-file dpkg.priv.key --add
```
