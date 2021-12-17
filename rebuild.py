#!/usr/bin/env python3

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

from urllib.request import urlopen
import json
from urllib.parse import quote_plus as urlencode, unquote
import re
import os, sys
import configparser
import glob
import shlex
import shutil
from pathlib import Path
from types import SimpleNamespace
import argparse
import contextlib
import types

parser = argparse.ArgumentParser()
parser.add_argument('--no-fetch', dest='fetch', action='store_false', default=True)
parser.add_argument('--no-send', dest='send', action='store_false', default=True)
parser.add_argument('--no-build', dest='build', action='store_false', default=True)
parser.add_argument('--clear', action='store_true')
parser.add_argument('--host', default='sourceforge')
parser.add_argument('--force-send', action='store_true')
args = parser.parse_args()

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

config = types.SimpleNamespace()

# load build config
with IniFile('config.ini') as ini:
  config.path = types.SimpleNamespace(**{ key: os.path.abspath(path) for key, path in dict(ini['path']).items() })
  bump = lambda client, version: (version + '-' + bumped) if (bumped := ini[client].get(version)) else version

assert config.path.wwwroot == config.path.repo or Path(config.path.wwwroot) in Path(config.path.repo).parents, 'repo must be in wwwroot'

def system(cmd, execute=True):
  if execute:
    print(cmd)
    if (exitcode := os.system(cmd)) != 0:
      sys.exit(exitcode)
  else:
    print('#', cmd)

class Sync:
  def __init__(self):
    self.repo = {
      'sourceforge': SimpleNamespace(remote='retorquere@frs.sourceforge.net:/home/frs/project/zotero-deb/', url='https://downloads.sourceforge.net/project/zotero-deb'),
      'b2': SimpleNamespace(remote='b2://zotero-apt/', url='https://apt.retorque.re/file/zotero-apt'),
      'github': SimpleNamespace(remote='https://github.com/retorquere/zotero-deb/releases/download/apt-get', url='https://github.com/retorquere/zotero-deb/releases/download/apt-get'),
    }[args.host]
    self.repo.local = config.path.repo
    self.repo.codename = os.path.relpath(config.path.repo, config.path.wwwroot)
    self.repo.subdir = '' if self.repo.codename == '.' else self.repo.codename + '/'

    self.sync = {
      'sourceforge': self.rsync,
      'b2': self.b2sync,
      'github': self.ghrelease,
    }[args.host]

  def fetch(self):
    return self.sync(self.repo.remote + self.repo.subdir, self.repo.local)

  def publish(self):
    return self.sync(self.repo.local, self.repo.remote + self.repo.subdir)

  def rsync(self, _from, _to):
    if not _from.endswith('/'): _from += '/'
    if not _to.endswith('/'): _to += '/'
    return f'rsync --progress -e "ssh -o StrictHostKeyChecking=no" -avhz --delete {shlex.quote(_from)} {shlex.quote(_to)}'

  def b2sync(self, _from, _to):
    return f'./bin/b2-linux sync --replaceNewer --delete {shlex.quote(_from)} {shlex.quote(_to)}'

  def ghrelease(self, _from, _to):
    if _from.startswith('http'):
      _, _, _, owner, repo, _, _, release = _from.split('/')
      return f'cd {shlex.quote(_from} && githubrelease asset {owner}/{repo} download {release}'
    else:
      _, _, _, owner, repo, _, _, release = _to.split('/')
      return f'cd {shlex.quote(_from} && githubrelease asset {owner}/{repo} upload {release} *'

Sync=Sync()

if args.clear:
  if os.path.exists(config.path.repo):
    shutil.rmtree(config.path.repo)
  os.makedirs(config.path.repo)

os.makedirs(config.path.repo, exist_ok=True)
system(Sync.fetch())

def load(url,parse_json=False):
  response = urlopen(url).read()
  if type(response) is bytes: response = response.decode('utf-8')
  if parse_json:
    return json.loads(response)
  else:
    return response

archmap = {
  'i686': 'i386',
  'x86_64': 'amd64',
}

debs = []

# zotero
debs += [
  ('zotero', bump('zotero', release['version']), archmap[arch], f'https://www.zotero.org/download/client/dl?channel=release&platform=linux-{arch}&version={release["version"]}')
  for release in load('https://www.zotero.org/download/client/manifests/release/updates-linux-x86_64.json', parse_json=True)
  for arch in [ 'i686', 'x86_64' ]
] + [
  ('zotero-beta', bump('zotero', unquote(re.match(r'https://download.zotero.org/client/beta/([^/]+)', url)[1]).replace('-beta', '')), archmap[arch], url)
  for arch, url in [
    (arch, urlopen(f'https://www.zotero.org/download/standalone/dl?platform=linux-{arch}&channel=beta').geturl())
    for arch in [ 'i686', 'x86_64' ]
  ]
]

# jurism
debs += [
  ('jurism', bump('jurism', version), archmap[arch], f'https://github.com/Juris-M/assets/releases/download/client%2Frelease%2F{version}/Jurism-{version}_linux-{arch}.tar.bz2')
  
  for version in ({
    version.rsplit('m', 1)[0] : version
    for version in sorted([
      version
      for version in load('https://github.com/Juris-M/assets/releases/download/client%2Freleases%2Fincrementals-linux/incrementals-release-linux').split('\n')
      if version != ''
    ], key=lambda k: tuple([int(v) for v in re.split('[m.]', k)]))
  }.values())
  for arch in [ 'i686', 'x86_64' ]
]

print(config)
debs = [ (os.path.join(config.path.repo, f'{client}_{version}_{arch}.deb'), url) for client, version, arch, url in debs ]

modified = False

for deb in (set(glob.glob(os.path.join(config.path.repo, '*.deb'))) - set( [_deb for _deb, _url in debs])):
  print('delete', deb)
  os.remove(deb)
  modified = True

if os.path.exists('staging'):
  shutil.rmtree('staging')
for deb, url in debs:
  if os.path.exists(deb):
    continue
  staging = os.path.join('staging', Path(deb).stem)
  os.makedirs(staging)
  print('staging', staging)
  system(f'curl -sL {shlex.quote(url)} | tar xjf - -C {shlex.quote(staging)} --strip-components=1')
  modified = True

if args.force_send or modified:
  if args.build and modified:
    system('./build.py staging/*')
  elif args.build:
    system('./build.py')
  with open('install.sh') as src, open(os.path.join(config.path.repo, 'install.sh'), 'w') as tgt:
    tgt.write(src.read().format(url=Sync.repo.url, codename=Sync.repo.codename))
  system(Sync.publish(), args.send or args.force_send)
  print('::set-output name=modified::true')
else:
  print('echo nothing to do')
