Packaged version of Zotero. Install the repo using 

```
curl -s https://packagecloud.io/install/repositories/retorquere/zotero/script.deb.sh | sudo bash
```

once, after that you can just use the regular apt tools to install and upgrade the package `zotero`.

## How this was packaged (you can skip this if you're not a developer)

Packaging binary .debs turns out to be simple if you don't use a PPA. From what I've been able to gather, PPAs are

1. the preferred way of doing things at least for Ubuntu/Mint, and 
2. a major PITA to get set up. I can vouch for the latter.

The bulk of the work in this repo is a rather flexible zotero-installer that can also be used for manual installs on your system rather than using the package hosted here.

The installer figures out what the latest version is, downloads it and installs it (in the case of this .deb packager) in place. I use this script as part of my tests of Better BibTeX but all or at least most of this script could be ditched if it were to be part of the zotero build process. I don't know exactly how the zotero build process works, but after Zotero is built, here's what I do:

1. create an empty directory (let's say `<deb>`) for packaging
2. Unpack the zotero .tar.bz2 into `<deb>/usr/lib/zotero` (in the case of the Zotero build it could probably just copy the build layout there)
3. Create the desktop link file in `<deb>/usr/share/applications/zotero.desktop`, with
   * `Exec=/usr/lib/zotero/zotero` and
   * `Icon=/usr/lib/zotero/chrome/icons/default/default48.png` (in the case of the zotero build this file would be fixed content)
4. Create a text file `<deb>/DEBIAN/control` with the contents as below
5. run `dpkg-deb --build <deb> zotero_5.0.56_amd64.deb`

you now have an installable .deb package

## make it apt-gettable

For apt-gettable you can either upload it to packagecloud using

```
package_cloud push zotero/zotero/ubuntu/bionic zotero_5.0.56_amd64.deb
```

or if you want to host it yourself you can create a disk layout as described at https://blog.packagecloud.io/eng/2015/08/04/apt-repository-internals/ and host it via https. Downside: more work + hosting costs, upside: download tracking.

## hosting the .debs on Github

For uploading binaries to GH releases I usually have my own scripts, but for this repo I used https://github.com/aktau/github-release:

```
github-release release --user retorquere --repo zotero_deb --tag 'zotero-5.0.56' --name 'zotero 5.0.56' --description 'zotero 5.0.56'
github-release upload --user retorquere --repo zotero_deb --tag 'zotero-5.0.56' --name 'zotero_5.0.56_amd64.deb' --file '/home/emile/github/ppa/../zotero_5.0.56_amd64.deb"
```

The python script on my repo automates all this including figuring out what the latest Zotero (or Juris-M when it comes back online) is, downloading it, laying it out, updating the control file and package name, and running the `dpkg-deb`, `package_cloud` and `github-release` commands.

## Control file

```
Package: zotero
Architecture: amd64
Maintainer: @retorquere
Priority: optional
Version: 5.0.56
Description: Zotero 5.0.56 is a free, easy-to-use tool to help you collect, organize, cite, and share r
```
