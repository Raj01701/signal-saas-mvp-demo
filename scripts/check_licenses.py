"""Fail the build if a shipped (runtime) dependency uses a copyleft licence.

The product must only ship permissively licensed code (MIT, BSD, Apache, ISC,
PSF, ...). AGPL tools such as Swiss Ephemeris or PyJHora may only be used in the
isolated ``oracle/`` harness, which is never installed into the product
environment.

Usage:
    uv run python scripts/check_licenses.py            # Python runtime deps
    uv run python scripts/check_licenses.py --js web   # web runtime deps (pnpm)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from importlib import metadata
from pathlib import Path

DENY = re.compile(
    r"\b(A?GPL|LGPL|GNU (Affero |Lesser )?General Public|SSPL|EUPL|CC-BY-(NC|SA)|"
    r"Commons Clause|BUSL|Business Source)\b",
    re.IGNORECASE,
)

# Licences reviewed by hand. Key: distribution name (lower-case), value: reason.
REVIEWED: dict[str, str] = {
    "certifi": "MPL-2.0 is file-level weak copyleft; used unmodified, allowed.",
    "timezonefinder-data": (
        "ODbL-1.0 timezone boundaries (OpenStreetMap-derived), used unmodified; "
        "attribution shown in the About page. Share-alike applies only to derivative databases."
    ),
}

WORKSPACE_PACKAGES = {"jyotish-engine", "jyotish-api", "jyotish-platform"}


def _runtime_python_packages(root: Path) -> list[str]:
    exported = subprocess.run(
        [
            "uv",
            "export",
            "--no-dev",
            "--all-packages",
            "--no-hashes",
            "--no-emit-workspace",
            "--format",
            "requirements-txt",
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    names = []
    for raw_line in exported.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "-")):
            continue
        name = re.split(r"[=<>\[; ]", line, maxsplit=1)[0].strip().lower()
        if name and name not in WORKSPACE_PACKAGES:
            names.append(name)
    return sorted(set(names))


def _licence_text(dist: metadata.Distribution) -> str:
    meta = dist.metadata
    parts = [
        meta.get("License-Expression") or "",
        (meta.get("License") or "").splitlines()[0] if meta.get("License") else "",
    ]
    parts += [c for c in meta.get_all("Classifier") or [] if c.startswith("License")]
    return " | ".join(p for p in parts if p)


def check_python(root: Path) -> int:
    failures = 0
    for name in _runtime_python_packages(root):
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            print(f"?? {name}: not installed in this environment (run `uv sync`)")
            failures += 1
            continue
        text = _licence_text(dist)
        if name in REVIEWED:
            print(f"ok {name}: {text} (reviewed: {REVIEWED[name]})")
        elif DENY.search(text):
            print(f"XX {name}: copyleft licence not allowed in product: {text}")
            failures += 1
        elif not text:
            print(f"?? {name}: no licence metadata; review and add to REVIEWED")
            failures += 1
        else:
            print(f"ok {name}: {text}")
    return failures


def check_js(web_dir: Path) -> int:
    raw = subprocess.run(
        ["pnpm", "licenses", "list", "--prod", "--json"],
        cwd=web_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    by_licence: dict[str, list[dict[str, object]]] = json.loads(raw or "{}")
    failures = 0
    for licence, packages in sorted(by_licence.items()):
        names = ", ".join(str(p.get("name")) for p in packages)
        if DENY.search(licence):
            print(f"XX {licence}: {names}")
            failures += 1
        else:
            print(f"ok {licence}: {len(packages)} package(s)")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--js", metavar="WEB_DIR", help="check a pnpm project instead")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    failures = check_js(root / args.js) if args.js else check_python(root)
    if failures:
        print(f"\n{failures} licence problem(s) found.")
        return 1
    print("\nAll runtime dependencies are permissively licensed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
