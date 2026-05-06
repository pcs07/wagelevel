# OFLC Wage Level Explorer

Static GitHub Pages dashboard for exploring OFLC prevailing wage data by:

- wage year
- source
- SOC code
- wage level
- state
- county

## Local build

1. Build the SQLite database:

```bash
python3 scripts/build_wage_map_db.py
```

2. Build the static Pages data:

```bash
python3 scripts/build_static_pages_data.py
```

3. Open `docs/index.html` with a static file server, or publish via GitHub Pages.

## Publish model

The GitHub Pages site is the static app under `docs/`.

- `docs/data/meta.json`
- `docs/data/geo/<year>.json`
- `docs/data/wages/<year>/<source>.json`
- `docs/us-counties.geojson`

The local server scripts remain available for development, but GitHub Pages uses the static build only.
