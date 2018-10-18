#!/usr/bin/env python3

import platform
import re
import json
import os
import sys
import glob

maintainer = 'emiliano.heyns@iris-advies.com'
component = 'main'

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

def run(cmd):
  print("\n$ " + cmd)
  os.system(cmd)

def write(filename, lines):
  print(f"# writing {filename}\n")

  with open(filename, 'w') as f:
    for line in lines:
      f.write(line + "\n")

def build(client, arch, version, url):
  packagename = f'sf/{"_".join([client, version, arch])}.deb'
  if os.path.exists(packagename):
    print(f"# not rebuilding {packagename}\n")
    return

  print(f"# Building {packagename}\n")

  run(f'rm -rf build client.tar.bz2 {packagename}')
  run(f'mkdir -p build/usr/lib/{client} build/usr/share/applications build/DEBIAN')
  run(f'curl -L -o client.tar.bz2 "{url}"')
  run(f'tar --strip 1 -xpf client.tar.bz2 -C build/usr/lib/{client}')

  name = {'zotero': 'Zotero', 'jurism': 'Juris-M'}[client]

  write(f'build/usr/share/applications/{client}.desktop', [
    '[Desktop Entry]',
    'Name=Zotero',
    f'Name={name}',
    'Comment=Open-source reference manager',
    f'Exec=/usr/lib/{client}/{client}',
    f'Icon=/usr/lib/{client}/chrome/icons/default/default48.png',
    'Type=Application',
    'StartupNotify=true',
  ])

  write('build/DEBIAN/control', [
    f'Package: {client}',
    f'Architecture: {arch}',
    f'Maintainer: {maintainer}',
    'Section: Science',
    'Priority: optional',
    f'Version: {version}',
    f'Description: {name} is a free, easy-to-use tool to help you collect, organize, cite, and share research',
  ])

  run(f'dpkg-deb --build -Zgzip build {packagename}')

run('mkdir -p sf')

response = urlopen('https://www.zotero.org/download/').read()
if type(response) is bytes: response = response.decode("utf-8")
for line in response.split('\n'):
  if not '"standaloneVersions"' in line: continue
  line = re.sub(r'.*Downloads,', '', line)
  line = re.sub(r'\),', '', line)
  versions = json.loads(line)
  zotero = versions['standaloneVersions'][f'linux-{platform.machine()}']
  break

build('zotero', 'amd64', zotero, f'https://www.zotero.org/download/client/dl?channel=release&platform=linux-x86_64&version={zotero}')
build('zotero', 'i386', zotero, f'https://www.zotero.org/download/client/dl?channel=release&platform=linux-i686&version={zotero}')

release = HTTPSConnection('our.law.nagoya-u.ac.jp')
release.request('GET', f'/jurism/dl?channel=release&platform=linux-{platform.machine()}')
release = release.getresponse()
release = release.getheader('Location')
jurism = release.split('/')[-2]

build('jurism', 'amd64', jurism, f'https://github.com/Juris-M/assets/releases/download/client%2Frelease%2F{jurism}/Jurism-{jurism}_linux-x86_64.tar.bz2')
build('jurism', 'i386', jurism, f'https://github.com/Juris-M/assets/releases/download/client%2Frelease%2F{jurism}/Jurism-{jurism}_linux-i686.tar.bz2')

if not os.path.exists('sf/repo/'):
  for d in ['incoming', 'conf', 'key']:
    run(f'mkdir -p sf/repo/{d}')

  run(f'gpg --armor --export username {maintainer} > sf/repo/key/deb.gpg.key')

  write('sf/repo/conf/distributions', sum([[
    f'Origin: {maintainer}',
    'Label: Zotero/Juris-M',
    'Suite: stable',
    f'Codename: {dist}',
    f'Components: {component}',
    f'Version: {({"bionic": "18.04", "trusty": "14.04"}[dist])}',
    'Architectures: amd64 i386',
    'Description: Zotero/Juris-M is a free, easy-to-use tool to help you collect, organize, cite, and share research',
    'SignWith: yes',
    '',
  ] for dist in ['bionic', 'trusty']], []))

  run('reprepro --ask-passphrase -Vb sf/repo export')
  run('reprepro -b sf/repo/ createsymlinks')

for dist in ['bionic', 'trusty']:
  write(f'sf/repo/install-{dist}.sh', [
    'curl --silent -L https://sourceforge.net/projects/zotero-deb/files/repo/key/deb.gpg.key | sudo apt-key add -',
    '',
    'cat << EOF | sudo tee /etc/apt/sources.list.d/zotero.list',
    f'deb https://sourceforge.net/projects/zotero-deb/files/repo {dist} {component}',
    'EOF'
  ])

installed = []
for packages in glob.glob(f'sf/repo/dists/*/{component}/binary*/Packages'):
  dist = packages.split('/')[3]

  with open(packages) as f:
    for line in f.readlines():
      if line.strip() == '': continue

      key, value = [v.strip() for v in line.split(':', 1)]

      if key == 'Filename': installed.append(f'{dist}/{value.split("/")[-1]}')

for arch in ['i386', 'amd64']:
  for pkg in [ f'zotero_{zotero}_{arch}.deb', f'jurism_{jurism}_{arch}.deb']:
    for dist in ['trusty', 'bionic']:
      if f'{dist}/{pkg}' in installed:
        print(f'# {pkg} exists in {dist}')
      else:
        run(f'reprepro -C {component} -Vb sf/repo includedeb {dist} sf/{pkg}')

run('cp README.md sf')

run('rsync -avP -e ssh sf/ retorquere@frs.sourceforge.net:/home/pfs/project/zotero-deb')
