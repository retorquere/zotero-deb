# Packaged version of Zotero and Juris-M.

## Installation

One-time installation of the repo:

for `bionic`:

`$ curl --silent -L https://sourceforge.net/projects/zotero-deb/files/repo/bionic/install.sh | sudo bash`

for `trusty`:

`$ curl --silent -L https://sourceforge.net/projects/zotero-deb/files/repo/trusty/install.sh | sudo bash`

after this you can install and update in the usual way:

`$ sudo apt-get update`

`$ sudo apt-get install zotero jurism`

## How this was packaged (you can skip this if you're not a developer)

Packaging binary .debs turns out to be simple if you don't use a PPA. From what I've been able to gather, PPAs are

1. the preferred way of doing things at least for Ubuntu/Mint, and 
2. a major PITA to get set up. I can vouch for the latter.

The bulk of the work in this repo is a rather flexible zotero-installer that can also be used for manual installs on your system rather than using the package hosted here.

The installer figures out what the latest version is, downloads it and installs it (in the case of this .deb packager) in place. I use this script as part of my tests of Better BibTeX but all or at least most of this script could be ditched if it were to be part of the zotero build process. I don't know exactly how the zotero build process works, but after I have the packaged Zotero, here's what I do:

1. create an empty directory (let's say `<deb>`) for packaging
2. Unpack the zotero .tar.bz2 into `<deb>/usr/lib/zotero` (in the case of the Zotero build it could probably just copy the build layout there)
3. Create the desktop link file in `<deb>/usr/share/applications/zotero.desktop`, with
   * `Exec=/usr/lib/zotero/zotero` and
   * `Icon=/usr/lib/zotero/chrome/icons/default/default48.png` (in the case of the zotero build this file would be fixed content)
4. Create a text file `<deb>/DEBIAN/control` with the contents as below
5. run `dpkg-deb --build <deb> zotero_5.0.56_amd64.deb`

you now have an installable .deb package

## make it apt-gettable

install the build tools:

```
sudo apt-get install reprepro gnupg
```

generate your gpg key if you don't have one already

```
gpg --gen-key
```

create the layout
```
mkdir -p apt/incoming
mkdir -p apt/conf
mkdir -p apt/key
gpg --armor --export username <your email> > apt/key/deb.gpg.key

cat << EOF > apt/conf/distributions
Origin: Emiliano Heyns
Label: Zotero/Juris-M
Suite: stable
Codename: bionic
Version: 18.04
Architectures: amd64
Components: universe
Description: Zotero/Juris-M
SignWith: yes
EOF

reprepro --ask-passphrase -Vb apt export
```

add the package

```
reprepro -Vb apt -S Science includedeb bionic zotero_5.0.56_amd64.deb
```

and send it to sourceforge

```
rsync -avP -e ssh apt/ retorquere@frs.sourceforge.net:/home/pfs/project/zotero-deb/repo
```

## hosting the .debs on Github

For uploading binaries to GH releases I usually have my own scripts, but for this repo I used https://github.com/aktau/github-release:

```
github-release release --user retorquere --repo zotero_deb --tag 'zotero-5.0.56' --name 'zotero 5.0.56' --description 'zotero 5.0.56'
github-release upload --user retorquere --repo zotero_deb --tag 'zotero-5.0.56' --name 'zotero_5.0.56_amd64.deb' --file '/home/emile/github/ppa/../zotero_5.0.56_amd64.deb"
```

The python script on this repo automates all this including figuring out what the latest Zotero (or Juris-M when it comes back online) is, downloading it, laying it out, updating the control file and package name, and running the `dpkg-deb`, `package_cloud` and `github-release` commands.

## Control file

```
Package: zotero
Architecture: amd64
Maintainer: @retorquere
Priority: optional
Version: 5.0.56
Description: Zotero 5.0.56 is a free, easy-to-use tool to help you collect, organize, cite, and share r
```
