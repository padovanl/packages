#!/bin/sh
# Builds a signed APT repository from a directory of .deb files.
#
#   scripts/build-repo.sh <incoming-dir> <out-dir>
#
# The signing key must already be in the gpg keyring; SIGNING_KEY picks
# it by fingerprint and defaults to the first secret key found.
set -eu

in=$1
out=$2
suite=stable
component=main
archs="amd64 arm64 armhf"

key=${SIGNING_KEY:-$(gpg --batch --list-secret-keys --with-colons | awk -F: '$1 == "fpr" { print $10; exit }')}
if [ -z "$key" ]; then
	echo "no signing key in the gpg keyring" >&2
	exit 1
fi

rm -rf "$out"
mkdir -p "$out"

# Pool layout and filenames follow Debian's (pool/main/p/portop/
# portop_1.2.3_amd64.deb), taken from the package metadata rather than
# the release asset name.
for deb in "$in"/*.deb; do
	pkg=$(dpkg-deb --field "$deb" Package)
	ver=$(dpkg-deb --field "$deb" Version)
	arch=$(dpkg-deb --field "$deb" Architecture)
	dir=$out/pool/$component/$(printf %.1s "$pkg")/$pkg
	dst=$dir/${pkg}_${ver}_${arch}.deb
	if [ -e "$dst" ]; then
		echo "two packages map to $dst; keep one per architecture" >&2
		exit 1
	fi
	mkdir -p "$dir"
	cp "$deb" "$dst"
done

cd "$out"
for arch in $archs; do
	dir=dists/$suite/$component/binary-$arch
	mkdir -p "$dir"
	apt-ftparchive --arch "$arch" packages "pool/$component" >"$dir/Packages"
	gzip -9 --no-name --keep "$dir/Packages"
done

apt-ftparchive \
	-o APT::FTPArchive::Release::Origin=lucapadovan.dev \
	-o APT::FTPArchive::Release::Label=lucapadovan.dev \
	-o APT::FTPArchive::Release::Suite="$suite" \
	-o APT::FTPArchive::Release::Codename="$suite" \
	-o APT::FTPArchive::Release::Architectures="$archs" \
	-o APT::FTPArchive::Release::Components="$component" \
	-o APT::FTPArchive::Release::Description="Packages by Luca Padovan" \
	release "dists/$suite" >Release.tmp
mv Release.tmp "dists/$suite/Release"

gpg --batch --yes --local-user "$key" --clearsign \
	--output "dists/$suite/InRelease" "dists/$suite/Release"
gpg --batch --yes --local-user "$key" --armor --detach-sign \
	--output "dists/$suite/Release.gpg" "dists/$suite/Release"

# Latest version of each package for shields.io endpoint badges
# (https://img.shields.io/endpoint?url=https://apt.lucapadovan.dev/badges/portop.json).
mkdir -p badges
for dir in "pool/$component"/*/*/; do
	pkg=$(basename "$dir")
	ver=$(for deb in "$dir"*.deb; do dpkg-deb --field "$deb" Version; done | sort -uV | tail -n 1)
	printf '{"schemaVersion":1,"label":"apt","message":"v%s","color":"blue"}\n' "$ver" >"badges/$pkg.json"
done

# Binary keyring for signed-by=, armored copy for people who want to read it.
gpg --batch --export "$key" >lucapadovan.gpg
gpg --batch --armor --export "$key" >lucapadovan.asc
