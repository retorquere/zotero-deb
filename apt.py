#!/usr/bin/env python3

import os, sys
from types import SimpleNamespace
import tempfile
import shutil, shlex
import hashlib, time
from pathlib import Path

from util import Config, run, Open, IniFile, chdir

def packagename(client, version, arch):
  return f'{client}_{version}_{arch}.deb'

def prebuilt():
  return Config.repo.glob('*.deb')

def package(staged):
  assert staged.is_dir()

  # gather metadata for the deb file
  deb = SimpleNamespace()

  # get version and package name
  print('packaging', staged)
  app_ini = None
  for app_ini_candidate in [staged / 'application.ini', staged / 'app' / 'application.ini']:
    if app_ini_candidate.exists():
      app_ini = app_ini_candidate
  if app_ini is None:
    raise ValueError('no application.ini in', staged)
  with IniFile(app_ini) as ini:
    deb.vendor = ini['App']['Vendor'] # vendor instead of app name because jurism uses the same appname
    deb.package = deb.client = deb.vendor.lower()
    deb.version = ini['App']['Version']
    if '-beta' in deb.version:
      deb.package += '-beta'
      # https://bugs.launchpad.net/ubuntu/+source/dpkg/+bug/1701756/comments/3. + and ~ get escaped in URLs in B2 and GH respectively, ':' is seen as an epoch, . is going to cause problems, - is reserved for bumps
      deb.version = deb.version.replace('-beta', '')
    deb.version = Config[deb.package].bumped(deb.version)

  # detect arch from staged dir
  deb.arch = staged.name.split('_')[-1]

  with tempfile.TemporaryDirectory() as build_dir:
    print('created temporary directory', build_dir)

    build_dir = Path(build_dir)

    # get package dependencies
    deb.dependencies = Config.common.dependencies[:]
    if 'dependencies' in Config[deb.package]:
      deb.dependencies += Config[deb.package].dependencies[:]

    # inherit the firefox-esr dependencies except lsb-release and libgcc
    for dep in os.popen('apt-cache depends firefox-esr').read().split('\n'):
      dep = dep.strip()
      if not dep.startswith('Depends:'): continue
      dep = dep.split(':')[1].strip()
      if dep == 'lsb-release': continue # why should it need this?
      if 'gcc' in dep: continue #43
      deb.dependencies.append(dep)
    deb.dependencies = ', '.join(sorted(list(set(deb.dependencies))))
    print('dependencies:', deb.dependencies)

    # for the desktop entry
    deb.description = Config[deb.package].description
    deb.filename = f'{deb.package}_{deb.version}_{deb.arch}.deb'
    # path to the generated deb file
    deb_file = Config.repo / deb.filename

    # copy zotero to the build directory, excluding the desktop file (which we'll recreate later) and the files that are only for the zotero-internal updater,
    # as these packages will be updated by apt
    package_dir = build_dir / 'usr/lib' / deb.package
    shutil.copytree(
      staged,
      package_dir,
      ignore=shutil.ignore_patterns(
        deb.client + '.desktop',
       'active-update.xml', 'precomplete', 'removed-files', 'updates', 'updates.xml'
       )
    )

    # enable mozilla.cfg
    with Open(package_dir / 'defaults/pref/local-settings.js', 'a') as ls: 
      if ls.tell() != 0: print('', file=ls) # if the file exists, add an empty line
      print('pref("general.config.obscure_value", 0); // only needed if you do not want to obscure the content with ROT-13', file=ls)
      print('pref("general.config.filename", "mozilla.cfg");', file=ls)

    # disable auto-update
    with Open(package_dir / 'mozilla.cfg', 'a') as cfg:
      if cfg.tell() == 0:
        print('//', file=cfg) # this file needs to start with '//' -- if it's empty, add it, if not, it should already be there
      else:
        print('', file=cfg)
      # does not make it impossible for the user to request an update (which will fail, because this install is root-owned), but Zotero won't ask the user to do so
      print('lockPref("app.update.enabled", false);', file=cfg)
      print('lockPref("app.update.auto", false);', file=cfg)

    # create desktop file from existing .desktop file, but add mime handlers that Zotero can respond to
    with IniFile(staged / f'{deb.client}.desktop') as ini:
      deb.section = ini['Desktop Entry'].get('Categories', 'Science;Office;Education;Literature').rstrip(';')
      ini.set('Desktop Entry', 'Exec', f'/usr/lib/{deb.package}/{deb.client} --url %u')
      ini.set('Desktop Entry', 'Name', deb.package.capitalize())

      beta_icon = package_dir / 'icons' / 'icon128.png'
      if beta_icon.is_file():
        ini.set('Desktop Entry', 'Icon', f'/usr/lib/{deb.package}/icons/icon128.png')
      else:
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
      with Open(build_dir / 'usr/share/applications' / f'{deb.package}.desktop', 'w') as f:
        ini.write(f, space_around_delimiters=False)

    # add mime info
    build_mime = build_dir / 'usr/share/mime/packages'
    build_mime.mkdir(parents=True)
    shutil.copy('mime.xml', build_mime/f'{deb.package}.xml')

    # write build control file
    with Open(build_dir / 'DEBIAN/control', 'w') as f:
      print(f'Package: {deb.package}', file=f)
      print(f'Architecture: {deb.arch}', file=f)
      print(f'Depends: {deb.dependencies}', file=f)
      print(f'Maintainer: {Config.maintainer.email}', file=f)
      print(f'Section: {deb.section}', file=f)
      print('Priority: optional', file=f)
      print(f'Version: {deb.version}', file=f)
      print(f'Description: {deb.description}', file=f)

    # create symlink to binary
    build_bin = build_dir / 'usr/bin'
    build_bin.mkdir(parents=True) 
    (build_bin / deb.package).symlink_to(f'/usr/lib/{deb.package}/{deb.client}')

    # build deb
    deb_file.unlink(missing_ok=True)
    run(f'fakeroot dpkg-deb --build -Zgzip {shlex.quote(str(build_dir))} {shlex.quote(str(deb_file))}')
    #run(f'dpkg-sig -k {shlex.quote(Config.maintainer.gpgkey)} --sign builder {shlex.quote(str(deb_file))}')

    changes = deb_file.with_suffix('.changes')
    with open(deb_file, 'rb') as f:
      md5sum = hashlib.md5(f.read()).hexdigest()
    with Open(changes, 'w') as f:
      size = os.path.getsize(deb_file)
      f.write(f"Format: 1.8\n")
      f.write(f"Date: {time.strftime('%a, %d %b %Y %H:%M:%S %z')}\n")
      f.write(f"Source: {deb.package}\n")
      f.write(f"Binary: {deb.package}\n")
      f.write(f"Architecture: {deb.arch}\n")
      f.write(f"Version: {deb.version}\n")
      f.write(f"Distribution: unstable\n")
      f.write(f"Urgency: medium\n")
      f.write(f"Maintainer: {Config.maintainer.email}\n")
      f.write(f"Changed-By: {Config.maintainer.name}\n")
      f.write(f"Description: \n")
      f.write(f" {deb.package} - {deb.description}\n")
      f.write(f"Checksums-Md5: \n")
      f.write(f" {md5sum} {size} {deb_file}\n")
      f.write(f"Files: \n")
      f.write(f" {md5sum} {size} {deb_file}\n")
      
    run(f'debsign -k{Config.maintainer.gpgkey} {changes}')

