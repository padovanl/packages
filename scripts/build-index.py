#!/usr/bin/env python3
"""Writes index.html for an APT repository built by build-repo.sh.

    scripts/build-index.py <repo-dir> <key-fingerprint>

The package list comes from the repository's own Packages indexes, so a
project added to REPOS shows up here without touching this file.
static/descriptions.json can replace a package's description on the page,
for releases that shipped a poor one.
"""

import html
import json
import pathlib
import string
import sys


def parse_packages(text):
    """Yields one dict per stanza of a Packages file."""
    for stanza in text.split("\n\n"):
        fields, key = {}, None
        for line in stanza.splitlines():
            if line.startswith((" ", "\t")) and key:
                fields[key] += "\n" + line.strip()
            elif ":" in line:
                key, _, value = line.partition(":")
                fields[key] = value.strip()
        if fields:
            yield fields


def version_key(version):
    """Orders plain dotted versions numerically (1.10.0 after 1.9.0)."""
    return [int(p) if p.isdigit() else p for p in version.replace("-", ".").split(".")]


def main():
    repo, fingerprint = pathlib.Path(sys.argv[1]), sys.argv[2]

    packages = {}
    for path in sorted(repo.glob("dists/*/main/binary-*/Packages")):
        for fields in parse_packages(path.read_text()):
            pkg = packages.setdefault(fields["Package"], {"versions": set(), "archs": set()})
            pkg["versions"].add(fields["Version"])
            pkg["archs"].add(fields["Architecture"])
            # The page shows the newest version's description and homepage.
            if pkg["versions"] and version_key(fields["Version"]) < version_key(max(pkg["versions"], key=version_key)):
                continue
            # A "." line separates paragraphs in a Debian description.
            pkg["description"] = " ".join(
                l for l in fields.get("Description", "").splitlines() if l != "."
            )
            pkg["homepage"] = fields.get("Homepage", "")

    here = pathlib.Path(__file__).parent.parent / "static"
    overrides = json.loads((here / "descriptions.json").read_text())
    for name, description in overrides.items():
        if name in packages:
            packages[name]["description"] = description

    items = []
    for name, pkg in sorted(packages.items()):
        latest = max(pkg["versions"], key=version_key)
        archs = " · ".join(sorted(pkg["archs"]))
        title = html.escape(name)
        if pkg["homepage"]:
            title = f'<a href="{html.escape(pkg["homepage"])}">{title}</a>'
        items.append(
            f"""      <li>
        <div class="pkg-top"><span class="badge">{html.escape(archs)}</span><span class="version">v{html.escape(latest)}</span></div>
        <h3>{title}</h3>
        <p>{html.escape(pkg["description"])}</p>
        <code class="install">sudo apt install {html.escape(name)}</code>
      </li>"""
        )

    template = string.Template((here / "index.html.in").read_text())
    spaced = " ".join(fingerprint[i : i + 4] for i in range(0, len(fingerprint), 4))
    (repo / "index.html").write_text(
        template.substitute(packages="\n".join(items), fingerprint=html.escape(spaced))
    )


if __name__ == "__main__":
    main()
