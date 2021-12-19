# https://wiki.debian.org/DebianRepository/UseThirdParty

case `uname -m` in
  "i386" | "i686" | "x86_64")
    ;;
  *)
    echo "Zotero is only available for architectures i686 and x86_64"
    exit
    ;;
esac

export GNUPGHOME="/dev/null"

BASEURL={url}
CODENAME={codename}
KEYNAME=zotero-archive-keyring.gpg
GPGKEY=$BASEURL/$CODENAME/$KEYNAME
KEYRING=/usr/share/keyrings/$KEYNAME
if [ -x "$(command -v curl)" ]; then
  sudo curl -L $GPGKEY -o $KEYRING
elif [ -x "$(command -v wget)" ]; then
  sudo wget -O $KEYRING $GPGKEY
else
  echo "Error: need wget or curl installed." >&2
  exit 1
fi

sudo chmod 644 $KEYRING
# old key with too broad reach
sudo rm -f /etc/apt/trusted.gpg.d/zotero.gpg

cat << EOF | sudo tee /etc/apt/sources.list.d/zotero.list
deb [signed-by=$KEYRING by-hash=force] $BASEURL $CODENAME/
EOF

sudo apt-get clean
