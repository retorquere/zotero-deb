#!/usr/bin/env python3

import os, sys
import configparser
import types
import shutil, shlex
import subprocess

config = types.SimpleNamespace()
config.here = os.path.abspath(os.path.dirname(__file__))
config.source = os.path.abspath(sys.argv[1])
# remove trailing slash since it messes with basename
if config.source.endswith('/'):
  config.source = config.source[:-1]

# get arch
if os.path.basename(config.source) == 'Zotero_linux-i686':
  config.arch = 'i386'
elif os.path.basename(config.source) == 'Zotero_linux-x86_64':
  config.arch = 'amd64'
else:
  print('unknown architecture from', os.path.basename(config.source))
  sys.exit(1)

# make build directory
config.build = os.path.join(config.here, 'build')
if os.path.exists(config.build):
  shutil.rmtree(config.build)

# make repo directory
config.repo = os.path.join(config.here, 'repo')
os.makedirs(config.repo, exist_ok=True)

# get version and binary name
ini = configparser.RawConfigParser()
ini.read(os.path.join(config.source, 'application.ini'))
config.version = ini['App']['Version']
if '-beta' in config.version:
  config.binary = 'zotero-beta'
else:
  config.binary = 'zotero'

# load config
ini = configparser.RawConfigParser()
ini.read(os.path.join(config.here, 'config.ini'))
config.maintainer = ini['maintainer']['email']
config.gpgkey = ini['maintainer']['gpgkey']
config.bump = ''
config.dependencies = []
if 'deb' in ini:
  if config.version in ini['deb']:
    config.bump = '-' + ini['deb'][config.version]
  if 'dependencies' in ini['deb']:
    config.dependencies = [dep.strip() for dep in ini['deb']['dependencies'].split(',')]
for dep in os.popen('apt-cache depends firefox-esr').read().split('\n'):
  dep = dep.strip()
  if not dep.startswith('Depends:'): continue
  dep = dep.split(':')[1].strip()
  if dep == 'lsb-release': continue # why should it need this?
  if 'gcc' in dep: continue #43
  config.dependencies.append(dep)
config.dependencies = ', '.join(sorted(list(set(config.dependencies))))
config.description = ini['deb']['description']
config.deb = os.path.join(config.repo, f'{config.binary}_{config.version}{config.bump}_{config.arch}.deb')

# copy zotero to the build directory, excluding the desktpo file (which we'll recreate later) and the update files
os.makedirs(os.path.join(config.build, 'usr/lib'), exist_ok=True)
shutil.copytree(config.source, os.path.join(config.build, 'usr/lib', config.binary), ignore=shutil.ignore_patterns('zotero.desktop', 'active-update.xml', 'precomplete', 'removed-files', 'updates', 'updates.xml'))
if config.binary != 'zotero':
  shutil.move(os.path.join(config.build, 'usr/lib', config.binary, 'zotero'), os.path.join(config.build, 'usr/lib', config.binary, config.binary))

class Open():
  def __init__(self, path, mode='r', fmode=None):
    self.path = os.path.join(config.build, path)
    if 'w' in mode or 'a' in mode: os.makedirs(os.path.dirname(self.path), exist_ok=True)
    self.mode = fmode
    self.f = open(self.path, mode)

  def __enter__(self):
    return self.f

  def __exit__(self, exc_type, exc_value, exc_traceback):
    self.f.close()
    if self.mode is not None:
      os.chmod(self.path, self.mode)

# disable auto-update
with Open(f'usr/lib/{config.binary}/defaults/pref/local-settings.js', 'a') as ls, Open(f'usr/lib/{config.binary}/mozilla.cfg', 'a') as cfg:
  # enable mozilla.cfg
  if ls.tell() != 0: print('', file=ls)
  print('pref("general.config.obscure_value", 0); // only needed if you do not want to obscure the content with ROT-13', file=ls)
  print('pref("general.config.filename", "mozilla.cfg");', file=ls)

  # disable auto-update
  if cfg.tell() == 0:
    print('//', file=cfg)
  else:
    print('', file=cfg)
  print('lockPref("app.update.enabled", false);', file=cfg)
  print('lockPref("app.update.auto", false);', file=cfg)

# create desktop file
ini = configparser.RawConfigParser()
ini.optionxform=str
ini.read(os.path.join(config.source, 'zotero.desktop'))
config.section = ini['Desktop Entry']['Categories'].rstrip(';')
ini.set('Desktop Entry', 'Exec', f'/usr/lib/{config.binary}/{config.binary} --url %u')
ini.set('Desktop Entry', 'Icon', f'/usr/lib/{config.binary}/chrome/icons/default/default256.png')
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
ini.set('Desktop Entry', 'Description', config.description)
with Open(f'usr/share/applications/{config.binary}.desktop', 'w') as f:
  ini.write(f, space_around_delimiters=False)

# add mime info
with open(os.path.join(config.here, 'mime.xml')) as mime, Open(f'usr/share/mime/packages/{config.binary}.xml', 'w') as f:
  f.write(mime.read())

#write build control file
with Open('DEBIAN/control', 'w') as f:
  print(f'Package: {config.binary}', file=f)
  print(f'Architecture: {config.arch}', file=f)
  print(f'Depends: {config.dependencies}', file=f)
  print(f'Maintainer: {config.maintainer}', file=f)
  print(f'Section: {config.section}', file=f)
  print('Priority: optional', file=f)
  print(f'Version: {config.version}{config.bump}', file=f)
  print(f'Description: {config.description}', file=f)

# create symlink to binary
os.makedirs(os.path.join(config.build, 'usr/local/bin'))
os.symlink(f'/usr/lib/{config.binary}/{config.binary}', f'build/usr/local/bin/{config.binary}')

def run(cmd):
  print('$', cmd)
  print(subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8'))

# build deb
if os.path.exists(config.deb):
  os.remove(config.deb)
run(f'fakeroot dpkg-deb --build -Zgzip {shlex.quote(config.build)} {shlex.quote(config.deb)}')
run(f'dpkg-sig -k {shlex.quote(config.gpgkey)} --sign builder {shlex.quote(config.deb)}')

# rebuild repo
repo = shlex.quote(config.repo)
gpgkey = shlex.quote(config.gpgkey)
deb_gpg_key = shlex.quote(os.path.join(config.repo, 'deb.gpg.key'))
packages = shlex.quote(os.path.join(config.repo, "Packages"))
release = shlex.quote(os.path.join(config.repo, "Release"))
release_gpg = shlex.quote(os.path.join(config.repo, "Release.gpg"))
inrelease = shlex.quote(os.path.join(config.repo, "InRelease"))
run(f'gpg --armor --export {gpgkey} > {deb_gpg_key}')
run(f'cd {repo} && apt-ftparchive packages . > {packages}')
run(f'bzip2 -kf {packages}')
run(f'cd {repo} && apt-ftparchive release . > Release')
run(f'gpg --yes -abs -u {gpgkey} -o {release_gpg} --digest-algo sha256 {release}')
run(f'gpg --yes -abs -u {gpgkey} --clearsign -o {inrelease} --digest-algo sha256 {release}')
