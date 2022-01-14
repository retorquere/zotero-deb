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
from github3 import login as ghlogin
import html
import subprocess
from colorama import Fore, Style

import b2sdk.v2 as b2
import multiprocessing
import time

headers = { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36' }
import urllib.request
opener = urllib.request.build_opener()
opener.addheaders = [ tuple(kv) for kv in headers.items() ]
urllib.request.install_opener(opener)

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
config.beta = '~' if args.host == 'b2' else '+'

# load build config
with IniFile('config.ini') as ini:
  config.path = types.SimpleNamespace(**{ key: os.path.abspath(path) for key, path in dict(ini['path']).items() })
  bump = lambda client, version: (version + '-' + bumped) if (bumped := ini[client].get(version)) else version

assert config.path.wwwroot == config.path.repo or Path(config.path.wwwroot) in Path(config.path.repo).parents, 'repo must be in wwwroot'

def run(cmd, execute=True):
  print('$', Fore.GREEN + cmd, Style.RESET_ALL)
  if execute:
    subprocess.run(cmd, shell=True, check=True)
  print('')

class Sync:
  def __init__(self):
    self.repo = {
      'sourceforge': SimpleNamespace(remote='retorquere@frs.sourceforge.net:/home/frs/project/zotero-deb/', url='https://downloads.sourceforge.net/project/zotero-deb'),
      'b2': SimpleNamespace(remote='b2://zotero-apt', url='https://apt.retorque.re/file/zotero-apt'),
      'github': SimpleNamespace(remote='https://github.com/retorquere/zotero-deb/releases/download/apt-get', url='https://github.com/retorquere/zotero-deb/releases/download/apt-get'),
    }[args.host]
    self.repo.local = config.path.repo
    self.repo.codename = os.path.relpath(config.path.repo, config.path.wwwroot)
    self.repo.subdir = '' if self.repo.codename == '.' else self.repo.codename + '/'

    self.sync = {
      'sourceforge': self.rsync,
      'b2': self.b2sync,
      'github': self.ghsync,
    }[args.host]

  def fetch(self):
    self.sync(self.repo.remote + self.repo.subdir, self.repo.local)

  def publish(self):
    self.sync(self.repo.local, self.repo.remote + self.repo.subdir)

  def here(self):
    return set([ str(path.relative_to(self.repo.local)) for path in Path(self.repo.local).rglob('*.deb') ])

  def rsync(self, _from, _to):
    if not _from.endswith('/'): _from += '/'
    if not _to.endswith('/'): _to += '/'
    if os.environ.get('CI'):
      progress = ''
    else:
      progress = '--progress'
    run(f'rsync {progress} -e "ssh -o StrictHostKeyChecking=no" -avhz --delete {shlex.quote(_from)} {shlex.quote(_to)}')

  def b2sync(self, _from, _to):
    b2_api = b2.B2Api(b2.InMemoryAccountInfo())
    b2_api.authorize_account('production', os.environ['B2_APPLICATION_KEY_ID'], os.environ['B2_APPLICATION_KEY'])
    bucket = b2_api.get_bucket_by_name(self.repo.remote.split('/')[-1])

    ls = list(bucket.ls(latest_only=True))
    mod = { f.file_name: f.mod_time_millis for f, _ in ls if f.file_name.endswith('.deb') }
    there = set([ f.file_name for f, _ in ls if f.file_name.endswith('.deb')])
    here = self.here()

    if _from.startswith('b2:'):
      for filename in sorted(there - here):
        print('<+', self.repo.url + '/' + urlencode(filename))
        tgt = os.path.join(_to, filename)
        urllib.request.urlretrieve(self.repo.url + '/' + urlencode(filename), tgt)
        os.utime(tgt, tuple([mod[filename] / 1000] * 2))
      for filename in (here - there):
        print('<-', filename)
        os.remove(os.path.join(_to, filename))
    else:
      policies_manager = b2.ScanPoliciesManager(
        # exclude means "don't upload" which means "delete"
        #exclude_file_regexes=[ '^' + re.escape(filename) + '$' for filename in sorted(there.intersection(here)) ]
      )
      synchronizer = b2.Synchronizer(
        max_workers=10,
        policies_manager=policies_manager,
        dry_run=False,
        allow_empty_source=True,
        #compare_version_mode=b2.CompareVersionMode.NONE,
        newer_file_mode=b2.NewerFileSyncMode.REPLACE,
        keep_days_or_delete=b2.KeepOrDeleteMode.DELETE
      )
      with b2.SyncReport(sys.stdout, True) as reporter:
        synchronizer.sync_folders(
          source_folder=b2.parse_sync_folder(_from, b2_api),
          dest_folder=b2.parse_sync_folder(_to, b2_api),
          now_millis=int(round(time.time() * 1000)),
          reporter=reporter
        )

  def ghsync(self, _from, _to):
    _, _, _, owner, project, _, _, release = self.repo.url.split('/')
    release = ghlogin('', '', os.environ['GITHUB_TOKEN']).repository(owner, project).release_from_tag(release)

    here = self.here()
    there = set([asset.name for asset in release.assets()])

    if _from.startswith('http'):
      for filename in sorted(here - there):
        print('<-', filename)
        os.remove(os.path.join(_to, filename))

      for asset in release.assets():
        if asset.name in here or not asset.name.endswith('.deb'): continue
        print('<+', asset.name)
        asset.download(os.path.join(_to, asset.name))

    else:
      for asset in release.assets():
        # always delete because upload_asset does not replace
        print('->', asset.name)
        asset.delete()
      for filename in glob.glob(os.path.join(_from, '*')):
        for filename in sorted([ str(path.relative_to(self.repo.local)) for path in Path(self.repo.local).rglob('*') if os.path.isfile(str(path)) ]):
          print('->', os.path.basename(filename))
          with open(os.path.join(self.repo.local, filename), 'rb') as f:
            release.upload_asset('application/octet-stream', filename, f)
Sync=Sync()

if args.clear and os.path.exists(config.path.repo):
  shutil.rmtree(config.path.repo)
os.makedirs(config.path.repo, exist_ok=True)
Sync.fetch()

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
  ('zotero-beta', bump('zotero', unquote(re.match(r'https://download.zotero.org/client/beta/([^/]+)', url)[1]).replace('-beta', '').replace('+', config.beta)), archmap[arch], url)
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
  run(f'curl -sL {shlex.quote(url)} | tar xjf - -C {shlex.quote(staging)} --strip-components=1')
  modified = True

if args.force_send or modified:
  if args.build and modified:
    run(f'./build.py --beta {shlex.quote(config.beta)} staging/*')
  elif args.build:
    run(f'./build.py --beta {shlex.quote(config.beta)}')
  with open('install.sh') as src, open(os.path.join(config.path.repo, 'install.sh'), 'w') as tgt:
    tgt.write(src.read().format(url=Sync.repo.url, codename=Sync.repo.codename))
  with open('uninstall.sh') as src, open(os.path.join(config.path.repo, 'uninstall.sh'), 'w') as tgt:
    tgt.write(src.read().format(url=Sync.repo.url, codename=Sync.repo.codename))

  files = [f for f in os.listdir(config.path.repo) if os.path.isfile(os.path.join(config.path.repo, f))]
  with open('index.html') as src, open(os.path.join(config.path.repo, 'index.html'), 'w') as tgt:
    tgt.write(src.read().format(site=Sync.repo.url))
    print('\n<ul>', file=tgt)
    for f in sorted(files):
      print('<li><a href="' + f + '">', html.escape(f), '</a></li>', file=tgt)
    print('</ul>', file=tgt)
  if args.send or args.force_send:
    Sync.publish()
  print('::set-output name=modified::true')
else:
  print('nothing to do')
