#!/usr/bin/env python3

import platform
import re
import json
import os
import sys
import glob
import shlex
import argparse
import subprocess
from shutil import copyfile

import os
from github import Github

parser = argparse.ArgumentParser()
parser.add_argument('--publish', action='store_true')
parser.add_argument('--rebuild', action='store_true')
args = parser.parse_args()

maintainer = 'emiliano.heyns@iris-advies.com'
architectures = [ 'amd64', 'i386' ]
gpg = 'dpkg'

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

  if subprocess.call(cmd, shell=True) != 0:
    print(f'{cmd} exited with an error')
    sys.exit(1)

def write(filename, content):
  print(f"\n# writing {filename}\n")

  if type(content) == list: content = '\n'.join(content)

  with open(filename, 'w') as f:
    f.write(content + "\n")

class Repo:
  def __init__(self):
    self.repo = 'repo'
    self.updated = False

    gh = Github(os.environ['GITHUB_TOKEN'])

    user = gh.get_user()
    repo = user.get_repo('zotero-deb')

    if 'apt-get' in [rel.tag_name for rel in repo.get_releases()]:
      self.release = repo.get_release('apt-get')
    else:
      with open('README.md') as f:
        description = f.read()
      self.release = repo.create_git_release('apt-get', 'Debian packages for Zotero/Juris-M', description)
    self.assets = [asset.name for asset in self.release.get_assets()]

  def upload(self, path):
    action = 'uploading'
    for asset in self.release.get_assets():
      if asset.name == os.path.basename(path):
        asset.delete_asset()
        action = 'replacing'

    print(f'{action} {path}')
    self.release.upload_asset(path)

  def publish(self):
    if not args.publish and not self.updated:
      print('publish: nothing to do')
      return

    # general prep
    run(f'mkdir -p {self.repo}')
    run(f'gpg --armor --export {gpg} > {self.repo}/deb.gpg.key')
    run(f'cd {self.repo} && apt-ftparchive packages . > Packages')
    run(f'bzip2 -kf {self.repo}/Packages')
    run(f'cd {self.repo} && apt-ftparchive release . > Release')
    run(f'gpg --yes -abs -u {gpg} -o {self.repo}/Release.gpg --digest-algo sha256 {self.repo}/Release')
    run(f'gpg --yes -abs -u {gpg} --clearsign -o {self.repo}/InRelease --digest-algo sha256 {self.repo}/Release')

    # github
    write(f'{self.repo}/install.sh', [
      'if [ -x "$(command -v curl)" ]; then',
      '  curl --silent -L https://github.com/retorquere/zotero-deb/releases/download/apt-get/deb.gpg.key | sudo apt-key add -',
      'elif [ -x "$(command -v wget)" ]; then',
      '  wget -qO- https://github.com/retorquere/zotero-deb/releases/download/apt-get/deb.gpg.key | sudo apt-key add -',
      'else',
      '  echo "Error: need wget or curl installed." >&2',
      '  exit 1',
      'fi',
      '',
      'cat << EOF | sudo tee /etc/apt/sources.list.d/zotero.list',
      'deb https://github.com/retorquere/zotero-deb/releases/download/apt-get/ ./',
      'EOF'
    ])

    for f in sorted(os.listdir(self.repo)):
      self.upload(f'{self.repo}/{f}')

    # sourceforge
    #write(f'{self.repo}/install.sh', [
    #  'curl --silent -L https://downloads.sourceforge.net/project/zotero-deb/deb.gpg.key | sudo apt-key add -',
    #  '',
    #  'cat << EOF | sudo tee /etc/apt/sources.list.d/zotero.list',
    #  'deb https://downloads.sourceforge.net/project/zotero-deb/ ./',
    #  'EOF'
    #])
    #run('rsync -avP -e ssh repo/ retorquere@frs.sourceforge.net:/home/pfs/project/zotero-deb')

