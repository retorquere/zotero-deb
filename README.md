<a href="https://www.zotero.org/"><img src="https://www.zotero.org/static/images/promote/zotero-logo-256x62.png" alt="Zotero"></a><a href="https://juris-m.github.io/"><img src="https://juris-m.github.io/blog/image/juris-m-logo.svg" alt="Juris-M" height="62" align="right"></a>

**PSA**

I was in the process of transferring the hosting of these packages to the Zotero organisation. That may or may not yet happen, but right now, the following options are available. If you are getting errors, **please re-run install.sh or see the instructions below to re-install manually**. I have had to restructure the repos. I apologize, but it was a necessary simplification. Simply re-running the install is all that is required.

**Primary source**, very much the preferred option:

* (re)install using `curl -sL https://zotero.retorque.re/file/apt-package-archive/install.sh | sudo bash`

**Deprecated sources, please change to the primary source.**

If you still use these, you will get errors -- apologies for this, but they had become so unreliable I cannot support them.

* this github project
  * github has made changes to how they're hosting release files, which triggered a long-standing bug in `apt`.
* sourceforge
  * sourceforge uses a mirror system that updates haphazardly and which may redirect you to a mirror that is down.

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
wget -qO- https://zotero.retorque.re/file/apt-package-archive/install.sh | sudo bash
sudo apt update
sudo apt install zotero
```

### Installing Juris-M

To install Juris-M, use the following commands:

```
wget -qO- https://zotero.retorque.re/file/apt-package-archive/install.sh | sudo bash
sudo apt update
sudo apt install jurism
```

**Note**

You can use `curl` instead of `wget` by typing
```
curl -sL https://zotero.retorque.re/file/apt-package-archive/install.sh | sudo bash
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
wget -qO- https://zotero.retorque.re/file/apt-package-archive/install.sh | sudo bash
```

## Instructions for installation on Crostini-capable Chromebooks

Instructions for installation on Crostini-capable Chromebooks can be found on the [wiki](https://github.com/retorquere/zotero-deb/wiki).

## Uninstall

```
wget -qO- https://zotero.retorque.re/file/apt-package-archive/uninstall.sh | sudo bash
sudo apt-get purge zotero
```

## What goes on under the hood in `install.sh`

The install.sh is convenient, but there's a risk to running random scripts from the internet as root. What the script does, and what you could manually do yourself, is:

Check whether you are installing on a supported architecture:

```
case `uname -m` in
  "i386" | "i686" | "x86_64")
    ;;
  *)
    echo "Zotero is only available for architectures i686 and x86_64"
    exit
    ;;
esac
```

Set up some basic information about the repo and your environment:

```
KEYNAME=zotero-archive-keyring.gpg
GPGKEY=https://raw.githubusercontent.com/retorquere/zotero-deb/master/$KEYNAME
KEYRING=/usr/share/keyrings/$KEYNAME
```

checks whether you have `curl` or `wget` and use that to download the public key for signature verification

```
if [ -x "$(command -v curl)" ]; then
  sudo curl -L $GPGKEY -o $KEYRING
elif [ -x "$(command -v wget)" ]; then
  sudo wget -O $KEYRING $GPGKEY
else
  echo "Error: need wget or curl installed." >&2
  exit 1
fi
sudo chmod 644 $KEYRING
```

remove old key with too broad reach if present

```
sudo rm -f /etc/apt/trusted.gpg.d/zotero.gpg
```

install repo pointer

```
cat << EOF | sudo tee /etc/apt/sources.list.d/zotero.list
deb [signed-by=$KEYRING by-hash=force] https://zotero.retorque.re/file/apt-package-archive ./
EOF
```

clean up remnants from previous use of another mirror, if any

```
sudo apt-get clean
```

# Developers

To rebuild this repo you need:

* a deb-based system (I use Ubuntu)
* Python 3.10

