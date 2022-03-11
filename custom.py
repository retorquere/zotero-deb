#!/usr/bin/env python3

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

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
import pathlib

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
    print(source_path, source_folder)
    policy = UpAndDeletePolicy if delete else UpPolicy
    deb = source_path is not None and pathlib.Path(source_path.absolute_path).suffix == '.deb'
    return policy(
      source_path,
      source_folder,
      dest_path,
      dest_folder,
      now_millis,
      keep_days,
      NewerFileSyncMode.SKIP if deb else NewerFileSyncMode.REPLACE, # newer_file_mode
      compare_threshold,
      CompareVersionMode.NONE, # compare_version_mode
      encryption_settings_provider,
    )

b2_api = B2Api(InMemoryAccountInfo())
b2_api.authorize_account('production', os.environ['B2_APPLICATION_KEY_ID'], os.environ['B2_APPLICATION_KEY'])

bucket_name = 'zotero-apt'
source = '/Users/emile/github/debs/repo'
destination = f'b2://{bucket_name}'

bucket = b2_api.get_bucket_by_name(bucket_name)

try:
  from prep import prep
  prep(source, bucket, f'https://apt.retorque.re/file/{bucket_name}')
except ModuleNotFoundError:
  pass

source = parse_sync_folder(source, b2_api)
destination = parse_sync_folder(destination, b2_api)

synchronizer = Synchronizer(
  max_workers=10,
  policies_manager = ScanPoliciesManager(exclude_all_symlinks=True), # object which decides which files to process
  sync_policy_manager = RepoPolicyManager(), # object which decides what to do with each file (upload, download, delete, copy, hide etc)
  dry_run=False,
  allow_empty_source=True,
)

no_progress = False

with SyncReport(sys.stdout, no_progress) as reporter:
  synchronizer.sync_folders(
    source_folder=source,
    dest_folder=destination,
    now_millis=int(round(time.time() * 1000)),
    reporter=reporter,
  )
