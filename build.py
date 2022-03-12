#!/usr/bin/env python3

import os, sys
from types import SimpleNamespace
import tempfile
#import configparser
import shutil, shlex
#import subprocess
#import argparse
#import re
#import contextlib
#import hashlib
#from pathlib import Path
#from colorama import Fore, Style

from util import Config, run, Open, IniFile

def package(staged, betadelim):
  assert os.path.isdir(staged)

  # gather metadata for the deb file
  deb = SimpleNamespace()

  # get version and package name
  with IniFile(os.path.join(staged, 'application.ini')) as ini:
    deb.vendor = ini['App']['Vendor'] # vendor instead of app name because jurism uses the same appname
    deb.package = deb.client = deb.vendor.lower()
    deb.version = ini['App']['Version']
    if '-beta' in deb.version:
      deb.package += '-beta'
      # https://bugs.launchpad.net/ubuntu/+source/dpkg/+bug/1701756/comments/3. + and ~ get escaped in URLs in B2 and GH respectively, ':' is seen as an epoch, . is going to cause problems, - is reserved for bumps
      deb.version = deb.version.replace('-beta', '').replace('+', betadelim)
    deb.version = Config[deb.client].bumped(deb.version)

  # detect arch from staged dir
  deb.arch = staged.split('_')[-1]

  with tempfile.TemporaryDirectory() as builddir:
    print('created temporary directory', builddir)
    deb.build = builddir

    # get package dependencies
    deb.dependencies = Config[deb.client].dependencies[:]

    # inherit the firefox-esr dependencies except lsb-release and libgcc
    for dep in os.popen('apt-cache depends firefox-esr').read().split('\n'):
      dep = dep.strip()
      if not dep.startswith('Depends:'): continue
      dep = dep.split(':')[1].strip()
      if dep == 'lsb-release': continue # why should it need this?
      if 'gcc' in dep: continue #43
      deb.dependencies.append(dep)
    deb.dependencies = ', '.join(sorted(list(set(deb.dependencies))))

    # for the desktop entry
    deb.description = Config[deb.client].description
    # path to the generated deb file
    deb.deb = os.path.join(Config.repo.path, f'{deb.package}_{deb.version}_{deb.arch}.deb')

    # copy zotero to the build directory, excluding the desktpo file (which we'll recreate later) and the files that are only for the zotero-internal updater,
    # as these packages will be updated by apt
    os.makedirs(os.path.join(deb.build, 'usr/lib'), exist_ok=True)
    shutil.copytree(staged, os.path.join(deb.build, 'usr/lib', deb.package), ignore=shutil.ignore_patterns(deb.client + '.desktop', 'active-update.xml', 'precomplete', 'removed-files', 'updates', 'updates.xml'))

    # disable auto-update
    with Open(os.path.join(deb.build, 'usr/lib/', deb.package, 'defaults/pref/local-settings.js'), 'a') as ls, Open(os.path.join(deb.build, 'usr/lib/', deb.package, 'mozilla.cfg'), 'a') as cfg:
      # enable mozilla.cfg
      if ls.tell() != 0: print('', file=ls) # if the file exists, add an empty line
      print('pref("general.config.obscure_value", 0); // only needed if you do not want to obscure the content with ROT-13', file=ls)
      print('pref("general.config.filename", "mozilla.cfg");', file=ls)

      # disable auto-update
      if cfg.tell() == 0:
        print('//', file=cfg) # this file needs to start with '//' -- if it's empty, add it, if not, it should already be there
      else:
        print('', file=cfg)
      # does not make it impossible for the user to request an update (which will fail, because this install is root-owned), but Zotero won't ask the user to do so
      print('lockPref("app.update.enabled", false);', file=cfg)
      print('lockPref("app.update.auto", false);', file=cfg)

    # create desktop file from existing .desktop file, but add mime handlers that Zotero can respond to
    with IniFile(os.path.join(staged, deb.client + '.desktop')) as ini:
      deb.section = ini['Desktop Entry'].get('Categories', 'Science;Office;Education;Literature').rstrip(';')
      ini.set('Desktop Entry', 'Exec', f'/usr/lib/{deb.package}/{deb.client} --url %u')
      ini.set('Desktop Entry', 'Icon', f'/usr/lib/{deb.package}/chrome/icons/default/default256.png')
      ini.set('Desktop Entry', 'MimeType', ';'.join([
        'x-scheme-handler/zotero',
        'application/x-endnote-refer',
        'application/x-research-info-systems',
        'text/ris',
        'text/x-research-info-systems',
        'application/x-inst-for-Scientific-info',
        'application/mods+xml',
        'application/rdf+xml',
        'application/x-bibtex',
        'text/x-bibtex',
        'application/marc',
        'application/vnd.citationstyles.style+xml'
      ]))
      ini.set('Desktop Entry', 'Description', deb.description.format_map(vars(deb)))
      with Open(os.path.join(deb.build, 'usr/share/applications', f'{deb.package}.desktop'), 'w') as f:
        ini.write(f, space_around_delimiters=False)

    # add mime info
    with open('mime.xml') as mime, Open(os.path.join(deb.build, 'usr/share/mime/packages', f'{deb.package}.xml'), 'w') as f:
      f.write(mime.read())

    # write build control file
    with Open(os.path.join(deb.build, 'DEBIAN/control'), 'w') as f:
      print(f'Package: {deb.package}', file=f)
      print(f'Architecture: {deb.arch}', file=f)
      print(f'Depends: {deb.dependencies}', file=f)
      print(f'Maintainer: {Config.maintainer.email}', file=f)
      print(f'Section: {deb.section}', file=f)
      print('Priority: optional', file=f)
      print(f'Version: {deb.version}', file=f)
      print(f'Description: {deb.description}', file=f)

    # create symlink to binary
    os.makedirs(os.path.join(deb.build, 'usr/local/bin'))
    os.symlink(f'/usr/lib/{deb.package}/{deb.client}', os.path.join(deb.build, 'usr/local/bin', deb.package))

    # build deb
    if os.path.exists(deb.deb):
      os.remove(deb.deb)
    os.makedirs(os.path.dirname(deb.deb), exist_ok=True)
    run(f'fakeroot dpkg-deb --build -Zgzip {shlex.quote(deb.build)} {shlex.quote(deb.deb)}')
    run(f'dpkg-sig -k {shlex.quote(Config.maintainer.gpgkey)} --sign builder {shlex.quote(deb.deb)}')

