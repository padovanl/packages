# packages

Source of [apt.lucapadovan.dev](https://apt.lucapadovan.dev), the APT
repository for [portop](https://github.com/padovanl/portop).

The repository is rebuilt from scratch on every run of
[publish.yml](.github/workflows/publish.yml): it downloads the `.deb` files
of the latest stable GitHub releases of each project in `REPOS`, checks them
against the release `checksums.txt`, indexes them with `apt-ftparchive`,
signs the index and deploys it to GitHub Pages. No package is stored in git.

## Setup

- Secret `APT_SIGNING_KEY`: ASCII-armored private key that signs the
  repository (no passphrase).
- Settings → Pages → Source: GitHub Actions; custom domain
  `apt.lucapadovan.dev`.

To build locally with a key in your keyring:

```sh
scripts/build-repo.sh <dir-with-debs> public
```