class Package:
  def __init__(self, client, name, repo):
    self.machine = {'amd64': 'x86_64', 'i386': 'i686'}
    self.client = client
    self.name = name
    self.repo = repo

  def deb(self, arch, version = None):
    return f'{self.repo.repo}/{"_".join([self.client, version or self.version, arch])}.deb'

  def build(self, arch):
    print()

    deb = self.deb(arch)
    for old in glob.glob(self.deb(arch, '*')):
      if old == deb and not args.rebuild: continue
      os.remove(old)

    if os.path.exists(deb):
      print(f"# not rebuilding {deb}\n")
      return

    print(f"# Building {deb}\n")

    run(f'mkdir -p {self.repo.repo}')

    run(f'rm -rf build client.tar.bz2 {deb}')
    run(f'mkdir -p build/usr/lib/{self.client}/distribution build/usr/share/applications build/DEBIAN')
    run(f'curl -L -o client.tar.bz2 "{self.url(arch)}"')
    run(f'tar --strip 1 -xpf client.tar.bz2 -C build/usr/lib/{self.client}')

    write(f'build/usr/lib/{self.client}/distribution/policies.json', json.dumps({ "policies": { "DisableAppUpdate": True } }))

    write(f'build/usr/share/applications/{self.client}.desktop', [
      '[Desktop Entry]',
      f'Name={self.name}',
      'Comment=Open-source reference manager',
      f'Exec=/usr/lib/{self.client}/{self.client} --url %u',
      f'Icon=/usr/lib/{self.client}/chrome/icons/default/default48.png',
      'Type=Application',
      'StartupNotify=true',
      'MimeType=x-scheme-handler/zotero',
    ])

    # fix ownership because I previously forgot --root-owner-group
    write('build/DEBIAN/postinst', [
      '#!/bin/bash',
      f'rm -f /usr/lib/{self.client}/active-update.xml',
      f'rm -f /usr/lib/{self.client}/precomplete',
      f'rm -f /usr/lib/{self.client}/removed-files',
      f'rm -f /usr/lib/{self.client}/updates',
      f'rm -f /usr/lib/{self.client}/updates.xml',
      f'chown -R root:root /usr/lib/{self.client}',
      f'chown -R root:root /usr/share/applications/{self.client}.desktop',
    ])
    run('chmod +x build/DEBIAN/postinst')

    for f in ['preinst', 'postrm']:
      target = f'build/DEBIAN/{f}'
      print(f'Copying {target}')
      copyfile('mimeapps', target)
      run(f'chmod +x {target}')

    write('build/DEBIAN/control', [
      f'Package: {self.client}',
      f'Architecture: {arch}',
      'Depends: libnss3-dev',
      f'Maintainer: {maintainer}',
      'Section: Science',
      'Priority: optional',
      f'Version: {self.version}',
      f'Description: {self.name} is a free, easy-to-use tool to help you collect, organize, cite, and share research',
    ])

    run(f'dpkg-deb --root-owner-group --build -Zgzip build {deb}')
    run(f'dpkg-sig -k {gpg} --sign builder {deb}')

    self.repo.updated = True

class Zotero(Package):
  def __init__(self, repo):
    super().__init__('zotero', 'Zotero', repo) 

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
  def __init__(self, repo):
    super().__init__('jurism', 'Juris-M', repo) 

    response = urlopen('https://github.com/Juris-M/assets/releases/download/client%2Freleases%2Fincrementals-linux/incrementals-release-linux').read()
    if type(response) is bytes: response = response.decode("utf-8")
    self.version = sorted(response.split('\n'))[-1]

  def url(self, arch):
    return f'https://github.com/Juris-M/assets/releases/download/client%2Frelease%2F{self.version}/Jurism-{self.version}_linux-{self.machine[arch]}.tar.bz2'

print("\n# creating repo")
repo = Repo()

zotero = Zotero(repo)
jurism = JurisM(repo)
for arch in architectures:
  zotero.build(arch)
  jurism.build(arch)

print("\n# publishing repo")
repo.publish()