def rebuild():
  # rebuild repo
  os.makedirs(Config.repo.path, exist_ok=True)
  with chdir(Config.repo.path):
    # these will be recreated, but just to be sure
    run('rm -f *Package* *Release*')
  
    gpgkey = shlex.quote(Config.maintainer.gpgkey)
    repo = os.path.relpath(Config.repo.path, Config.repo.build)
  
    with chdir(Config.repo.build):
      # collects the Package metadata
      # needs to be ran from the wwwroot so the packages have the path relative to wwwroot
      run(f'apt-ftparchive packages {shlex.quote(repo)} > {shlex.quote(os.path.join(repo, "Packages"))}')
  
    run(f'bzip2 -kf Packages')
  
    # creates the Release file with pointers to the Packages file and sig
    run(f'apt-ftparchive -o APT::FTPArchive::AlwaysStat="true" -o APT::FTPArchive::Release::Codename={shlex.quote(repo + "/")} -o APT::FTPArchive::Release::Acquire-By-Hash="yes" release . > Release')
  
    # export public key so people can install the repo
    run(f'gpg --export {gpgkey} > zotero-archive-keyring.gpg')
    run(f'gpg --armor --export {gpgkey} > zotero-archive-keyring.asc')
  
    # sign the Release file
    run(f'gpg --yes -abs -u {gpgkey} -o Release.gpg --digest-algo sha256 Release')
    run(f'gpg --yes -abs -u {gpgkey} --clearsign -o InRelease --digest-algo sha256 Release')
  
    # apt has race conditions. https://blog.packagecloud.io/eng/2016/09/27/fixing-apt-hash-sum-mismatch-consistent-apt-repositories/
    hash_type = None
    run('rm -rf by-hash')
    # parse the Release file to get the hashes and copy the Package files to their hashes
    with open('Release') as f:
      for line in f.readlines():
        line = line.rstrip()
        if line in [ 'MD5Sum:', 'SHA1:', 'SHA256:', 'SHA512:' ]:
          hash_type = line.replace(':', '')
        elif line.startswith(' '):
          hsh, size, filename = line.strip().split()
  
          if filename == 'Release': # Release can't possibly contain it's own size and hash?!
            continue
  
          # check size -- probably overkill
          assert os.path.getsize(filename) == int(size), (filename, os.path.getsize(filename), int(size))
  
          # check hash -- probably overkill
          with open(filename, 'rb') as f:
            hasher = getattr(hashlib, hash_type.lower().replace('sum', ''))
            should = hasher(f.read()).hexdigest()
            assert hsh == should, (filename, hash_type, 'mismatch')
  
          # copy file
          hash_dir = os.path.join('by-hash', hash_type)
          os.makedirs(hash_dir, exist_ok=True)
          run(f'cp {filename} {hash_dir}/{hsh}')
