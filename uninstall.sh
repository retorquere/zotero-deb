KEYNAME=zotero-archive-keyring.gpg
KEYRING=/usr/share/keyrings/$KEYNAME
sudo rm -f $KEYRING
sudo rm -f /etc/apt/sources.list.d/zotero.list
sudo apt-get clean
