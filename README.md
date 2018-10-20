# Packaged version of Zotero and Juris-M.

One-time installation of the repo:

```
$ curl --silent --location https://github.com/retorquere/zotero-deb/releases/download/apt-get/install.sh | sudo bash
```

or 

```
curl --silent --location https://downloads.sourceforge.net/project/zotero-deb/install.sh
```

if the sourceforge CND is faster for you and actually works (which is approximately 3 out of four tries for me).

after this you can install and update in the usual way:

```
$ sudo apt-get update
$ sudo apt-get install zotero jurism
```

