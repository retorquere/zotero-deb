<img src="https://www.zotero.org/static/images/promote/zotero-logo-256x62.png" alt="Zotero"><img src="https://juris-m.github.io/blog/image/juris-m-logo.svg" alt="Juris-M" height="62" align="right">

**PSA**

I'm in the process of transferring the hosting of these packages to the Zoero organisation. Until that is done, the following options are available:

* download from B2:
  * (re)install using `curl -sL https://apt.retorque.re/file/zotero-apt/install.sh | sudo bash`
* download from this repo
  * (re)install using `curl -sL https://github.com/retorquere/zotero-deb/releases/download/apt-get/install.sh | sudo bash`
  * **caveat**: github has made recent changes to how they're hosting release files, which triggered a long-standing bug in `apt`. If you hit this problem, see [this thread](https://github.com/linux-surface/linux-surface/issues/625) for a workaround.
* download from sourceforge
  * (re) install using `curl -sL https://downloads.sourceforge.net/project/zotero-deb/install.sh | sudo bash`
  * **caveat**: sourceforge uses a mirror system that updates haphazardly and which may redirect you to a mirror that is down. If you get errors, try again in a few hours.

----

This repository contains packaged releases of [Zotero](https://www.zotero.org) and [Juris-M](https://juris-m.github.io) for Debian-based Linux systems and Crostini-enabled chromebooks, and the script used to build them.

This repository updates to new releases of Zotero and Juris-M within 2 hours, usually faster.

## Contents of the packages

The packages include the whole Zotero/Juris-M binaries, as built by Zotero / Juris-M teams themselves.

The packages provide a system-wide installation (into the `/usr/lib` directory), as opposed to a single-user installation (e.g. in your `HOME` directory).

They manage both desktop file registration and MimeType registration.

## Installing Zotero / Juris-M

### Installing Zotero

To install Zotero, use the following commands:

```
wget -qO- https://apt.retorque.re/file/zotero-apt/install.sh | sudo bash
sudo apt update
sudo apt install zotero
```

### Installing Juris-M

To install Juris-M, use the following commands:

```
wget -qO- https://apt.retorque.re/file/zotero-apt/install.sh | sudo bash
sudo apt update
sudo apt install jurism
```

**Note**

You can use `curl` instead of `wget` by typing
```
curl -sL https://apt.retorque.re/file/zotero-apt/install.sh | sudo bash
```

## Updating Zotero / Juris-M

The Zotero / Juris-M programs provided by this repository have their self-update facility disabled.

Simply rely on on your system's package manager to give you update notifications when a new version comes out.

Alternatively, you can use the following commands:

```
sudo apt update
sudo apt upgrade
```

install.sh will ask for sudo permissions to install the pointer to the apt repo, and to add the signing key to the keyring.

## Beta packages

This repo also has the nightly beta's, installable as the `zotero-beta` and `jurism-beta` packages. You can install these alongside the regular packages.

## Package signing errors in Debian/Ubuntu/...

The accepted key format in Debian-based systems seems to have changed a while ago, which means the existing signing verification key you have may no longer be available during install. Re-running the install script will remedy that:

```
wget -qO- https://apt.retorque.re/file/zotero-apt/install.sh | sudo bash
```

## Instructions for installation on Crostini-capable Chromebooks

Instructions for installation on Crostini-capable Chromebooks can be found on the [wiki](https://github.com/retorquere/zotero-deb/wiki).

## Uninstall

```
wget -qO- https://apt.retorque.re/file/zotero-apt/uninstall.sh | sudo bash
sudo apt-get purge zotero
```

# Developers

To rebuild this repo you need:

* a deb-based system (I use Ubuntu)
* Python 3.9
