#!/usr/bin/env python3

import sys, os
from util import run
from pathlib import Path
from requests import Session

BASEURL = 'https://zotero.retorque.re/file/apt-package-archive'
URL = sys.argv[1]
UPDATE = sys.argv[2]
META = '''---
title: Zotero/Jurism binaries for Debian-based linux systems
...
'''

## set UA for web requests
update = '_true_' in UPDATE
if not update:
  request = Session()
  request.headers.update({ 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36' })
  baseurl = URL
  if baseurl[-1] != '/':
    baseurl += '/'
  for asset in ['Packages']:
    asset = baseurl + asset
    response = request.get(asset)
    if response.status_code >= 400:
      print(asset, 'missing, force republish')
      update = True
if not update:
  sys.exit(1) # confusing, but returning an "error" here will cause the exit code to be falsish and *not* force a rebuild

with open('README.md') as f:
  readme = META + f.read()

repo = Path(os.environ['REPO'])
readme += '\n---\n\n'
for asset in sorted(repo.rglob('*'), key=lambda f: str(f)):
  if asset.is_file():
    asset = str(asset.relative_to(repo))
    assetname = asset.replace('_', '\\_')
    readme += f'* [{assetname}]({asset})\n'

with open('index.md', 'w') as f:
  f.write(readme)
run('pandoc index.md -s --css pandoc.css -o index.html')
