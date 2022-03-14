#!/usr/bin/env python3

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

from util import Config

from b2sdk.v2 import SyncPolicyManager, ScanPoliciesManager
from b2sdk.v2 import parse_sync_folder
from b2sdk.v2 import Synchronizer
from b2sdk.v2 import SyncReport
from b2sdk.v2 import InMemoryAccountInfo
from b2sdk.v2 import B2Api
from b2sdk.v2 import CopyAndDeletePolicy, CopyAndKeepDaysPolicy, CopyPolicy, DownAndDeletePolicy, DownAndKeepDaysPolicy, DownPolicy, UpAndDeletePolicy, UpAndKeepDaysPolicy, UpPolicy
from b2sdk.v2 import NewerFileSyncMode, CompareVersionMode
import time
import os, sys
from pathlib import Path
import requests
import multiprocessing
from types import SimpleNamespace
import magic

class RepoPolicyManager:
  """
  Policy manager; implement a logic to get a correct policy class
  and create a policy object based on various parameters.
  """

  def get_policy(self, sync_type, source_path, source_folder, dest_path, dest_folder, now_millis, delete, keep_days, newer_file_mode, compare_threshold, compare_version_mode, encryption_settings_provider):
    """
    Return a policy object.
    :param str sync_type: synchronization type
    :param b2sdk.v2.AbstractSyncPath source_path: source file
    :param str source_folder: a source folder path
    :param b2sdk.v2.AbstractSyncPath dest_path: destination file
    :param str dest_folder: a destination folder path
    :param int now_millis: current time in milliseconds
    :param bool delete: delete policy
    :param int keep_days: keep for days policy
    :param b2sdk.v2.NewerFileSyncMode newer_file_mode: setting which determines handling for destination files newer than on the source
    :param int compare_threshold: difference between file modification time or file size
    :param b2sdk.v2.CompareVersionMode compare_version_mode: setting which determines how to compare source and destination files
    :param b2sdk.v2.AbstractSyncEncryptionSettingsProvider encryption_settings_provider: an object which decides which encryption to use (if any)
    :return: a policy object
    """

    #print( sync_type,  delete, source_folder,                              source_path)
    #       local-to-b2 False   LocalFolder(/Users/emile/github/debs/repo)  LocalSyncPath('InRelease', 1642160794155, 2153)
    assert sync_type == 'local-to-b2', sync_type
    deb = source_path is not None and Path(source_path.absolute_path).suffix == '.deb'
    policy = UpAndDeletePolicy if delete else UpPolicy
    return policy(
      source_path,
      source_folder,
      dest_path,
      dest_folder,
      now_millis,
      keep_days,
      NewerFileSyncMode.SKIP if deb else NewerFileSyncMode.REPLACE, # newer_file_mode
      compare_threshold,
      CompareVersionMode.NONE if deb else CompareVersionMode.MODTIME, # compare_version_mode
      encryption_settings_provider,
    )

class Sync:
  def __init__(self):
    self.b2_api = B2Api(InMemoryAccountInfo())
    self.b2_api.authorize_account('production', os.environ['B2_APPLICATION_KEY_ID'], os.environ['B2_APPLICATION_KEY'])

    self.bucket = self.b2_api.get_bucket_by_name(Config.repo.bucket)

    self.source = parse_sync_folder(Config.repo.path, self.b2_api)
    self.target = parse_sync_folder(f'b2://{Config.repo.bucket}', self.b2_api)

    self.remote = []
    for file_info, folder_name in self.bucket.ls():
      if os.path.basename(file_info.file_name) == '.bzEmpty':
        continue
      asset = os.path.join(Config.repo.path, file_info.file_name)
      self.remote.append(asset)

  def fetch(self):
    # first download missing assets using the free path
    for asset in self.remote:
      if asset.endswith('.deb') and not os.path.exists(asset):
        with open(asset, 'wb') as f:
          print('Downloading', asset)
          f.write(requests.get(Config.repo.url + '/' + os.path.basename(asset), allow_redirects=True).content)
          filetype = magic.from_file(asset)
          assert filetype.startswith('Debian binary package'), (asset, filetype)

  def update(self):
    synchronizer = Synchronizer(
      max_workers=multiprocessing.cpu_count(),
      policies_manager = ScanPoliciesManager(exclude_all_symlinks=True), # object which decides which files to process
      sync_policy_manager = RepoPolicyManager(), # object which decides what to do with each file (upload, download, delete, copy, hide etc)
      dry_run=False,
      allow_empty_source=True,
    )

    no_progress = False

    with SyncReport(sys.stdout, no_progress) as reporter:
      synchronizer.sync_folders(
        source_folder=self.source,
        dest_folder=self.target,
        now_millis=int(round(time.time() * 1000)),
        reporter=reporter,
      )

if __name__ == '__main__':
  sync = Sync()
  sync.fetch()
