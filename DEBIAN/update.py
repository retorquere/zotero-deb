#!/usr/bin/env python

import platform
import glob
import argparse
import re
import json
import os
import sys
import tempfile
import socket
import subprocess

if sys.version_info[0] >= 3:
  from urllib.request import urlopen
  from html.parser import HTMLParser
  from urllib.request import urlretrieve
  from http.client import HTTPSConnection
else:
  from urllib2 import urlopen
  from HTMLParser import HTMLParser
  from urllib import urlretrieve
  from httplib import HTTPSConnection
  input = raw_input
  ConnectionRefusedError = socket.error

def zotero_latest():
  response = urlopen('https://www.zotero.org/download/').read()
  if type(response) is bytes: response = response.decode("utf-8")
  for line in response.split('\n'):
    if not '"standaloneVersions"' in line: continue
    line = re.sub(r'.*Downloads,', '', line)
    line = re.sub(r'\),', '', line)
    versions = json.loads(line)
    return versions['standaloneVersions']['linux-' + platform.machine()]

def jurism_latest():
  release = HTTPSConnection('our.law.nagoya-u.ac.jp')
  try:
    release.request('GET', '/jurism/dl?channel=release&platform=linux-' + platform.machine())
  except ConnectionRefusedError as e:
    if args.cache is not None:
      return 'cached'
    else:
      raise e

  release = release.getresponse()
  release = release.getheader('Location')

  if release is None and args.cache is not None: return 'cached'

  return release.split('/')[-2]

def validate(name, value, options, allowpath = False):
  if allowpath and value[0] in ['/', '.', '~']: return os.path.abspath(os.path.expanduser(value))

  value = re.sub(r"[^a-z0-9]", '', value.lower())

  for option in options:
    if option[:len(value)] == value: return option

  options = ['"' + option + '"' for option in options]
  if allowpath: options.push('a path of your choosing')
  raise Exception('Unexpected ' + name + ' "' + value + '", expected ' + ' / '.join(options))

class DataDirAction(argparse.Action):
  options = ['profile', 'home']

  def __call__(self, parser, namespace, values, option_string=None):
    try:
      setattr(namespace, self.dest, self.__class__.validate(values))
    except Exception as err:
      parser.error(err)

  @classmethod
  def validate(cls, value):
    return validate('data directory', value, cls.options)

class LocationAction(argparse.Action):
  options = ['local', 'global']

  def __call__(self, parser, namespace, values, option_string=None):
    try:
      setattr(namespace, self.dest, self.__class__.validate(values))
    except Exception as err:
      parser.error(err)

  @classmethod
  def validate(cls, value):
    return validate('install location', value, cls.options, True)

class ClientAction(argparse.Action):
  options = ['zotero', 'jurism']

  def __call__(self, parser, namespace, values, option_string=None):
    try:
      setattr(namespace, self.dest, self.__class__.validate(values))
    except Exception as err:
      parser.error(err)

  @classmethod
  def validate(cls, value):
    return validate('client', value, cls.options)

installdir_local = os.path.expanduser('~/bin')
installdir_global = '/opt'

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--client', action=ClientAction, help='select Zotero client to download and install, either Zotero or Juris-M')
parser.add_argument('--deb', action=ClientAction, help='prepare deb package for Zotero client, either Zotero or Juris-M')
parser.add_argument('-v', '--version', default='latest', help='install the given version rather than the latest')
parser.add_argument('-l', '--location', action=LocationAction, help="location to install, either 'local' (" + installdir_local + ") or 'global' (" + installdir_global + ')')
parser.add_argument('-r', '--replace', action='store_true', help='replace Zotero at selected install location if it exists there')
parser.add_argument('-p', '--picker', action='store_true', help='Start Zotero with the profile picker')
parser.add_argument('-d', '--datadir', default='home', action=DataDirAction, help="Zotero data location, either 'profile' or 'home'")
parser.add_argument('--cache', help='cache downloaded installer in this directory. Use this if you expect to re-install Zotero often')

args = parser.parse_args()

if args.deb and args.client:
  print('use either --client or --deb but not both')
  sys.exit(1)

if args.deb:
  args.client = args.deb
  args.location = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'usr', 'lib'))
  args.replace = True
  args.menudir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'usr', 'share', 'applications'))
  args.installdir = os.path.join('/usr/lib', args.client)
else:
  args.control = None
  args.menudir = None
  args.installdir = None

if args.client is None:
  args.client = ClientAction.validate(input("Client to install ('zotero'* or 'juris-m'): ") or 'zotero')

if args.version == 'latest' or args.version is None:
  version = zotero_latest() if args.client == 'zotero' else jurism_latest()
  if args.version is None:
    args.version = input(args.client + ' version (' + version + '): ') or version
  else:
    args.version = version

if args.datadir is None:
  if args.client == 'jurism':
    args.datadir = 'home'
  else:
    args.datadir = DataDirAction.validate(input("Data directory ('home'* or 'profile'): ") or 'home')
