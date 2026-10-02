#!/usr/bin/env bash
# Create the isolated oracle environment and fetch Swiss Ephemeris data files.
# Development only: nothing here is shipped or imported by the product.
set -euo pipefail
cd "$(dirname "$0")"

uv venv -q .venv --python 3.11
VIRTUAL_ENV=.venv uv pip install -q -r requirements.txt

mkdir -p cache/ephe
base="https://raw.githubusercontent.com/aloistr/swisseph/master/ephe"
for file in sepl_18.se1 semo_18.se1 seas_18.se1; do
  if [ ! -s "cache/ephe/$file" ]; then
    curl -sSfL --retry 3 -o "cache/ephe/$file" "$base/$file"
  fi
done
echo "Oracle ready. Regenerate fixtures with: oracle/.venv/bin/python oracle/generate_astro_fixtures.py"
