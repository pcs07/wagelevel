#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/p958s831/Documents/wagelevel"
DB="$ROOT/data/oflc_wages.sqlite"

if [ ! -f "$DB" ]; then
  echo "Building OFLC wage database..."
  python3 "$ROOT/scripts/build_wage_map_db.py"
fi

echo "Starting county wage dashboard at http://127.0.0.1:8123"
python3 "$ROOT/scripts/serve_county_wage_map.py" --port 8123
