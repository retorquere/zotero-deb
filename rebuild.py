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

if Config.mode == 'apt':
  import apt as repository

## set UA for web requests
request = Session()
request.headers.update({ 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36' })

Config.repo.mkdir(parents=True, exist_ok=True)

packages = []

print('Finding Zotero versions...')
# zotero
packages += [
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
packages += [
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
print([v[:3] for v in packages])

prebuilt = set(repository.prebuilt())
packages = [ (Config.repo / repository.packagename(client, version, arch), url) for client, version, arch, url in packages ]

modified = False
allowed = set([pkg for pkg, url in packages])
for pkg in prebuilt - allowed:
  print('rebuild: delete', pkg)
  modified = True
  pkg.unlink()

Config.staged = []
for pkg, url in packages:
  if pkg.exists():
    continue
  print('rebuild: packaging', pkg)
  modified = True
  staged = Config.staging / Path(pkg).stem
  Config.staged.append(staged)
  if not staged.exists():
    staged.mkdir(parents=True)
    run(f'curl -sL {shlex.quote(url)} | tar xjf - -C {shlex.quote(str(staged))} --strip-components=1')

  repository.package(staged)

if Config.staging.exists():
  for unstage in Config.staging.iterdir():
    if unstage not in Config.staged:
      print('unstaged', unstage)
      shutil.rmtree(unstage)

if modified:
  repository.mkrepo()
  print(f'::set-output name=rebuilt::true')
