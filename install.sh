if [ `whoami` != root ]; then
    echo Please run this script as root or using sudo
    exit
fi

case `uname -m` in
  "i686" | "x86_64")
    ;;
  *)
    echo "Zotero is only available for architectures i686 and x86_64"
    exit
    ;;
esac
exit

if [ -x "$(command -v curl)" ]; then
  curl --silent -L https://github.com/retorquere/zotero-deb/releases/download/apt-get/deb.gpg.key | sudo apt-key add -
elif [ -x "$(command -v wget)" ]; then
  wget -qO- https://github.com/retorquere/zotero-deb/releases/download/apt-get/deb.gpg.key | sudo apt-key add -
else
  echo "Error: need wget or curl installed." >&2
  exit 1
fi

cat << EOF | sudo tee /etc/apt/sources.list.d/zotero.list
deb https://github.com/retorquere/zotero-deb/releases/download/apt-get/ ./
EOF

