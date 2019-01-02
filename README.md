# Packaged version of Zotero and Juris-M.

One-time installation of the repo:

If you have `wget` installed:

```
$ wget -qO- https://github.com/retorquere/zotero-deb/releases/download/apt-get/install.sh | sudo bash
```

or if you have `curl` installed:

```
$ curl -sL https://github.com/retorquere/zotero-deb/releases/download/apt-get/install.sh | sudo bash
```

<!--

or if the sourceforge CND is faster for you and actually works (which is approximately 3 out of four tries for me), one of

```
$ curl -sL https://downloads.sourceforge.net/project/zotero-deb/install.sh
$ wget -qO- https://downloads.sourceforge.net/project/zotero-deb/install.sh
```

-->

after this you can install and update in the usual way:

```
$ sudo apt-get update
$ sudo apt-get install zotero # if you want Zotero
$ sudo apt-get install jurism # if you want Juris-M
```

