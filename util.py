import subprocess
import os, sys
from colorama import Fore, Style
import json
import munch
import contextlib
import configparser
from pathlib import Path

from ruamel.yaml import YAML
yaml=YAML(typ='safe')

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--mode')
parser.add_argument('--config')
args, unknownargs = parser.parse_known_args()
sys.argv = sys.argv[:1]
sys.argv += unknownargs

## change directory and back
class chdir():
  def __init__(self, path):
    self.cwd = Path.cwd()
    self.path = path
  def __enter__(self):
    print('changing to', self.path)
    os.chdir(self.path)
  def __exit__(self, exc_type, exc_value, exc_traceback):
    os.chdir(self.cwd)

## run and exit on error
def run(cmd, env={}):
  print('$', Fore.GREEN + cmd, Style.RESET_ALL)
  subprocess.run(cmd, shell=True, check=True, env=os.environ.copy() | env)
  print('')

def bumped(client, version):
  global Config
  if bump := Config[client].get('bump', {}).get(version):
    return f'{version}-{bump}'
  else:
    return version

## load config
config_file = Path(args.config or 'config.yml')

Config = munch.munchify(yaml.load(config_file))
Config.mode = args.mode
assert Config.mode in [ None, 'apt'], Config.mode
Config.repo = Path(os.environ['REPO']).resolve()
Config.staging = Path(Config.staging)

Config.zotero.bumped = lambda version: bumped('zotero', version)
Config['zotero-beta'].bumped = lambda version: bumped('zotero-beta', version)
Config.jurism.bumped = lambda version: bumped('jurism', version)

Config.archmap = {
  'i686': 'i386',
  'x86_64': 'amd64',
}

  # context manager to open file for reading or writing, and in the case of write, create paths as required
class Open():
  def __init__(self, path, mode='r', fmode=None):
    self.path = path
    if 'w' in mode or 'a' in mode:
      self.path.parent.mkdir(parents=True, exist_ok=True)
    self.mode = fmode
    self.f = open(self.path, mode)

  def __enter__(self):
    return self.f

  def __exit__(self, exc_type, exc_value, exc_traceback):
    self.f.close()
    if self.mode is not None:
      self.path.chmod(self.mode)

# open inifile with default settings
@contextlib.contextmanager
def IniFile(path):
  ini = configparser.RawConfigParser()
  ini.optionxform=str
  ini.read(path)
  yield ini
