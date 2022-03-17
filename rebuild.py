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

## set UA for web requests
request = Session()
request.headers.update({ 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36' })

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

allowed = set([deb for deb, url in debs])
found = set(glob.glob(os.path.join(Config.repo.path, '*.deb')))
for deb in found - allowed:
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
  build.package(staged)

for unstage in [re.sub(r'/$', '', staged) for staged in glob.glob(os.path.join(Config.repo.staging, '*'))]:
  if unstage not in Config.repo.staged:
    print('unstaged', unstage)
    shutil.rmtree(unstage)

if modified:
  build.mkrepo()
  print(f'::set-output name=publish::true')
