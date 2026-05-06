#!/usr/bin/env python3

import json
import shutil
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "oflc_wages.sqlite"
DOCS_DIR = BASE_DIR / "docs"
GEO_DIR = DOCS_DIR / "data" / "geo"
WAGES_DIR = DOCS_DIR / "data" / "wages"
SOURCE_GEOJSON = BASE_DIR / "us-counties.geojson"
TARGET_GEOJSON = DOCS_DIR / "us-counties.geojson"


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def annualize(value, label):
    if value is None:
        return None
    if label == "Annual Wage":
        return round(value, 2)
    return round(value * 2080, 2)


def main() -> None:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    years = [
        dict(row)
        for row in connection.execute(
            "SELECT year, sort_order FROM years ORDER BY sort_order DESC"
        )
    ]
    sources = [
        {"id": row["source_id"], "label": row["label"]}
        for row in connection.execute("SELECT source_id, label FROM sources ORDER BY source_id")
    ]
    occupations = [
        {
            "socCode": row["soc_code"],
            "title": row["title"],
            "description": row["description"],
            "label": f"{row['soc_code']} | {row['title']}",
        }
        for row in connection.execute(
            "SELECT soc_code, title, description FROM occupations ORDER BY soc_code"
        )
    ]

    availability = {}
    for row in connection.execute(
        """
        SELECT year, source_id, soc_code
        FROM wages
        GROUP BY year, source_id, soc_code
        ORDER BY year, source_id, soc_code
        """
    ):
        availability.setdefault(row["year"], {}).setdefault(row["source_id"], []).append(
            row["soc_code"]
        )

    coverage = {
        row["year"]: {
            "totalCountyRows": row["total_county_rows"],
            "matchedCountyRows": row["matched_county_rows"],
            "unmatchedCountyRows": row["unmatched_county_rows"],
        }
        for row in connection.execute("SELECT * FROM coverage")
    }

    write_json(
        DOCS_DIR / "data" / "meta.json",
        {
            "years": years,
            "sources": sources,
            "occupations": occupations,
            "availability": availability,
            "coverage": coverage,
            "defaultYear": years[0]["year"] if years else "",
            "defaultSource": "all_industries",
            "defaultSocCode": "15-1252",
        },
    )

    for year in [row["year"] for row in years]:
        geo_rows = [
            [
                row["county_fips"],
                row["county_name"],
                row["state_ab"],
                row["state_name"],
                row["area_code"],
                row["area_name"],
            ]
            for row in connection.execute(
                """
                SELECT county_fips, county_name, state_ab, state_name, area_code, area_name
                FROM geography
                WHERE year = ? AND county_fips IS NOT NULL
                ORDER BY state_ab, county_name, area_code
                """,
                (year,),
            )
        ]
        write_json(GEO_DIR / f"{year}.json", {"rows": geo_rows})

        for source in [item["id"] for item in sources]:
            labels = [""]
            label_index = {"": 0}
            rows_by_soc = {}

            for row in connection.execute(
                """
                SELECT soc_code, area_code, level1, level2, level3, level4, average, label
                FROM wages
                WHERE year = ? AND source_id = ?
                ORDER BY soc_code, area_code
                """,
                (year, source),
            ):
                label = row["label"] or ""
                if label not in label_index:
                    label_index[label] = len(labels)
                    labels.append(label)

                rows_by_soc.setdefault(row["soc_code"], []).append(
                    [
                        row["area_code"],
                        annualize(row["level1"], label),
                        annualize(row["level2"], label),
                        annualize(row["level3"], label),
                        annualize(row["level4"], label),
                        annualize(row["average"], label),
                        label_index[label],
                    ]
                )

            write_json(
                WAGES_DIR / year / f"{source}.json",
                {"labels": labels, "rowsBySoc": rows_by_soc},
            )

    shutil.copyfile(SOURCE_GEOJSON, TARGET_GEOJSON)
    connection.close()


if __name__ == "__main__":
    main()
