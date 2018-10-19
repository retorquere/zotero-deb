# Packaged version of Zotero and Juris-M.

## Installation

One-time installation of the repo:

`$ curl --silent -L https://sourceforge.net/projects/zotero-deb/files/install.sh | sudo bash`

after this you can install and update in the usual way:

`$ sudo apt-get update`

`$ sudo apt-get install zotero jurism`

If you want to manually install the packages you can download them at https://sourceforge.net/projects/zotero-deb/files/

## How to reproduce this repo

Set up gpg

```
cat << EOF | gpg --gen-key --batch
Key-Type: RSA
Key-Length: 4096
Key-Usage: sign
Name-Real: dpkg
Name-Email: dpkg@iris-advies.com
Expire-Date: 0
EOF
```

and run `update.py`