def mkrepo():
  with chdir(Config.repo):
    # collects the Package metadata
    # https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=299035
    awkcheck = 'BEGIN{ok=1} { if ($0 ~ /^E: /) { ok = 0 }; print } END{exit !ok}'
    run(f'apt-ftparchive packages . | awk {shlex.quote(awkcheck)} > Packages')

    run('rm -rf by-hash')
    run('bzip2 -kf Packages')
    run('apt-ftparchive -o APT::FTPArchive::AlwaysStat="true" -o APT::FTPArchive::Release::Codename=./ -o APT::FTPArchive::Release::Acquire-By-Hash="yes" release . > Release')
    run(f'gpg --yes -abs --local-user {Config.maintainer.gpgkey} -o Release.gpg --digest-algo sha256 Release')
    run(f'gpg --yes -abs --local-user {Config.maintainer.gpgkey} --clearsign -o InRelease --digest-algo sha256 Release')

    for hsh in ['MD5Sum', 'SHA1', 'SHA256', 'SHA512']:
      run(f'mkdir -p by-hash/{hsh}')
      for pkg in ['Packages', 'Packages.bz2']:
        run(f'cp {pkg} by-hash/{hsh}/`{hsh.lower().replace("sum", "")}sum {pkg} ' + " | awk '{print $1}'`")
