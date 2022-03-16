#!/usr/bin/env python3

import argparse, os

parser = argparse.ArgumentParser()
parser.add_argument('--repo', required=True)
parser.add_argument('--codename', required=True)
parser.add_argument('--baseurl', required=True)
parser.add_argument('--sync', required=True)
parser.add_argument('--beta-delim')
args = parser.parse_args()
args.repo = os.path.abspath(args.repo)

import tempfile
import shlex
import glob
from tenacity import retry, stop_after_attempt

from util import run, chdir

@retry(stop=stop_after_attempt(5)) # sourceforge rsync is ridiculously unreliable
def sync():
  print('running sync in', os.getcwd())
  run('find . -type f')
  run(args.sync)

codename = shlex.quote(args.codename)
assert not os.path.exists(args.codename), f'{codename} exists'
run(f'cp -r {shlex.quote(args.repo)} {codename}')

# https://bugs.launchpad.net/ubuntu/+source/dpkg/+bug/1701756/comments/3. + and ~ get escaped in URLs in B2 and GH respectively, ':' is seen as an epoch, . is going to cause problems, - is reserved for bumps
if args.beta_delim:
  for deb in glob.glob(os.path.join(args.codename, 'zotero-beta*.deb')):
    run(f'mv {shlex.quote(deb)} {shlex.quote(deb.replace("+", args.beta_delim))}')

run(f'apt-ftparchive packages {codename} > {codename}/Packages')

with chdir(args.codename):
  run('rm -rf by-hash')
  run('bzip2 -kf Packages')
  run(f'apt-ftparchive -o APT::FTPArchive::AlwaysStat="true" -o APT::FTPArchive::Release::Codename={args.codename}/ -o APT::FTPArchive::Release::Acquire-By-Hash="yes" release . > Release')
  #(cd repo/$1 && gpg --export dpkg > zotero-archive-keyring.gpg)
  #(cd repo/$1 && gpg --armor --export dpkg > zotero-archive-keyring.asc)
  run('gpg --yes -abs -u dpkg -o Release.gpg --digest-algo sha256 Release')
  run('gpg --yes -abs -u dpkg --clearsign -o InRelease --digest-algo sha256 Release')

  for asset in ['Packages', 'Packages.bz2']:
    for hsh in ['MD5Sum', 'SHA1', 'SHA256', 'SHA512']:
      run(f'mkdir -p by-hash/{hsh}')
      run(f"cp {asset} by-hash/{hsh}/`{hsh.lower().replace('sum', '')}sum Packages " + " | awk '{print $1}'`")

  def replace(line):
    if line.startswith('BASEURL='):
      return f'BASEURL={args.baseurl}\n'
    elif line.startswith('CODENAME='):
      return f'CODENAME={args.codename}\n'
    return line

  with open('install.sh') as f:
    installsh = [replace(line) for line in f.readlines()]
  with open('install.sh', 'w') as f:
    f.write(''.join(installsh))

  sync()
