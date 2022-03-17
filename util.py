import subprocess
import os
from colorama import Fore, Style
import json
from munch import Munch
import contextlib
import configparser

from ruamel.yaml import YAML
yaml=YAML(typ='safe')

## change directory and back
class chdir():
  def __init__(self, path):
    self.cwd = os.getcwd()
    self.path = path
  def __enter__(self):
    print('changing to', self.path)
    os.chdir(self.path)
  def __exit__(self, exc_type, exc_value, exc_traceback):
    os.chdir(self.cwd)

## run and exit on error
def run(cmd):
  print('$', Fore.GREEN + cmd, Style.RESET_ALL)
  subprocess.run(cmd, shell=True, check=True)
  print('')

def bumped(client, version):
  global Config
  if bump := Config[client].bump.get(version):
    return f'{version}-{bump}'
  else:
    return version

## load config
with open('config.yml') as f:
  Config = json.loads(json.dumps(yaml.load(f)), object_hook=Munch.fromDict)
  Config.apt = os.path.abspath(Config.apt)

  Config.zotero.bumped = lambda version: bumped('zotero', version)
  Config.jurism.bumped = lambda version: bumped('jurism', version)

  Config.archmap = {
    'i686': 'i386',
    'x86_64': 'amd64',
  }

  # context manager to open file for reading or writing, and in the case of write, create paths as required
class Open():
  def __init__(self, path, mode='r', fmode=None):
    self.path = path
    if 'w' in mode or 'a' in mode: os.makedirs(os.path.dirname(self.path), exist_ok=True)
    self.mode = fmode
    self.f = open(self.path, mode)

  def __enter__(self):
    return self.f

  def __exit__(self, exc_type, exc_value, exc_traceback):
    self.f.close()
    if self.mode is not None:
      os.chmod(self.path, self.mode)

# open inifile with default settings
@contextlib.contextmanager
def IniFile(path):
  ini = configparser.RawConfigParser()
  ini.optionxform=str
  ini.read(path)
  yield ini
