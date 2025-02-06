# https://wiki.debian.org/DebianRepository/UseThirdParty

case `uname -m` in
  "i386" | "i686" | "x86_64")
    ;;
  *)
    echo "Zotero is only available for architectures i686 and x86_64"
    exit
    ;;
esac

check_dir() {
    dir=$1
    if [ ! -d "$dir" ] || [ ! -w "$dir" ]; then
        echo "Directory does not exist or is not writable: $dir"
        exit 1
    fi
}
check_dir /usr/share/keyrings
check_dir /etc/apt/sources.list.d

export GNUPGHOME="/dev/null"

REPO=${1:-'https://zotero.retorque.re/file/apt-package-archive'}
KEYNAME=zotero-archive-keyring.gpg
GPGKEY=https://raw.githubusercontent.com/retorquere/zotero-deb/master/$KEYNAME
KEYRING=/usr/share/keyrings/$KEYNAME
if [ -x "$(command -v curl)" ]; then
  sudo -E curl -L $GPGKEY -o $KEYRING
elif [ -x "$(command -v wget)" ]; then
  sudo -E wget -O $KEYRING $GPGKEY
else
  echo "Error: need wget or curl installed." >&2
  exit 1
fi

sudo chmod 644 $KEYRING
# old key with too broad reach
if [ -f /etc/apt/trusted.gpg.d/zotero.gpg ]; then
  sudo rm -f /etc/apt/trusted.gpg.d/zotero.gpg
fi

cat << EOF | sudo tee /etc/apt/sources.list.d/zotero.list
deb [signed-by=$KEYRING by-hash=force] $REPO ./
EOF

KEYNAME=zotero-archive-keyring.asc
GPGKEY=https://raw.githubusercontent.com/retorquere/zotero-deb/master/$KEYNAME
if [ -x "$(command -v curl)" ]; then
  GPGKEY=$(curl -sL $GPGKEY | sed 's/^$/./' | sed 's/^/ /')
elif [ -x "$(command -v wget)" ]; then
  GPGKEY=$(wget -qO- $GPGKEY | sed 's/^$/./' | sed 's/^/ /')
fi
cat << EOF | sudo tee /etc/apt/sources.list.d/zotero.sources
Types: deb
URIs: https://zotero.retorque.re/file/apt-package-archive
Suites: ./
Options: by-hash=force
Signed-By:
$GPGKEY
EOF

sudo apt-get clean
