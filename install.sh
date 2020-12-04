if [ `whoami` != root ]; then
    echo Please run this script as root or using sudo
    exit
fi

case `uname -m` in
  "i386" | "i686" | "x86_64")
    ;;
  *)
    echo "Zotero is only available for architectures i686 and x86_64"
    exit
    ;;
esac

if [[ -f "/etc/apt/trusted.gpg" && -f "/usr/bin/apt-key" ]]; then
  echo "apt-key will show it is deprecated -- don't worry, we're just migrating the package signing key to a new format"
  sudo apt-key --keyring /etc/apt/trusted.gpg del 1C349BCF
fi

if [ -x "$$(command -v curl)" ]; then
  curl --silent -L $url/deb.gpg.key | gpg --no-default-keyring --keyring gnupg-ring:/etc/apt/trusted.gpg.d/zotero.gpg --import -
elif [ -x "$$(command -v wget)" ]; then
  wget -qO- $url/deb.gpg.key | gpg --no-default-keyring --keyring gnupg-ring:/etc/apt/trusted.gpg.d/zotero.gpg --import -
else
  echo "Error: need wget or curl installed." >&2
  exit 1
fi

sudo chmod 644 /etc/apt/trusted.gpg.d/zotero.gpg

cat << EOF | sudo tee /etc/apt/sources.list.d/zotero.list
deb $url/ ./
EOF

