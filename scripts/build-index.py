#!/usr/bin/env python3
"""Writes index.html for an APT repository built by build-repo.sh.

    scripts/build-index.py <repo-dir> <key-fingerprint>

The package list comes from the repository's own Packages indexes, so a
project added to REPOS shows up here without touching this file.
"""

import html
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
            # A "." line separates paragraphs in a Debian description.
            pkg["description"] = " ".join(
                l for l in fields.get("Description", "").splitlines() if l != "."
            )
            pkg["homepage"] = fields.get("Homepage", "")

    items = []
    for name, pkg in sorted(packages.items()):
        latest = max(pkg["versions"], key=version_key)
        archs = ", ".join(sorted(pkg["archs"]))
        title = html.escape(name)
        if pkg["homepage"]:
            title = f'<a href="{html.escape(pkg["homepage"])}">{title}</a>'
        items.append(
            f"""      <li>
        <div class="pkg-head"><h3>{title}</h3><span class="version">{html.escape(latest)}</span></div>
        <p>{html.escape(pkg["description"])}</p>
        <div class="pkg-foot"><code>sudo apt install {html.escape(name)}</code><span class="archs">{html.escape(archs)}</span></div>
      </li>"""
        )

    template = string.Template(
        (pathlib.Path(__file__).parent.parent / "static" / "index.html.in").read_text()
    )
    spaced = " ".join(fingerprint[i : i + 4] for i in range(0, len(fingerprint), 4))
    (repo / "index.html").write_text(
        template.substitute(packages="\n".join(items), fingerprint=html.escape(spaced))
    )


if __name__ == "__main__":
    main()
