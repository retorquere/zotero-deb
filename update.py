#!/usr/bin/env python3

import sys, os
from util import run
from pathlib import Path
from requests import Session

BASEURL = 'https://zotero.retorque.re/file/apt-package-archive'
URL = sys.argv[1]
UPDATE = sys.argv[2]
SEP = '----'
META = '''---
title: Zotero/Jurism binaries for Debian-based linux systems
...
'''

## set UA for web requests
update = '_true_' in UPDATE
if not update:
  request = Session()
  request.headers.update({ 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36' })
  packages = URL
  if packages[-1] != '/':
    packages += '/'
  packages += 'Packages'
  response = request.get(packages)
  update = response.status_code >= 400:
  if update:
    print(packages, 'missing, force republish')
if not update:
  sys.exit(1) # confusing, but returning an "error" here will cause the exit code to be falsish and *not* force a rebuild

with open('README.md') as f:
  header, body = f.read().split(SEP, 1)
  readme = META + header + SEP + body.replace(BASEURL, URL)

repo = Path(os.environ['REPO'])
readme += '\n---\n\n'
for asset in sorted(repo.rglob('*'), key=lambda f: str(f)):
  if asset.is_file():
    asset = str(asset.relative_to(repo))
    assetname = asset.replace('_', '\\_')
    readme += f'* [{assetname}]({URL}/{asset})\n'

with open('index.md', 'w') as f:
  f.write(readme)
run('pandoc index.md -s --css pandoc.css -o index.html')

with open('install.sh', 'w') as f:
  f.write(f"""
# https://wiki.debian.org/DebianRepository/UseThirdParty

case `uname -m` in
  "i386" | "i686" | "x86_64")
    ;;
  *)
    echo "Zotero is only available for architectures i686 and x86_64"
    exit
    ;;
esac

export GNUPGHOME="/dev/null"

KEYNAME=zotero-archive-keyring.gpg
GPGKEY=https://raw.githubusercontent.com/retorquere/zotero-deb/master/$KEYNAME
KEYRING=/usr/share/keyrings/$KEYNAME
if [ -x "$(command -v curl)" ]; then
  sudo curl -L $GPGKEY -o $KEYRING
elif [ -x "$(command -v wget)" ]; then
  sudo wget -O $KEYRING $GPGKEY
else
  echo "Error: need wget or curl installed." >&2
  exit 1
fi

sudo chmod 644 $KEYRING
# old key with too broad reach
sudo rm -f /etc/apt/trusted.gpg.d/zotero.gpg

cat << EOF | sudo tee /etc/apt/sources.list.d/zotero.list
deb [signed-by=$KEYRING by-hash=force] {URL} ./
EOF

sudo apt-get clean
""")
