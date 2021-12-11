#!/usr/bin/env python3

from urllib.request import urlopen
import json
from urllib.parse import quote_plus as urlencode, unquote
import re
import os
import configparser
import glob
import shlex
import shutil
from pathlib import Path
from types import SimpleNamespace

repo = SimpleNamespace(local='./repo/', remote='retorquere@frs.sourceforge.net:/home/frs/project/zotero-deb/')

def system(cmd):
  print(cmd)
  os.system(cmd)

def rsync(_from, _to):
  return f'rsync --progress -e "ssh -o StrictHostKeyChecking=no" -avhz --delete {shlex.quote(_from)} {shlex.quote(_to)}'

system(rsync(repo.remote, repo.local))

def load(url,parse_json=False):
  response = urlopen(url).read()
  if type(response) is bytes: response = response.decode('utf-8')
  if parse_json:
    return json.loads(response)
  else:
    return response

config = configparser.RawConfigParser()
config.read('config.ini')
bump = lambda client, version, beta=None: (version + '-' + bumped) if (bumped := config[client].get(beta or version)) else version

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
  ('zotero-beta', bump('zotero', unquote(re.match(r'https://download.zotero.org/client/beta/([^/]+)', url)[1]).replace('-beta', ''), 'beta'), archmap[arch], url)
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

debs = [ (f'repo/{client}_{version}_{arch}.deb', url) for client, version, arch, url in debs ]

modified = False
for deb in glob.glob('repo/*.deb'):
  if not deb in [_deb for _deb, _url in debs]:
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

with open('send.sh', 'w') as f:
  if modified:
    print('./build.py staging', file=f)
    print('cp install.sh repo', file=f)
    print(rsync(repo.local, repo.remote), file=f)
    print('::set-output name=modified::true')
  else:
    print('echo nothing to do', file=f)
  
