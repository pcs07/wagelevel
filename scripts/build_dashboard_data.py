#!/usr/bin/env python3

import csv
import json
from collections import defaultdict
from pathlib import Path


INPUT_ROWS = Path("output/oflc_wages_selected_roles.csv")
INPUT_COUNTY_ROWS = Path("output/oflc_wages_selected_roles_county_map.csv")
OUTPUT_JS = Path("dashboard/data.js")


def to_number(value: str):
    if value == "":
        return None
    return float(value)


def slugify(value: str) -> str:
    return (
        value.lower()
        .replace("/", "-")
        .replace(" ", "-")
        .replace(",", "")
        .replace(".", "")
    )


def read_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def build_area_rows():
    rows = []
    roles = {}
    sources = {}

    for row in read_rows(INPUT_ROWS):
        if row["geo_level_code"] != "1":
            continue

        source_id = row["source_name"]
        role_id = row["soc_code"]

        sources[source_id] = {
            "id": source_id,
            "label": "All Industries"
            if source_id == "all_industries"
            else "ACWIA / Higher Education",
        }
        roles[role_id] = {
            "id": role_id,
            "title": row["occupation_title"],
            "description": row["occupation_description"],
            "slug": slugify(row["occupation_title"]),
        }

        rows.append(
            {
                "source": source_id,
                "role": role_id,
                "roleTitle": row["occupation_title"],
                "areaCode": row["area_code"],
                "areaName": row["area_name"],
                "stateList": row["state_ab_list"].split("|") if row["state_ab_list"] else [],
                "countyCount": int(row["county_count"]),
                "level1": to_number(row["level_1"]),
                "level2": to_number(row["level_2"]),
                "level3": to_number(row["level_3"]),
                "level4": to_number(row["level_4"]),
                "average": to_number(row["average"]),
                "label": row["label"],
            }
        )

    return rows, sorted(roles.values(), key=lambda item: item["title"]), sorted(
        sources.values(), key=lambda item: item["id"]
    )


def build_state_rows():
    grouped = defaultdict(
        lambda: {
            "state": "",
            "source": "",
            "role": "",
            "roleTitle": "",
            "level1": [],
            "level2": [],
            "level3": [],
            "level4": [],
            "average": [],
            "countyCount": 0,
        }
    )

    for row in read_rows(INPUT_COUNTY_ROWS):
        if row["geo_level_code"] != "1":
            continue

        state = row["county_state_ab"]
        key = (row["source_name"], row["soc_code"], state)
        group = grouped[key]
        group["state"] = state
        group["source"] = row["source_name"]
        group["role"] = row["soc_code"]
        group["roleTitle"] = row["occupation_title"]
        group["countyCount"] += 1

        for metric, column in [
            ("level1", "level_1"),
            ("level2", "level_2"),
            ("level3", "level_3"),
            ("level4", "level_4"),
            ("average", "average"),
        ]:
            value = to_number(row[column])
            if value is not None:
                group[metric].append(value)

    state_rows = []
    for group in grouped.values():
        state_rows.append(
            {
                "state": group["state"],
                "source": group["source"],
                "role": group["role"],
                "roleTitle": group["roleTitle"],
                "countyCount": group["countyCount"],
                "level1": round(sum(group["level1"]) / len(group["level1"]), 2)
                if group["level1"]
                else None,
                "level2": round(sum(group["level2"]) / len(group["level2"]), 2)
                if group["level2"]
                else None,
                "level3": round(sum(group["level3"]) / len(group["level3"]), 2)
                if group["level3"]
                else None,
                "level4": round(sum(group["level4"]) / len(group["level4"]), 2)
                if group["level4"]
                else None,
                "average": round(sum(group["average"]) / len(group["average"]), 2)
                if group["average"]
                else None,
            }
        )

    return sorted(state_rows, key=lambda item: (item["source"], item["role"], item["state"]))


def main():
    area_rows, roles, sources = build_area_rows()
    state_rows = build_state_rows()

    payload = {
        "generatedFrom": "OFLC 2025-2026 official wage download",
        "roles": roles,
        "sources": sources,
        "metrics": [
            {"id": "level1", "label": "Level 1"},
            {"id": "average", "label": "Average"},
            {"id": "level4", "label": "Level 4"},
        ],
        "areaRows": area_rows,
        "stateRows": state_rows,
    }

    OUTPUT_JS.write_text(
        "window.OFLC_DASHBOARD_DATA = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
