#!/usr/bin/env python3

import argparse
import csv
from collections import defaultdict
from pathlib import Path


DEFAULT_ROLE_CODES = [
    "15-1252",  # Software Developers
    "15-2051",  # Data Scientists
    "15-1211",  # Computer Systems Analysts
    "11-3021",  # Computer and Information Systems Managers
]

SOURCE_FILES = {
    "all_industries": "ALC_Export.csv",
    "acwia_higher_education": "EDC_Export.csv",
}

GEOLEVEL_LABELS = {
    "1": "area",
    "2": "contiguous_area",
    "3": "state",
    "4": "national",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare joined OFLC wage extracts for visualization."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("OFLC_Wages_2025-26_Updated"),
        help="Directory containing the extracted OFLC wage files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory for generated CSV files.",
    )
    parser.add_argument(
        "--roles",
        nargs="*",
        default=DEFAULT_ROLE_CODES,
        help="SOC codes to include in the selected-role outputs.",
    )
    return parser.parse_args()


def read_csv_rows(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        yield from csv.DictReader(handle)


def load_occupations(path: Path) -> dict[str, dict[str, str]]:
    occupations = {}
    for row in read_csv_rows(path):
        occupations[row["soccode"]] = {
            "title": row["Title"],
            "description": row["Description"],
        }
    return occupations


def load_areas(path: Path) -> dict[str, dict[str, str]]:
    grouped = defaultdict(list)
    for row in read_csv_rows(path):
        grouped[row["Area"]].append(row)

    areas = {}
    for area_code, rows in grouped.items():
        states = sorted({row["StateAb"] for row in rows if row["StateAb"]})
        state_names = sorted({row["State"] for row in rows if row["State"]})
        counties = sorted(
            {row["CountyTownName"] for row in rows if row["CountyTownName"]}
        )
        areas[area_code] = {
            "area_name": rows[0]["AreaName"],
            "state_ab_list": "|".join(states),
            "state_name_list": "|".join(state_names),
            "county_count": str(len(counties)),
            "county_list": "|".join(counties),
            "county_rows": rows,
        }
    return areas


def serialize_row(
    row: dict[str, str],
    source_name: str,
    occupation: dict[str, str] | None,
    area: dict[str, str] | None,
) -> dict[str, str]:
    occupation = occupation or {"title": "", "description": ""}
    area = area or {
        "area_name": "",
        "state_ab_list": "",
        "state_name_list": "",
        "county_count": "0",
        "county_list": "",
    }
    return {
        "source_name": source_name,
        "area_code": row["Area"],
        "area_name": area["area_name"],
        "state_ab_list": area["state_ab_list"],
        "state_name_list": area["state_name_list"],
        "county_count": area["county_count"],
        "soc_code": row["SocCode"],
        "occupation_title": occupation["title"],
        "occupation_description": occupation["description"],
        "geo_level_code": row["GeoLvl"],
        "geo_level_label": GEOLEVEL_LABELS.get(row["GeoLvl"], "unknown"),
        "level_1": row["Level1"],
        "level_2": row["Level2"],
        "level_3": row["Level3"],
        "level_4": row["Level4"],
        "average": row["Average"],
        "label": row["Label"],
    }


def build_selected_extracts(
    data_dir: Path,
    output_dir: Path,
    areas: dict[str, dict[str, str]],
    occupations: dict[str, dict[str, str]],
    role_codes: set[str],
) -> None:
    selected_path = output_dir / "oflc_wages_selected_roles.csv"
    county_path = output_dir / "oflc_wages_selected_roles_county_map.csv"

    with selected_path.open(
        "w", newline="", encoding="utf-8"
    ) as selected_handle, county_path.open(
        "w", newline="", encoding="utf-8"
    ) as county_handle:
        selected_writer = None
        county_writer = None

        for source_name, filename in SOURCE_FILES.items():
            for row in read_csv_rows(data_dir / filename):
                if row["SocCode"] not in role_codes:
                    continue

                base_row = serialize_row(
                    row=row,
                    source_name=source_name,
                    occupation=occupations.get(row["SocCode"]),
                    area=areas.get(row["Area"]),
                )

                if selected_writer is None:
                    selected_writer = csv.DictWriter(
                        selected_handle, fieldnames=list(base_row.keys())
                    )
                    selected_writer.writeheader()
                selected_writer.writerow(base_row)

                # County map rows are safe for the most local geography only.
                if row["GeoLvl"] != "1":
                    continue

                area = areas.get(row["Area"])
                if not area:
                    continue

                for county in area["county_rows"]:
                    county_row = {
                        **base_row,
                        "county_name": county["CountyTownName"],
                        "county_state_ab": county["StateAb"],
                        "county_state_name": county["State"],
                    }
                    if county_writer is None:
                        county_writer = csv.DictWriter(
                            county_handle, fieldnames=list(county_row.keys())
                        )
                        county_writer.writeheader()
                    county_writer.writerow(county_row)


def build_summary(
    data_dir: Path,
    output_dir: Path,
    areas: dict[str, dict[str, str]],
    occupations: dict[str, dict[str, str]],
    role_codes: set[str],
) -> None:
    summary_path = output_dir / "oflc_selected_role_top_areas.csv"
    fieldnames = [
        "source_name",
        "soc_code",
        "occupation_title",
        "metric",
        "rank",
        "area_code",
        "area_name",
        "state_ab_list",
        "geo_level_code",
        "level_1",
        "average",
        "label",
    ]

    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for source_name, filename in SOURCE_FILES.items():
            per_role = defaultdict(list)
            for row in read_csv_rows(data_dir / filename):
                if row["SocCode"] not in role_codes or row["GeoLvl"] != "1":
                    continue
                if not row["Level1"] or not row["Average"]:
                    continue
                per_role[row["SocCode"]].append(row)

            for soc_code, rows in per_role.items():
                top_rows = sorted(
                    rows,
                    key=lambda item: (float(item["Level1"]), float(item["Average"])),
                    reverse=True,
                )[:10]
                for rank, row in enumerate(top_rows, start=1):
                    area = areas.get(row["Area"], {})
                    occupation = occupations.get(soc_code, {})
                    writer.writerow(
                        {
                            "source_name": source_name,
                            "soc_code": soc_code,
                            "occupation_title": occupation.get("title", ""),
                            "metric": "level_1",
                            "rank": rank,
                            "area_code": row["Area"],
                            "area_name": area.get("area_name", ""),
                            "state_ab_list": area.get("state_ab_list", ""),
                            "geo_level_code": row["GeoLvl"],
                            "level_1": row["Level1"],
                            "average": row["Average"],
                            "label": row["Label"],
                        }
                    )


def main() -> None:
    args = parse_args()
    data_dir = args.data_dir
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    occupations = load_occupations(data_dir / "oes_soc_occs.csv")
    areas = load_areas(data_dir / "Geography.csv")
    role_codes = set(args.roles)

    build_selected_extracts(
        data_dir=data_dir,
        output_dir=output_dir,
        areas=areas,
        occupations=occupations,
        role_codes=role_codes,
    )
    build_summary(
        data_dir=data_dir,
        output_dir=output_dir,
        areas=areas,
        occupations=occupations,
        role_codes=role_codes,
    )


if __name__ == "__main__":
    main()
