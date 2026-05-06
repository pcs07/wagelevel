#!/usr/bin/env python3

import csv
import re
import sqlite3
import unicodedata
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "oflc_wages.sqlite"
COUNTY_CODES_PATH = BASE_DIR / "national_county.txt"

YEARS = [
    ("2019-20", BASE_DIR / "data" / "raw" / "2019-20"),
    ("2020-21", BASE_DIR / "data" / "raw" / "2020-21"),
    ("2021-22", BASE_DIR / "data" / "raw" / "2021-22"),
    ("2022-23", BASE_DIR / "data" / "raw" / "2022-23"),
    ("2023-24", BASE_DIR / "data" / "raw" / "2023-24"),
    ("2024-25", BASE_DIR / "data" / "raw" / "2024-25"),
    ("2025-26", BASE_DIR / "OFLC_Wages_2025-26_Updated"),
]

SOURCES = {
    "all_industries": ("ALC_Export.csv", "All Industries"),
    "acwia_higher_education": ("EDC_Export.csv", "ACWIA / Higher Education"),
}

COUNTY_ALIASES = {
    ("AK", "Anchorage Borough"): "Anchorage Municipality",
    ("AK", "Juneau Borough"): "Juneau City and Borough",
    ("AK", "Sitka Borough"): "Sitka City and Borough",
    ("AK", "Yakutat Borough"): "Yakutat City and Borough",
    ("AK", "Petersburg Borough"): "Petersburg Census Area",
    ("AK", "Prince of Wales-Outer Ketchikan Census Area"): "Prince of Wales-Hyder Census Area",
    ("AK", "Wade Hampton Census Area"): "Kusilvak Census Area",
    ("IL", "LaSalle County"): "La Salle County",
    ("LA", "LaSalle Parish"): "La Salle Parish",
}


def decode_text(value: str) -> str:
    value = value.replace("\xa0", " ").strip()
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")


