#!/usr/bin/env python3

import sys, os
from util import run
from pathlib import Path
from requests import Session

from argparse import ArgumentParser
parser = ArgumentParser()
parser.add_argument('--url', required=True)
parser.add_argument('--update', action='append', default=[])
args = parser.parse_args()

META = '''---
title: Zotero/Jurism binaries for Debian-based linux systems
...
'''

## set UA for web requests
if 'true' not in args.update:
  request = Session()
  request.headers.update({ 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36' })
  baseurl = args.url
  if baseurl[-1] != '/':
    baseurl += '/'
  for asset in ['Packages']:
    asset = baseurl + asset
    response = request.get(asset)
    if response.status_code >= 400:
      print(asset, 'missing, force republish')
      args.update.append('true')
if 'true' in args.update:
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

with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
  print(f'update={"true" if "true" in args.update else "false"}', file=f)
