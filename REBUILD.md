# How to reproduce this repo

Set up gpg

```
cat << EOF | gpg --gen-key --batch
%no-protection
Key-Type: RSA
Key-Length: 4096
Key-Usage: sign
Name-Real: dpkg
Name-Email: dpkg@iris-advies.com
Expire-Date: 0
%commit
EOF
```

and run `update.py`
