#!/usr/bin/env python

import platform
import glob
import argparse
import re
import json
import os
import sys
import tempfile
import socket
import collections
import shutil

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
  input = raw_input
  ConnectionRefusedError = socket.error

class Installer:
  def __init__(self):
    parser = argparse.ArgumentParser()
    parser.add_argument('--deb', choices=['zotero', 'zotero-beta', 'jurism'], required=True, help='prepare deb package for Zotero client, either Zotero or Juris-M')
    parser.add_argument('--dist', choices=['bionic', 'trusty'], default='bionic')
    args = parser.parse_args()

    self.dist = args.dist

    if args.deb == 'zotero-beta':
      self.client = 'zotero'
      self.version = 'beta'
    else:
      self.client = args.deb
      self.version = self.get_version()

    if self.client == 'zotero':
      if self.version == 'beta':
        self.url = "https://www.zotero.org/download/client/dl?channel=beta&platform=linux-" + platform.machine()
      else:
        self.url = "https://www.zotero.org/download/client/dl?channel=release&platform=linux-" + platform.machine() + '&version=' + self.version
    else:
      self.url = 'https://our.law.nagoya-u.ac.jp/jurism/dl?channel=release&platform=linux-' + platform.machine() + '&version=' + self.version

    self.usr = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'usr'))
    if os.path.exists(self.usr): shutil.rmtree(self.usr)

    if self.version == 'beta':
      self.client_release = self.client + '-beta'
    else:
      self.client_release = self.client
    self.installdir = os.path.join('/usr/lib', self.client)

    self.usr_lib_app = os.path.join(self.usr, 'lib', self.client_release)
    os.system('mkdir -p ' + self.shellquote(self.usr_lib_app))
    self.usr_share_applications = os.path.join(self.usr, 'share', 'applications')
    os.system('mkdir -p ' + self.shellquote(self.usr_share_applications))

    self.architecture = platform.machine()
    if self.architecture == 'x86_64':
      self.architecture = 'amd64'
    else:
      print('Unexpected architecture ' + architecture)
      sys.exit(1)

    self.packagedir = os.path.abspath(os.path.join(os.path.dirname(os.path.join(__file__)), '..'))
    self.packagename = '_'.join([self.client, self.version, self.architecture]) + '.deb'
    self.package = os.path.join(self.packagedir, '..', self.packagename)

    self.download()
    self.make_desktop_entry()
    self.build()
    self.release()

  def get_version(self):
    if self.client == 'zotero':
      response = urlopen('https://www.zotero.org/download/').read()
      if type(response) is bytes: response = response.decode("utf-8")
      for line in response.split('\n'):
        if not '"standaloneVersions"' in line: continue
        line = re.sub(r'.*Downloads,', '', line)
        line = re.sub(r'\),', '', line)
        versions = json.loads(line)
        return versions['standaloneVersions']['linux-' + platform.machine()]

    else:
      release = HTTPSConnection('our.law.nagoya-u.ac.jp')
      release.request('GET', '/jurism/dl?channel=release&platform=linux-' + platform.machine())
      release = release.getresponse()
      release = release.getheader('Location')
      return release.split('/')[-2]

  def download(self):
    tarball = tempfile.NamedTemporaryFile().name
    print("Downloading " + self.client + ' ' + self.version + ' for ' + platform.machine() + ' from ' + self.url + ' to ' + tarball)
    urlretrieve(self.url, tarball)

    os.system('tar --strip 1 -xpf ' + self.shellquote(tarball) + ' -C ' + self.shellquote(self.usr_lib_app))

  def shellquote(self, s):
    return "'" + s.replace("'", "'\\''") + "'"

  def make_desktop_entry(self):
    with open(os.path.join(self.usr_share_applications, self.client_release + '.desktop'), 'w') as desktop:
      desktop.write("[Desktop Entry]\n")
      if self.client == 'zotero':
        desktop.write("Name=Zotero\n")
      else:
        desktop.write("Name=Juris-M\n")

      desktop.write("Comment=Open-source reference manager\n")
      desktop.write("Exec=" + self.installdir + '/' + self.client + "\n")
      desktop.write("Icon=" + self.installdir + "/chrome/icons/default/default48.png\n")
      desktop.write("Type=Application\n")
      desktop.write("StartupNotify=true\n")

  def build(self):
    with open(os.path.abspath(os.path.join(os.path.dirname(__file__), 'control')), 'w') as f:

      f.write("Package: " + self.client_release + "\n")
      f.write("Architecture: " + self.architecture + "\n")
      f.write("Maintainer: @retorquere\n")
      f.write("Priority: optional\n")
      f.write("Version: " + self.version + "\n")
      if self.client == 'zotero':
        description = 'Zotero ' + self.version
      else:
        description = 'Juris-M ' + self.version
      f.write("Description: " + description + " is a free, easy-to-use tool to help you collect, organize, cite, and share research\n")

    if os.path.exists(self.package): os.remove(self.package)

    os.chdir(os.path.abspath(os.path.join(self.packagedir, '..')))
    os.system('dpkg-deb --build -Zgzip ' + self.shellquote(os.path.basename(self.packagedir)) + ' ' + self.shellquote(self.packagename))

  def release(self):
    os.chdir(os.path.abspath(os.path.join(self.packagedir, '..')))

    release = 'github-release release '
    release += '--user retorquere '
    release += '--repo zotero_deb '
    release += '--tag ' + self.shellquote(self.client + '-' + self.version) + ' '
    release += '--name ' + self.shellquote(self.client + ' ' + self.version) + ' '
    release += '--description ' + self.shellquote(self.client + ' ' + self.version) + ' '
    os.system(release)

    release = 'github-release upload '
    release += '--user retorquere '
    release += '--repo zotero_deb '
    release += '--tag ' + self.shellquote(self.client + '-' + self.version) + ' '
    release += '--name ' + self.shellquote(self.packagename) + ' '
    release += '--file ' + self.shellquote(self.package) + ' '
    os.system(release)

    os.system('package_cloud push retorquere/zotero/ubuntu/' + self.dist + ' ' + self.shellquote(self.packagename))

Installer()
