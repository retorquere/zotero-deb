#!/usr/bin/env python3

import platform
import re
import json
import os
import sys
import glob

maintainer = 'emiliano.heyns@iris-advies.com'
component = 'main'
distros = {'bionic': '18.04', 'trusty': '14.04'}
architectures = ['i386', 'amd64']

script = len(sys.argv) == 2 and {'script': True}[sys.argv[1]]

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
  print("\n" + cmd)
  if not script: os.system(cmd)

def write(filename, lines):
  if script:
    print()
    print(f'cat << E_O_F > {filename}')
    for line in lines:
      print(line)
    print('E_O_F')

  else:
    print(f"\n# writing {filename}\n")

    with open(filename, 'w') as f:
      for line in lines:
        f.write(line + "\n")

class Repo:
  def create(self):
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
        f'Version: {version}',
        f'Architectures: {" ".join(architectures)}',
        'Description: Zotero/Juris-M is a free, easy-to-use tool to help you collect, organize, cite, and share research',
        'SignWith: yes',
        '',
      ] for dist, version in distros.items()], []))

      run('reprepro --ask-passphrase -Vb sf/repo export')
      run('reprepro -b sf/repo/ createsymlinks')

    for dist in distros.keys():
      write(f'sf/repo/install-{dist}.sh', [
        'curl --silent -L https://sourceforge.net/projects/zotero-deb/files/repo/key/deb.gpg.key | sudo apt-key add -',
        '',
        'cat << EOF | sudo tee /etc/apt/sources.list.d/zotero.list',
        f'deb https://sourceforge.net/projects/zotero-deb/files/repo {dist} {component}',
        'EOF'
      ])

  def install(self, clients):
    installed = []
    for packages in glob.glob(f'sf/repo/dists/*/{component}/binary*/Packages'):
      dist = packages.split('/')[3]

      with open(packages) as f:
        for line in f.readlines():
          if line.strip() == '': continue

          key, value = [v.strip() for v in line.split(':', 1)]

          if key == 'Filename': installed.append(f'{dist}/{value.split("/")[-1]}')

    for arch in architectures:
      for dist in distros.keys():
        for client in clients:
          deb = client.deb(arch)
          if f'{dist}/{os.path.basename(deb)}' in installed:
            print(f'## {os.path.basename(deb)} exists in {dist}')
          else:
            run(f'reprepro -C {component} -Vb sf/repo includedeb {dist} {deb}')

    run('cp README.md sf')

  def publish(self):
    run('rsync -avP -e ssh sf/ retorquere@frs.sourceforge.net:/home/pfs/project/zotero-deb')

class Package:
  def __init__(self, client, name):
    self.machine = {'amd64': 'x86_64', 'i386': 'i686'}
    self.client = client
    self.name = name

  def deb(self, arch):
    return f'sf/{"_".join([self.client, self.version, arch])}.deb'

  def build(self, arch):
    print()

    deb = self.deb(arch)

    if os.path.exists(deb):
      print(f"# not rebuilding {deb}\n")
      return

    print(f"# Building {deb}\n")

    run('mkdir -p sf')

    run(f'rm -rf build client.tar.bz2 {deb}')
    run(f'mkdir -p build/usr/lib/{self.client} build/usr/share/applications build/DEBIAN')
    run(f'curl -L -o client.tar.bz2 "{self.url(arch)}"')
    run(f'tar --strip 1 -xpf client.tar.bz2 -C build/usr/lib/{self.client}')

    write(f'build/usr/share/applications/{self.client}.desktop', [
      '[Desktop Entry]',
      'Name=Zotero',
      f'Name={self.name}',
      'Comment=Open-source reference manager',
      f'Exec=/usr/lib/{self.client}/{self.client}',
      f'Icon=/usr/lib/{self.client}/chrome/icons/default/default48.png',
      'Type=Application',
      'StartupNotify=true',
    ])

    write('build/DEBIAN/control', [
      f'Package: {self.client}',
      f'Architecture: {arch}',
      f'Maintainer: {maintainer}',
      'Section: Science',
      'Priority: optional',
      f'Version: {self.version}',
      f'Description: {self.name} is a free, easy-to-use tool to help you collect, organize, cite, and share research',
    ])

    run(f'dpkg-deb --build -Zgzip build {deb}')

class Zotero(Package):
  def __init__(self):
    super().__init__('zotero', 'Zotero') 

    response = urlopen('https://www.zotero.org/download/').read()
    if type(response) is bytes: response = response.decode("utf-8")
    for line in response.split('\n'):
      if not '"standaloneVersions"' in line: continue
      line = re.sub(r'.*Downloads,', '', line)
      line = re.sub(r'\),', '', line)
      versions = json.loads(line)
      self.version = versions['standaloneVersions'][f'linux-{platform.machine()}']
      break

  def url(self, arch):
    return f'https://www.zotero.org/download/client/dl?channel=release&platform=linux-{self.machine[arch]}&version={self.version}'

class JurisM(Package):
  def __init__(self):
    super().__init__('jurism', 'Juris-M') 

    release = HTTPSConnection('our.law.nagoya-u.ac.jp')
    release.request('GET', f'/jurism/dl?channel=release&platform=linux-{platform.machine()}')
    release = release.getresponse()
    release = release.getheader('Location')
    self.version = release.split('/')[-2]

  def url(self, arch):
    return f'https://github.com/Juris-M/assets/releases/download/client%2Frelease%2F{self.version}/Jurism-{self.version}_linux-{self.machine[arch]}.tar.bz2'

zotero = Zotero()
jurism = JurisM()
for arch in architectures:
  zotero.build(arch)
  jurism.build(arch)

print("\n# publishing repo")
repo = Repo()
repo.create()
repo.install([zotero, jurism])
repo.publish()