def normalize_name(value: str) -> str:
    value = decode_text(value).lower()
    value = value.replace(".", "").replace("'", "")
    value = value.replace("&", "and")
    value = value.replace("-", " ")
    value = value.replace("lasalle", "la salle")
    value = re.sub(r"\bsaint\b", "st", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def canonical_county_name(state_ab: str, county_name: str) -> str:
    county_name = decode_text(county_name)
    county_name = COUNTY_ALIASES.get((state_ab, county_name), county_name)
    if state_ab == "PR" and not county_name.lower().endswith("municipio"):
        county_name = f"{county_name} Municipio"
    return normalize_name(county_name)


def csv_reader(path: Path):
    for encoding in ("utf-8-sig", "latin1"):
        try:
            with path.open(newline="", encoding=encoding) as handle:
                yield from csv.DictReader(handle)
            return
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("utf-8", b"", 0, 1, f"Unable to decode {path}")


def resolve_file(year_dir: Path, filename: str) -> Path:
    direct = year_dir / filename
    if direct.exists():
        return direct
    nested = list(year_dir.rglob(filename))
    if len(nested) == 1:
        return nested[0]
    raise FileNotFoundError(f"Could not resolve {filename} inside {year_dir}")


def load_county_fips() -> dict[tuple[str, str], str]:
    mapping = {}
    with COUNTY_CODES_PATH.open(encoding="latin1") as handle:
        for line in handle:
            state_ab, state_fp, county_fp, county_name, _ = line.strip().split(",")
            mapping[(state_ab, normalize_name(county_name))] = f"{state_fp}{county_fp}"
    return mapping


def build_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        DROP TABLE IF EXISTS years;
        DROP TABLE IF EXISTS sources;
        DROP TABLE IF EXISTS occupations;
        DROP TABLE IF EXISTS wages;
        DROP TABLE IF EXISTS geography;
        DROP TABLE IF EXISTS coverage;

        CREATE TABLE years (
            year TEXT PRIMARY KEY,
            sort_order INTEGER NOT NULL
        );

        CREATE TABLE sources (
            source_id TEXT PRIMARY KEY,
            label TEXT NOT NULL
        );

        CREATE TABLE occupations (
            soc_code TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL
        );

        CREATE TABLE wages (
            year TEXT NOT NULL,
            source_id TEXT NOT NULL,
            area_code TEXT NOT NULL,
            soc_code TEXT NOT NULL,
            level1 REAL,
            level2 REAL,
            level3 REAL,
            level4 REAL,
            average REAL,
            label TEXT NOT NULL,
            PRIMARY KEY (year, source_id, area_code, soc_code)
        );

        CREATE TABLE geography (
            year TEXT NOT NULL,
            area_code TEXT NOT NULL,
            area_name TEXT NOT NULL,
            state_ab TEXT NOT NULL,
            state_name TEXT NOT NULL,
            county_name TEXT NOT NULL,
            county_fips TEXT,
            PRIMARY KEY (year, area_code, state_ab, county_name)
        );

        CREATE TABLE coverage (
            year TEXT NOT NULL,
            total_county_rows INTEGER NOT NULL,
            matched_county_rows INTEGER NOT NULL,
            unmatched_county_rows INTEGER NOT NULL,
            PRIMARY KEY (year)
        );

        CREATE INDEX idx_wages_lookup
        ON wages (year, source_id, soc_code);

        CREATE INDEX idx_geography_lookup
        ON geography (year, area_code, county_fips);
        """
    )


def to_float(value: str):
    value = value.strip()
    return float(value) if value else None


def load_occupations(connection: sqlite3.Connection, year: str, path: Path) -> None:
    rows = [
        (
            row["soccode"],
            decode_text(row.get("Title") or row.get("soctitle") or ""),
            decode_text(row.get("Description") or row.get("socdefinition") or ""),
        )
        for row in csv_reader(path)
    ]
    connection.executemany(
        """
        INSERT INTO occupations (soc_code, title, description)
        VALUES (?, ?, ?)
        ON CONFLICT(soc_code) DO UPDATE SET
            title = excluded.title,
            description = excluded.description
        """,
        rows,
    )


def load_wages(connection: sqlite3.Connection, year: str, source_id: str, path: Path) -> None:
    batch = []
    for row in csv_reader(path):
        if row["GeoLvl"] != "1":
            continue
        batch.append(
            (
                year,
                source_id,
                row["Area"],
                row["SocCode"],
                to_float(row["Level1"]),
                to_float(row["Level2"]),
                to_float(row["Level3"]),
                to_float(row["Level4"]),
                to_float(row["Average"]),
                row.get("Label", "").strip(),
            )
        )
        if len(batch) >= 25000:
            connection.executemany(
                """
                INSERT OR REPLACE INTO wages
                (year, source_id, area_code, soc_code, level1, level2, level3, level4, average, label)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                batch,
            )
            batch.clear()

    if batch:
        connection.executemany(
            """
            INSERT OR REPLACE INTO wages
            (year, source_id, area_code, soc_code, level1, level2, level3, level4, average, label)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            batch,
        )


def load_geography(
    connection: sqlite3.Connection, year: str, path: Path, county_fips_map: dict[tuple[str, str], str]
) -> None:
    batch = []
    total_rows = 0
    matched_rows = 0

    for row in csv_reader(path):
        total_rows += 1
        state_ab = row["StateAb"].strip()
        county_name = decode_text(row["CountyTownName"])
        county_fips = county_fips_map.get((state_ab, canonical_county_name(state_ab, county_name)))
        if county_fips:
            matched_rows += 1

        batch.append(
            (
                year,
                row["Area"],
                decode_text(row["AreaName"]),
                state_ab,
                decode_text(row["State"]),
                county_name,
                county_fips,
            )
        )

        if len(batch) >= 5000:
            connection.executemany(
                """
                INSERT OR REPLACE INTO geography
                (year, area_code, area_name, state_ab, state_name, county_name, county_fips)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                batch,
            )
            batch.clear()

    if batch:
        connection.executemany(
            """
            INSERT OR REPLACE INTO geography
            (year, area_code, area_name, state_ab, state_name, county_name, county_fips)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            batch,
        )

    connection.execute(
        """
        INSERT OR REPLACE INTO coverage
        (year, total_county_rows, matched_county_rows, unmatched_county_rows)
        VALUES (?, ?, ?, ?)
        """,
        (year, total_rows, matched_rows, total_rows - matched_rows),
    )


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    county_fips_map = load_county_fips()

    connection = sqlite3.connect(DB_PATH)
    build_schema(connection)

    connection.executemany(
        "INSERT INTO years (year, sort_order) VALUES (?, ?)",
        [(year, index) for index, (year, _) in enumerate(YEARS, start=1)],
    )
    connection.executemany(
        "INSERT INTO sources (source_id, label) VALUES (?, ?)",
        [(source_id, label) for source_id, (_, label) in SOURCES.items()],
    )

    for year, year_dir in YEARS:
        load_occupations(connection, year, resolve_file(year_dir, "oes_soc_occs.csv"))
        load_geography(connection, year, resolve_file(year_dir, "Geography.csv"), county_fips_map)
        for source_id, (filename, _) in SOURCES.items():
            load_wages(connection, year, source_id, resolve_file(year_dir, filename))
        connection.commit()

    connection.close()


if __name__ == "__main__":
    main()
