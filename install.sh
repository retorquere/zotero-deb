case `uname -m` in
  "i386" | "i686" | "x86_64")
    ;;
  *)
    echo "Zotero is only available for architectures i686 and x86_64"
    exit
    ;;
esac

BASEURL={url}
CODENAME={codename}
GPGKEY=$BASEURL/$CODENAME/deb.gpg.key
KEYRING=gnupg-ring:/etc/apt/trusted.gpg.d/zotero.gpg
if [ -x "$(command -v curl)" ]; then
  curl --silent -L $GPGKEY | sudo gpg --no-default-keyring --keyring $KEYRING --import -
elif [ -x "$(command -v wget)" ]; then
  wget -qO- $GPGKEY | sudo gpg --no-default-keyring --keyring $KEYRING --import -
else
  echo "Error: need wget or curl installed." >&2
  exit 1
fi

sudo chmod 644 /etc/apt/trusted.gpg.d/zotero.gpg

cat << EOF | sudo tee /etc/apt/sources.list.d/zotero.list
deb [by-hash=force] $BASEURL $CODENAME/
EOF

sudo apt-get clean
