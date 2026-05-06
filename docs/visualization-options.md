# OFLC Wage Visualization Notes

## What is in the official download

- Wage year: `2025-2026`
- Source bundle: `OFLC_Wages_2025-26.zip`
- Main wage tables:
  - `ALC_Export.csv`: all industries
  - `EDC_Export.csv`: ACWIA / higher-education-oriented wage table
- Supporting tables:
  - `Geography.csv`: maps wage areas to counties and states
  - `oes_soc_occs.csv`: SOC titles and descriptions

## Recommended chart patterns

### 1. Role x Area heatmap

Best first view when you want to compare several occupations across metros or nonmetro areas.

- Rows: occupation title
- Columns: wage area
- Color: `Level1`, `Average`, or `Level4`
- Filter: `source_name = all_industries`
- Filter: `geo_level_code = 1`

Why it works:
- OFLC wages are already structured by occupation and area.
- It quickly shows which markets are expensive for entry-level versus senior roles.

### 2. Ranked horizontal bars

Best for a focused question like "where are software developer Level 1 wages highest?"

- One chart per role
- Bars: top 10 or bottom 10 wage areas
- Metric: `Level1` or `Average`

Why it works:
- Very easy to read
- Good for stakeholders who do not want dense matrices

### 3. Level spread dumbbell chart

Best for showing compression or spread between junior and senior wage levels.

- Y-axis: wage area
- X-axis: hourly wage
- Points: `Level1` and `Level4`
- Line between points: wage spread

Why it works:
- Shows how much a market rewards seniority for the same role
- Useful when comparing H-1B wage-level planning across cities

### 4. Small-multiple county choropleths

Best map option when you want one role at a time.

- Expand each `geo_level_code = 1` area to its counties using `Geography.csv`
- Color counties by the selected wage metric
- One panel per occupation or one interactive role selector

Why it works:
- The geography file gives county membership directly
- Counties are the cleanest map unit you can derive from the bundle without guessing

Important caveat:
- County maps should use `geo_level_code = 1` only. Levels `2-4` are fallback geographies and will look misleading on a local map.

### 5. State summary map

Best when you want a national map that stays simple.

- Aggregate county-expanded area wages to the state level
- Metric: median or average `Level1` for selected roles

Why it works:
- Easier than metro-boundary mapping
- Good executive overview

### 6. Scatter plot: entry wage vs market premium

Best for identifying unusual markets.

- X-axis: `Level1`
- Y-axis: `Average` or `Level4 - Level1`
- Point: wage area
- Color: occupation

Why it works:
- Finds cities with high starting wages versus cities with steep senior premiums

## Data caveats that should be visible in the UI

- `ALC_Export.csv` and `EDC_Export.csv` should not be merged into a single metric without a source selector.
- Some rows use labels like `Annual Wage`, `High Wage`, `No Leveled Wage`, or `No ACWIA`.
- Maps and local rankings should default to `geo_level_code = 1`.
- Roles should use SOC codes under the hood because titles can change across years.

## Files prepared in this workspace

- `output/oflc_wages_selected_roles.csv`
- `output/oflc_wages_selected_roles_county_map.csv`
- `output/oflc_selected_role_top_areas.csv`

Default selected roles:

- `15-1252` Software Developers
- `15-2051` Data Scientists
- `15-1211` Computer Systems Analysts
- `11-3021` Computer and Information Systems Managers
