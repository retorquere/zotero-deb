#!/usr/bin/env python3

import os, sys
import configparser
import types
import shutil, shlex
import subprocess
import tempfile
import argparse
import re
import magic
import contextlib
import hashlib
from pathlib import Path
from colorama import Fore, Style

args = argparse.ArgumentParser(description='update Zotero deb repo.')
args.add_argument('--config', type=str, default='config.ini')
args.add_argument('--mime', type=str, default='mime.xml')
args.add_argument('staged', nargs='*')
args = args.parse_args()

# open inifile with default settings
@contextlib.contextmanager
def IniFile(path):
  ini = configparser.RawConfigParser()
  ini.optionxform=str
  ini.read(path)
  yield ini

# change directory and back
class chdir():
  def __init__(self, path):
    self.cwd = os.getcwd()
    self.path = path
  def __enter__(self):
    print('changing to', self.path)
    os.chdir(self.path)
  def __exit__(self, exc_type, exc_value, exc_traceback):
    os.chdir(self.cwd)

# context manager to open file for reading or writing, and in the case of write, create paths as required
class Open():
  def __init__(self, path, mode='r', fmode=None):
    self.path = path
    if 'w' in mode or 'a' in mode: os.makedirs(os.path.dirname(self.path), exist_ok=True)
    self.mode = fmode
    self.f = open(self.path, mode)

  def __enter__(self):
    return self.f

  def __exit__(self, exc_type, exc_value, exc_traceback):
    self.f.close()
    if self.mode is not None:
      os.chmod(self.path, self.mode)

# run shell command, error out onm failure
def run(cmd):
  print('$', Fore.GREEN + cmd, Style.RESET_ALL)
  subprocess.run(cmd, shell=True, check=True)
  print('')

# gather build config
config = types.SimpleNamespace()

# load build config from ini file
with IniFile(args.config) as ini:
  config.ini = ini
config.maintainer = config.ini['maintainer']['email']
config.gpgkey = config.ini['maintainer']['gpgkey']

# need wwwroot and repo path separate so the right subdir of wwwroot is written to. These are both full paths, but the repo path must be inside the wwwroot
config.path = types.SimpleNamespace(**{ key: os.path.abspath(path) for key, path in config.ini['path'].items() })
assert config.path.wwwroot == config.path.repo or Path(config.path.wwwroot) in Path(config.path.repo).parents, 'repo must be in wwwroot'

# remove trailing slash from staged directories since it messes with basename
config.staged = [ re.sub(r'/$', '', staged) for staged in args.staged ]

# loop through all staged directories (can be one, or none)
for staged in config.staged:
  assert os.path.isdir(staged)

  # gather metadata for the deb file
  deb = types.SimpleNamespace()

  # get version and package name
  with IniFile(os.path.join(staged, 'application.ini')) as ini:
    deb.vendor = ini['App']['Vendor'] # vendor instead of app name because jurism uses the same appname
    deb.package = deb.client = deb.vendor.lower()
    deb.version = ini['App']['Version']
    if '-beta' in deb.version:
      deb.package += '-beta'
      # https://bugs.launchpad.net/ubuntu/+source/dpkg/+bug/1701756/comments/3. + and ~ get escaped in URLs, ':' is seen as an epoch, . is going to cause problems, - is reserved for bumps
      deb.version = deb.version.replace('-beta', '').replace('+', 'B')

  # detect arch from zotero-bin/jurism-bin
  arch = magic.from_file(os.path.join(staged, deb.client + '-bin'))
  if arch.startswith('ELF 32-bit LSB executable, Intel 80386,'):
    deb.arch = 'i386'
  elif arch.startswith('ELF 64-bit LSB executable, x86-64,'):
    deb.arch = 'amd64'
  else:
    print('unsupported architecture', arch)
    sys.exit(1)

  with tempfile.TemporaryDirectory() as builddir:
    print('created temporary directory', builddir)
    deb.build = builddir

    # add package "bump" version so we can offer updates for existing Zotero versions (use this to create a fix for the packaging process itself)
    if bump := config.ini[deb.client].get(deb.version):
      deb.bump = '-' + bump
    else:
      deb.bump = ''

    # get package dependencies
    if dependencies := config.ini[deb.client].get('dependencies'):
      deb.dependencies = [dep.strip() for dep in dependencies.split(',')]
    else:
      deb.dependencies = []

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
    deb.description = config.ini[deb.client]['description']
    # path to the generated deb file
    deb.deb = os.path.join(config.path.repo, f'{deb.package}_{deb.version}{deb.bump}_{deb.arch}.deb')

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
    with open(args.mime) as mime, Open(os.path.join(deb.build, 'usr/share/mime/packages', f'{deb.package}.xml'), 'w') as f:
      f.write(mime.read())

    # write build control file
    with Open(os.path.join(deb.build, 'DEBIAN/control'), 'w') as f:
      print(f'Package: {deb.package}', file=f)
      print(f'Architecture: {deb.arch}', file=f)
      print(f'Depends: {deb.dependencies}', file=f)
      print(f'Maintainer: {config.maintainer}', file=f)
      print(f'Section: {deb.section}', file=f)
      print('Priority: optional', file=f)
      print(f'Version: {deb.version}{deb.bump}', file=f)
      print(f'Description: {deb.description}', file=f)

    # create symlink to binary
    os.makedirs(os.path.join(deb.build, 'usr/local/bin'))
    os.symlink(f'/usr/lib/{deb.package}/{deb.client}', os.path.join(deb.build, 'usr/local/bin', deb.package))

    # build deb
    if os.path.exists(deb.deb):
      os.remove(deb.deb)
    os.makedirs(os.path.dirname(deb.deb), exist_ok=True)
    run(f'fakeroot dpkg-deb --build -Zgzip {shlex.quote(deb.build)} {shlex.quote(deb.deb)}')
    run(f'dpkg-sig -k {shlex.quote(config.gpgkey)} --sign builder {shlex.quote(deb.deb)}')

# rebuild repo
os.makedirs(config.path.repo, exist_ok=True)
with chdir(config.path.repo):
  # these will be recreated, but just to be sure
  run('rm -f *Package* *Release*')

  gpgkey = shlex.quote(config.gpgkey)
  repo = os.path.relpath(config.path.repo, config.path.wwwroot)

  with chdir(config.path.wwwroot):
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