if args.datadir == 'profile' and args.client == 'jurism': raise Exception('datadir profile not supported by Juris-M')

if args.location is None:
  args.location = LocationAction.validate(input("Location to install ('local'*, 'global', or absolute path): ") or 'local')
if args.location == 'local':
  installdir = os.path.join(installdir_local, args.client)
  args.menudir = os.path.expanduser('~/.local/share/applications')
elif args.location == 'global':
  installdir = os.path.join(installdir_global, args.client)
  args.menudir = '/usr/share/applications'
else:
  installdir = os.path.join(args.location, args.client)

if args.cache is not None and not os.path.exists(args.cache):
  print(args.cache + ' does not exist')
  sys.exit(1)

if args.client == 'zotero':
  if args.version == 'beta':
    args.url = "https://www.zotero.org/download/client/dl?channel=beta&platform=linux-" + platform.machine()
  else:
    args.url = "https://www.zotero.org/download/client/dl?channel=release&platform=linux-" + platform.machine() + '&version=' + args.version
else:
  args.url = 'https://our.law.nagoya-u.ac.jp/jurism/dl?channel=release&platform=linux-' + platform.machine() + '&version=' + args.version

if args.version == 'cached':
  tarball = None
  for candidate in glob.glob(os.path.join(args.cache, args.client + '-*.tar.bz2')):
    tarball = candidate
  if tarball is None:
    raise Exception('No cached ' + args.client + ' found in ' + args.cache)
  print('Using cached ' + tarball + ' without checking for newer versions')
else:
  if args.cache is None:
    tarball = tempfile.NamedTemporaryFile().name
  else:
    tarball = args.client + '-' + platform.machine() + '-' + args.version + '.tar.bz2'
    print('Looking for ' + tarball)
    for junk in glob.glob(os.path.join(args.cache, args.client + '-*.tar.bz2')):
      if os.path.basename(junk) != tarball:
        print('Removing obsolete ' + junk)
        os.remove(junk)
    tarball = os.path.join(args.cache, tarball)

  if os.path.exists(tarball):
    print('Retaining ' + tarball)
  else:
    print("Downloading " + args.client + ' ' + args.version + ' for ' + platform.machine() + ' from ' + args.url + ' to ' + tarball)
    # python on Travis is positively ancient and cannot download https files...
    urlretrieve(args.url, tarball)
    # print(subprocess.check_output(['curl', '-L', '-o', tarball, args.url]))

if os.path.exists(installdir) and not args.replace: raise Exception('Installation directory "' + installdir + '" exists')

extracted = tempfile.mkdtemp()

def shellquote(s):
  return "'" + s.replace("'", "'\\''") + "'"
os.system('tar --strip 1 -xpf ' + shellquote(tarball) + ' -C ' + shellquote(extracted))

if os.path.exists(installdir): os.system('rm -rf ' + shellquote(installdir))
os.system('mkdir -p ' + shellquote(os.path.dirname(installdir)))
os.system('mv ' + shellquote(extracted) + ' ' + shellquote(installdir))

if not args.menudir is None:
  if not os.path.exists(args.menudir): os.system('mkdir -p ' + shellquote(args.menudir))
  with open(os.path.join(args.menudir, args.client + '.desktop'), 'w') as desktop:
    if args.installdir: installdir = args.installdir

    desktop.write("[Desktop Entry]\n")
    if args.client == 'zotero':
      desktop.write("Name=Zotero\n")
    else:
      desktop.write("Name=Juris-M\n")

    client = args.client
    if args.datadir == 'profile':
      client = client + ' -datadir profile'
    if args.picker:
      client = client + ' -P'
    desktop.write("Comment=Open-source reference manager\n")
    desktop.write("Exec=" + installdir + '/' + client + "\n")
    desktop.write("Icon=" + installdir + "/chrome/icons/default/default48.png\n")
    desktop.write("Type=Application\n")
    desktop.write("StartupNotify=true")

if args.deb:
  with open(os.path.abspath(os.path.join(os.path.dirname(__file__), 'control')), 'w') as f:
    architecture = platform.machine()
    if architecture == 'x86_64':
      architecture = 'amd64'
    else:
      print('Unexpected architecture ' + architecture)
      sys.exit(1)

    f.write("Package: " + args.client + "\n")
    f.write("Architecture: " + architecture + "\n")
    f.write("Maintainer: @retorquere\n")
    f.write("Priority: optional\n")
    f.write("Version: " + args.version + "\n")
    if args.client == 'zotero':
      f.write("Description: Zotero\n")
    else:
      f.write("Description: Juris-M\n")

  packagedir = os.path.abspath(os.path.join(os.path.dirname(os.path.join(__file__)), '..'))
  packagename = '_'.join([args.client, args.version, architecture]) + '.deb'
  package = os.path.join(packagedir, '..', packagename)
  if os.path.exists(package): os.remove(package)

  os.chdir(os.path.abspath(os.path.join(packagedir, '..')))
  os.system('dpkg-deb --build ' + shellquote(os.path.basename(packagedir)) + ' ' + shellquote(packagename))
