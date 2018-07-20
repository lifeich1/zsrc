cd ~

apt update
apt install -y git build-essential

git clone https://github.com/ToyoDAdoubi/doubi.git

ln -s doubi/ssr.sh
chmod +x ssr.sh

mkdir -p var
cd var

wget -N --no-check-certificate https://download.libsodium.org/libsodium/releases/LATEST.tar.gz
tar xzf LATEST.tar.gz
cd libsodium-stable
./configure --disable-maintainer-mode
make && make check && make install

ldconfig


cd ~
touch /tmp/running
echo 
echo '[startup done]'
