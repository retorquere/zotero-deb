#!/bin/bash
set -e # Halt on errors

# Test a full rebuild
# Will reuse staged data to reduce bandwidth
# Set the CLEAN_STAGING env var to start from scratch

CONFIG=test/resource/e2e_test_config.yml
MODE=apt
REPO=test_apt

GNUPGHOME=test/resource/gpg
GNUPGHOME="$(realpath $GNUPGHOME)" # We need a full path for apt.py:mkrepo
GPGKEY=test_key

export GNUPGHOME
export REPO

# Cleanup previous tests
echo Clear GPG directory
rm -rf "$GNUPGHOME"

echo Clear Repo directory
rm -rf $REPO

if [[ -n $CLEAN_STAGING ]]; then
  echo Clear staging directory
  rm -rf staging
fi

# Build temporary gpg key
mkdir --mode=700 "$GNUPGHOME"
gpg \
  --yes \
  --batch \
  --passphrase '' \
  --quick-gen-key $GPGKEY

# Perform a rebuild
echo Test: Perform clean rebuild
python rebuild.py \
  --config $CONFIG \
  --mode $MODE

# Test package signatures
echo Test: Verify package signatures
dpkg-sig --verify $REPO/*.deb

# Test cached rebuild
echo Test: Perform cached rebuild
python rebuild.py \
  --config $CONFIG \
  --mode $MODE

echo Test: Ensure cached rebuild cleans staging dir
if rmdir staging; then
  echo Success
else
  echo Failure: staging contains files
  exit 1
fi
