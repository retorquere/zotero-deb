#!/usr/bin/env python

import platform
import re
import json
import os
import sys

maintainer = 'emiliano.heyns@iris-advies.com'

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
  print('# writing ' + filename + "\n")

  with open(filename, 'w') as f:
    for line in lines:
      f.write(line + "\n")

def build(client, arch, version, url):
  packagename = 'sf/' + '_'.join([client, version, arch]) + '.deb'
  if os.path.exists(packagename):
    print('# not rebuilding ' + packagename + "\n")
    return

  print('# Building ' + packagename + "\n")

  run('rm -rf build client.tar.bz2 ' + packagename)
  run('mkdir -p build/usr/lib/' + client + ' build/usr/share/applications build/DEBIAN')
  run('curl -L -o client.tar.bz2 "' + url + '"')
  run('tar --strip 1 -xpf client.tar.bz2 -C build/usr/lib/' + client)

  write('build/usr/share/applications/' + client + '.desktop', [
    '[Desktop Entry]',
    'Name=Zotero',
    'Name=' + ({'zotero': 'Zotero', 'jurism': 'Juris-M'}[client]),
    'Comment=Open-source reference manager',
    'Exec=/usr/lib/' + client + '/' + client,
    'Icon=/usr/lib/' + client + '/chrome/icons/default/default48.png',
    'Type=Application',
    'StartupNotify=true',
  ])

  write('build/DEBIAN/control', [
    'Package: ' + client,
    'Architecture: ' + arch,
    'Maintainer: ' + maintainer,
    'Section: Science',
    'Priority: optional',
    'Version: ' + version,
    'Description: ' + ({'zotero': 'Zotero', 'jurism': 'Juris-M'}[client]) + ' is a free, easy-to-use tool to help you collect, organize, cite, and share research',
  ])

  run('dpkg-deb --build -Zgzip build ' + ' ' + packagename)

run('mkdir -p sf')

response = urlopen('https://www.zotero.org/download/').read()
if type(response) is bytes: response = response.decode("utf-8")
for line in response.split('\n'):
  if not '"standaloneVersions"' in line: continue
  line = re.sub(r'.*Downloads,', '', line)
  line = re.sub(r'\),', '', line)
  versions = json.loads(line)
  zotero = versions['standaloneVersions']['linux-' + platform.machine()]
  break

build('zotero', 'amd64', zotero, 'https://www.zotero.org/download/client/dl?channel=release&platform=linux-x86_64&version=' + zotero)
build('zotero', 'i386', zotero, 'https://www.zotero.org/download/client/dl?channel=release&platform=linux-i686&version=' + zotero)

release = HTTPSConnection('our.law.nagoya-u.ac.jp')
release.request('GET', '/jurism/dl?channel=release&platform=linux-' + platform.machine())
release = release.getresponse()
release = release.getheader('Location')
jurism = release.split('/')[-2]

build('jurism', 'amd64', jurism, 'https://github.com/Juris-M/assets/releases/download/client%2Frelease%2F' + jurism + '/Jurism-' + jurism + '_linux-x86_64.tar.bz2')
build('jurism', 'i386', jurism, 'https://github.com/Juris-M/assets/releases/download/client%2Frelease%2F' + jurism + '/Jurism-' + jurism + '_linux-i686.tar.bz2')

for dist in ['bionic', 'trusty']:
  if not os.path.exists('sf/repo/' + dist):
    for d in ['incoming', 'conf', 'key']:
      run('mkdir -p sf/repo/' + dist + '/' + d)

    run('gpg --armor --export username ' + maintainer + ' > sf/repo/' + dist + '/key/deb.gpg.key')

    write('sf/repo/' + dist + '/conf/distributions', [
      'Origin: ' + maintainer,
      'Label: Zotero/Juris-M',
      'Suite: stable',
      'Codename: ' + dist,
      'Components: main',
      'Version: ' + ({'bionic': '18.04', 'trusty': '14.04'}[dist]),
      'Architectures: amd64 i386',
      'Description: Zotero/Juris-M is a free, easy-to-use tool to help you collect, organize, cite, and share research',
      'SignWith: yes',
    ])

    run('reprepro --ask-passphrase -Vb sf/repo/' + dist + ' export')
    run('reprepro -b sf/repo/' + dist + 'createsymlinks')

  write('sf/repo/' + dist + '/install.sh', [
    'curl --silent -L https://sourceforge.net/projects/zotero-deb/files/repo/' + dist + '/key/deb.gpg.key | sudo apt-key add -',
    ''
    'cat << EOF | sudo tee /etc/apt/sources.list.d/zotero.list',
    'deb https://sourceforge.net/projects/zotero-deb/files/repo/' + dist + ' ' + dist + ' main',
    'EOF'
  ])

  for arch in ['i386', 'amd64']:
    pkg = 'zotero_' + zotero + '_' + arch + '.deb'
    if os.path.exists('sf/repo/' + dist + '/pool/main/z/zotero/' + pkg):
      print(pkg + ' exists in ' + dist)
    else:
      run('reprepro -Vb sf/repo/' + dist + ' includedeb ' + dist + ' sf/' + pkg)

    pkg = 'jurism_' + jurism + '_' + arch + '.deb'
    if os.path.exists('sf/repo/' + dist + '/pool/main/j/jurism/' + pkg):
      print(pkg + ' exists in ' + dist)
    else:
      run('reprepro -Vb sf/repo/' + dist + ' includedeb ' + dist + ' sf/' + pkg)

run('cp README.md sf')

run('rsync -avP -e ssh sf/ retorquere@frs.sourceforge.net:/home/pfs/project/zotero-deb')
