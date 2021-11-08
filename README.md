<img src="https://www.zotero.org/static/images/promote/zotero-logo-256x62.png" alt="Zotero"><img src="https://juris-m.github.io/blog/image/juris-m-logo.svg" alt="Juris-M" height="62" align="right">

**PSA: GITHUB DOWNLOADS FOR THIS REPO ARE CURRENTLY BROKEN FOR SOME PEOPLE (myself included)**

I'm trying to reach github about this, but in the interim I've set up a mirror on [SourceForge](https://sourceforge.net/projects/zotero-deb/files/) while github gets its act together -- they're usually super responsive, but I've heard nothing from them yet. You have to run the `install.sh` and `apt update` again but now with the URL explained there, but after that it should just work as usual. When github is back, re-running the same install from the github project will restore things to how they were, but I'll probably just leave the sourceforge mirror updated, it isn't any extra work.

----

This repository contains packaged releases of [Zotero](https://www.zotero.org) and [Juris-M](https://juris-m.github.io) for Debian-based Linux systems and Crostini-enabled chromebooks, and the script used to build them.

This repository updates to new releases of Zotero and Juris-M within 24 hours, usually faster.

## Contents of the packages

The packages include the whole Zotero/Juris-M binaries, as built by Zotero / Juris-M teams themselves.

The packages provide a system-wide installation (into the `/usr/lib` directory), as opposed to a single-user installation (e.g. in your `HOME` directory).

They manage both desktop file registration and MimeType registration.

## Installing Zotero / Juris-M

### Installing Zotero

To install Zotero, use the following commands:

```
wget -qO- https://github.com/retorquere/zotero-deb/releases/download/apt-get/install.sh | sudo bash
sudo apt update
sudo apt install zotero
```

### Installing Juris-M

To install Juris-M, use the following commands:

```
wget -qO- https://github.com/retorquere/zotero-deb/releases/download/apt-get/install.sh | sudo bash
sudo apt update
sudo apt install jurism
```

**Note**

You can use `curl` instead of `wget` by typing
```
curl -sL https://github.com/retorquere/zotero-deb/releases/download/apt-get/install.sh | sudo bash
```

## Updating Zotero / Juris-M

The Zotero / Juris-M programs provided by this repository have their self-update facility disabled.

Simply rely on on your system's package manager to give you update notifications when a new version comes out.

Alternatively, you can use the following commands:

```
sudo apt update
sudo apt upgrade
```

## Beta packages

This repo also has the nightly beta's, installable as the `zotero-beta` and `jurism-beta` packages. You can install these alongside the regular packages.

## Package signing errors in Debian/Ubuntu/...

The accepted key format in Debian-based systems seems to have changed a while ago, which means the existing signing verification key you have may no longer be available during install. Re-running the install script will remedy that:

```
wget -qO- https://github.com/retorquere/zotero-deb/releases/download/apt-get/install.sh | sudo bash
```

## Instructions for installation on Crostini-capable Chromebooks

Instructions for installation on Crostini-capable Chromebooks can be found on the [wiki](https://github.com/retorquere/zotero-deb/wiki).

