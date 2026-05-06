#!/usr/bin/env python3

import argparse
import json
import sqlite3
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "oflc_wages.sqlite"
DASHBOARD_DIR = BASE_DIR / "county-map-dashboard"
GEOJSON_PATH = BASE_DIR / "us-counties.geojson"
ANNUAL_HOURS = 2080


def json_bytes(payload) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def annualize(value, label):
    if value is None:
        return None
    if label == "Annual Wage":
        return value
    return round(value * ANNUAL_HOURS, 2)


class CountyWageHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/meta":
            self.serve_meta()
            return
        if parsed.path == "/api/map":
            self.serve_map(parse_qs(parsed.query))
            return
        if parsed.path == "/us-counties.geojson":
            self.serve_file(GEOJSON_PATH, "application/geo+json; charset=utf-8")
            return
        super().do_GET()

    def serve_file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_json(self, payload, status: int = HTTPStatus.OK) -> None:
        data = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def open_db(self):
        connection = sqlite3.connect(DB_PATH)
        connection.row_factory = sqlite3.Row
        return connection

    def serve_meta(self) -> None:
        with self.open_db() as connection:
            years = [
                dict(row)
                for row in connection.execute(
                    "SELECT year, sort_order FROM years ORDER BY sort_order DESC"
                )
            ]
            sources = [
                {"id": row["source_id"], "label": row["label"]}
                for row in connection.execute(
                    "SELECT source_id, label FROM sources ORDER BY source_id"
                )
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

        self.serve_json(
            {
                "years": years,
                "sources": sources,
                "occupations": occupations,
                "availability": availability,
                "coverage": coverage,
                "defaultYear": years[0]["year"] if years else "",
                "defaultSource": "all_industries",
                "defaultSocCode": "15-1252",
            }
        )

    def serve_map(self, query: dict[str, list[str]]) -> None:
        year = query.get("year", [""])[0]
        source_id = query.get("source", ["all_industries"])[0]
        soc_code = query.get("soc_code", [""])[0]

        if not year or not soc_code:
            self.serve_json(
                {"error": "Both year and soc_code are required."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        with self.open_db() as connection:
            rows = []
            for row in connection.execute(
                """
                SELECT
                    g.county_fips,
                    g.county_name,
                    g.state_ab,
                    g.state_name,
                    g.area_code,
                    g.area_name,
                    w.level1,
                    w.level2,
                    w.level3,
                    w.level4,
                    w.average,
                    w.label,
                    o.title AS occupation_title
                FROM wages w
                JOIN geography g
                  ON g.year = w.year
                 AND g.area_code = w.area_code
                JOIN occupations o
                  ON o.soc_code = w.soc_code
                WHERE w.year = ?
                  AND w.source_id = ?
                  AND w.soc_code = ?
                  AND g.county_fips IS NOT NULL
                ORDER BY g.state_ab, g.county_name
                """,
                (year, source_id, soc_code),
            ):
                item = dict(row)
                item["annual_level1"] = annualize(item["level1"], item["label"])
                item["annual_level2"] = annualize(item["level2"], item["label"])
                item["annual_level3"] = annualize(item["level3"], item["label"])
                item["annual_level4"] = annualize(item["level4"], item["label"])
                item["annual_average"] = annualize(item["average"], item["label"])
                rows.append(item)

            area_count = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM wages
                WHERE year = ? AND source_id = ? AND soc_code = ?
                """,
                (year, source_id, soc_code),
            ).fetchone()["count"]

            stats = {
                "min_level1": min(
                    (row["annual_level1"] for row in rows if row["annual_level1"] is not None),
                    default=None,
                ),
                "max_level1": max(
                    (row["annual_level1"] for row in rows if row["annual_level1"] is not None),
                    default=None,
                ),
                "min_level2": min(
                    (row["annual_level2"] for row in rows if row["annual_level2"] is not None),
                    default=None,
                ),
                "max_level2": max(
                    (row["annual_level2"] for row in rows if row["annual_level2"] is not None),
                    default=None,
                ),
                "min_level3": min(
                    (row["annual_level3"] for row in rows if row["annual_level3"] is not None),
                    default=None,
                ),
                "max_level3": max(
                    (row["annual_level3"] for row in rows if row["annual_level3"] is not None),
                    default=None,
                ),
                "min_level4": min(
                    (row["annual_level4"] for row in rows if row["annual_level4"] is not None),
                    default=None,
                ),
                "max_level4": max(
                    (row["annual_level4"] for row in rows if row["annual_level4"] is not None),
                    default=None,
                ),
            }

        self.serve_json(
            {
                "year": year,
                "source": source_id,
                "socCode": soc_code,
                "areaCount": area_count,
                "countyCount": len(rows),
                "rows": rows,
                "stats": stats,
                "units": "annual",
                "annualizationHours": ANNUAL_HOURS,
            }
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the OFLC county wage dashboard.")
    parser.add_argument("--port", type=int, default=8123, help="Port to bind the local server.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), CountyWageHandler)
    print(f"Serving county wage dashboard at http://127.0.0.1:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
