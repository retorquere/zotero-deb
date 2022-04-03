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
rm -rf "$GNUPGHOME"
rm -rf $REPO
[[ -n $CLEAN_STAGING ]] && rm -rf staging

# Build temporary gpg key
mkdir "$GNUPGHOME"
gpg \
  --yes \
  --batch \
  --passphrase '' \
  --quick-gen-key $GPGKEY

# Perform a rebuild
python rebuild.py \
  --config $CONFIG \
  --mode $MODE

# Test package signatures
dpkg-sig --verify $REPO/*.deb
