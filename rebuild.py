#!/usr/bin/env python3

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

from requests import Session
import os, sys
import argparse
from urllib.parse import quote_plus as urlencode, unquote
import re
import glob
import shutil
from pathlib import Path
import shlex
#import configparser
#import contextlib
#import types
#from github3 import login as ghlogin
import html

from util import run, Config
import build
from b2 import Sync

## set UA for web requests
request = Session()
request.headers.update({ 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36' })

parser = argparse.ArgumentParser()
parser.add_argument('--no-fetch', dest='fetch', action='store_false', default=True)
parser.add_argument('--no-send', dest='send', action='store_false', default=True)
parser.add_argument('--sync', dest='sync', action='store_true', default=False)
parser.add_argument('--clean', dest='clean', action='store_true', default=False)
parser.add_argument('--no-build', dest='build', action='store_false', default=True)
parser.add_argument('--mirror', action='store_true')
parser.add_argument('--clear', action='store_true')
args = parser.parse_args()

assert not args.clear or not args.mirror, 'cannot clear for mirror'
## might have to rebuild for beta's on SF and GH
# config.beta = '~' if args.host == 'b2' else '+'

## clear for a full rebuild
if args.clear and os.path.exists(Config.repo.path):
  shutil.rmtree(Config.repo.path)
os.makedirs(Config.repo.path, exist_ok=True)

debs = []

print('Finding Zotero versions...')
# zotero
debs += [
  ('zotero', Config.zotero.bumped(release['version']), Config.archmap[arch], f'https://www.zotero.org/download/client/dl?channel=release&platform=linux-{arch}&version={release["version"]}')
  for release in request.get('https://www.zotero.org/download/client/manifests/release/updates-linux-x86_64.json').json()
  for arch in [ 'i686', 'x86_64' ]
] + [
  ('zotero-beta', Config.zotero.bumped(unquote(re.match(r'https://download.zotero.org/client/beta/([^/]+)', url)[1]).replace('-beta', '')), Config.archmap[arch], url)
  for arch, url in [
    (arch, request.get(f'https://www.zotero.org/download/standalone/dl?platform=linux-{arch}&channel=beta').url)
    for arch in [ 'i686', 'x86_64' ]
  ]
]

print('Finding Juris-M versions...')
# jurism
debs += [
  ('jurism', Config.jurism.bumped(version), Config.archmap[arch], f'https://github.com/Juris-M/assets/releases/download/client%2Frelease%2F{version}/Jurism-{version}_linux-{arch}.tar.bz2')

  for version in ({
    version.rsplit('m', 1)[0] : version
    for version in sorted([
      version
      for version in request.get('https://github.com/Juris-M/assets/releases/download/client%2Freleases%2Fincrementals-linux/incrementals-release-linux').text.split('\n')
      if version != ''
    ], key=lambda k: tuple([int(v) for v in re.split('[m.]', k)]))
  }.values())
  for arch in [ 'i686', 'x86_64' ]
]

debs = [ (os.path.join(Config.repo.path, f'{client}_{version}_{arch}.deb'), url) for client, version, arch, url in debs ]
# fetch what we can so we don't have to rebuild
b2sync = Sync()

modified = set(b2sync.remote) != set([deb for deb, url in debs])
if not args.sync and not modified:
  print('nothing to do')
  sys.exit()

print('Rehydrate')
b2sync.fetch()

for deb in (set(glob.glob(os.path.join(Config.repo.path, '*.deb'))) - set( [_deb for _deb, _url in debs])):
  print('delete', deb)
  modified = True
  os.remove(deb)

Config.repo.staged = []
for deb, url in debs:
  if os.path.exists(deb):
    continue
  print('## building', deb)
  modified = True
  staged = os.path.join(Config.repo.staging, Path(deb).stem)
  # remove trailing slash from staged directories since it messes with basename
  Config.repo.staged.append(re.sub(r'/$', '', staged))
  print('staging', staged)
  if not os.path.exists(staged):
    os.makedirs(staged)
    run(f'curl -sL {shlex.quote(url)} | tar xjf - -C {shlex.quote(staged)} --strip-components=1')
  build.package(staged, '+')
if args.clean:
  for unstage in [re.sub(r'/$', '', staged) for staged in glob.glob(os.path.join(Config.repo.staging, '*'))]:
    if unstage not in Config.repo.staged:
      print('unstaged', unstage)
      shutil.rmtree(unstage)

if not args.sync and not modified:
  print('again nothing to do')
  sys.exit()

if args.build or modified:
  build.rebuild()

with open('install.sh') as src, open(os.path.join(Config.repo.path, 'install.sh'), 'w') as tgt:
  tgt.write(src.read().format(baseurl=Config.repo.url.replace(f'/{Config.repo.bucket}', ''), codename=Config.repo.bucket))
with open('uninstall.sh') as src, open(os.path.join(Config.repo.path, 'uninstall.sh'), 'w') as tgt:
  tgt.write(src.read())

files = [f for f in os.listdir(Config.repo.path) if os.path.isfile(os.path.join(Config.repo.path, f))]
with open('index.html') as src, open(os.path.join(Config.repo.path, 'index.html'), 'w') as tgt:
  tgt.write(src.read().format(site=Config.repo.url))
  print('\n<ul>', file=tgt)
  for f in sorted(files):
    print('<li><a href="' + f + '">', html.escape(f), '</a></li>', file=tgt)
  print('</ul>', file=tgt)

if args.send or args.force_send:
  b2sync.update()
print(f'::set-output name=bucket::{Config.repo.bucket}')
