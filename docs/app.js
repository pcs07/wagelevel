const state = {
  meta: null,
  geojson: null,
  selectedYear: "",
  selectedState: "ALL",
  selectedSource: "all_industries",
  selectedMetric: "level1",
  selectedSocCode: "15-1252",
  currentRows: [],
  geoCache: new Map(),
  wageCache: new Map(),
  countyFeaturesById: new Map(),
  addressSuggestionCache: new Map(),
  addressSuggestionTimers: new Map(),
};

const palette = {
  ink: "#172224",
  warm: "#a95634",
  paper: "#fbf6ee",
};

const STATE_LABEL_POINTS = [
  { abbr: "AL", lat: 32.8, lon: -86.8 },
  { abbr: "AZ", lat: 34.2, lon: -111.8 },
  { abbr: "AR", lat: 34.9, lon: -92.4 },
  { abbr: "CA", lat: 37.2, lon: -119.5 },
  { abbr: "CO", lat: 39.0, lon: -105.5 },
  { abbr: "CT", lat: 41.6, lon: -72.7 },
  { abbr: "DE", lat: 39.0, lon: -75.5 },
  { abbr: "DC", lat: 38.9, lon: -77.0 },
  { abbr: "FL", lat: 28.4, lon: -82.0 },
  { abbr: "GA", lat: 32.7, lon: -83.3 },
  { abbr: "ID", lat: 44.2, lon: -114.4 },
  { abbr: "IL", lat: 40.0, lon: -89.2 },
  { abbr: "IN", lat: 39.9, lon: -86.3 },
  { abbr: "IA", lat: 42.0, lon: -93.5 },
  { abbr: "KS", lat: 38.5, lon: -98.2 },
  { abbr: "KY", lat: 37.6, lon: -85.3 },
  { abbr: "LA", lat: 31.2, lon: -92.3 },
  { abbr: "ME", lat: 45.2, lon: -69.2 },
  { abbr: "MD", lat: 39.0, lon: -76.7 },
  { abbr: "MA", lat: 42.3, lon: -71.8 },
  { abbr: "MI", lat: 44.4, lon: -85.4 },
  { abbr: "MN", lat: 46.3, lon: -94.2 },
  { abbr: "MS", lat: 32.7, lon: -89.7 },
  { abbr: "MO", lat: 38.5, lon: -92.5 },
  { abbr: "MT", lat: 47.0, lon: -109.6 },
  { abbr: "NE", lat: 41.5, lon: -99.7 },
  { abbr: "NV", lat: 39.4, lon: -116.6 },
  { abbr: "NH", lat: 43.7, lon: -71.6 },
  { abbr: "NJ", lat: 40.1, lon: -74.5 },
  { abbr: "NM", lat: 34.4, lon: -106.1 },
  { abbr: "NY", lat: 42.9, lon: -75.5 },
  { abbr: "NC", lat: 35.5, lon: -79.4 },
  { abbr: "ND", lat: 47.5, lon: -100.5 },
  { abbr: "OH", lat: 40.4, lon: -82.8 },
  { abbr: "OK", lat: 35.6, lon: -97.5 },
  { abbr: "OR", lat: 43.9, lon: -120.6 },
  { abbr: "PA", lat: 41.0, lon: -77.7 },
  { abbr: "RI", lat: 41.7, lon: -71.5 },
  { abbr: "SC", lat: 33.8, lon: -80.9 },
  { abbr: "SD", lat: 44.4, lon: -100.2 },
  { abbr: "TN", lat: 35.8, lon: -86.4 },
  { abbr: "TX", lat: 31.5, lon: -99.3 },
  { abbr: "UT", lat: 39.4, lon: -111.6 },
  { abbr: "VT", lat: 44.0, lon: -72.7 },
  { abbr: "VA", lat: 37.5, lon: -78.8 },
  { abbr: "WA", lat: 47.4, lon: -120.7 },
  { abbr: "WV", lat: 38.6, lon: -80.6 },
  { abbr: "WI", lat: 44.6, lon: -89.7 },
  { abbr: "WY", lat: 43.0, lon: -107.6 },
];

const yearSelect = document.getElementById("year-select");
const stateSelect = document.getElementById("state-select");
const sourceSelect = document.getElementById("source-select");
const metricSelect = document.getElementById("metric-select");
const jobCodeInput = document.getElementById("job-code-input");
const jobCodes = document.getElementById("job-codes");
const addressInputs = [
  document.getElementById("address-1"),
  document.getElementById("address-2"),
  document.getElementById("address-3"),
];
const addressSuggestionLists = [
  document.getElementById("address-1-suggestions"),
  document.getElementById("address-2-suggestions"),
  document.getElementById("address-3-suggestions"),
];
const compareAddressesButton = document.getElementById("compare-addresses");
const compareStatus = document.getElementById("compare-status");
const addressCompareBody = document.getElementById("address-compare-body");
const selectionTitle = document.getElementById("selection-title");
const selectionSubtitle = document.getElementById("selection-subtitle");
const countyCount = document.getElementById("county-count");
const areaCount = document.getElementById("area-count");
const coverageCount = document.getElementById("coverage-count");
const topCountyTable = document.getElementById("top-county-table");

function formatMoney(value) {
  if (value == null || Number.isNaN(value)) return "N/A";
  return `$${value.toFixed(2)}`;
}

function metricLabel(metricId) {
  return {
    level1: "Wage Level 1 Annual",
    level2: "Wage Level 2 Annual",
    level3: "Wage Level 3 Annual",
    level4: "Wage Level 4 Annual",
  }[metricId];
}

function selectedOccupation() {
  return state.meta.occupations.find((item) => item.socCode === state.selectedSocCode);
}

function selectedSourceLabel() {
  const source = state.meta.sources.find((item) => item.id === state.selectedSource);
  return source ? source.label : state.selectedSource;
}

function selectedStateLabel() {
  return state.selectedState === "ALL" ? "All states" : state.selectedState;
}

function availableSocCodes() {
  return state.meta.availability?.[state.selectedYear]?.[state.selectedSource] || [];
}

function availableOccupations() {
  const allowed = new Set(availableSocCodes());
  return state.meta.occupations.filter((item) => allowed.has(item.socCode));
}

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${url}`);
  }
  return response.json();
}

async function getExternalJson(url, callbackParam = "callback") {
  try {
    const response = await fetch(url, {
      headers: {
        Accept: "application/json",
      },
    });
    if (!response.ok) {
      throw new Error(`External request failed: ${response.status}`);
    }
    return response.json();
  } catch (fetchError) {
    return getJsonp(url, callbackParam);
  }
}

function getJsonp(url, callbackParam = "callback") {
  return new Promise((resolve, reject) => {
    const callbackName = `jsonp_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    const script = document.createElement("script");
    const timer = setTimeout(() => {
      cleanup();
      reject(new Error("Address lookup timed out."));
    }, 10000);

    function cleanup() {
      clearTimeout(timer);
      delete window[callbackName];
      script.remove();
    }

    window[callbackName] = (payload) => {
      cleanup();
      resolve(payload);
    };

    script.onerror = () => {
      cleanup();
      reject(new Error("Address service is unavailable right now."));
    };

    const separator = url.includes("?") ? "&" : "?";
    script.src = `${url}${separator}${callbackParam}=${callbackName}`;
    document.body.appendChild(script);
  });
}

function normalizeCountyName(name) {
  return (name || "")
    .toLowerCase()
    .replace(/\./g, "")
    .replace(/'/g, "")
    .replace(/-/g, " ")
    .replace(/\bsaint\b/g, "st")
    .replace(/\bcounty\b/g, "")
    .replace(/\bparish\b/g, "")
    .replace(/\bborough\b/g, "")
    .replace(/\bcity and borough\b/g, "")
    .replace(/\bcensus area\b/g, "")
    .replace(/\bmunicipio\b/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function setAddressSuggestions(index, suggestions) {
  const datalist = addressSuggestionLists[index];
  datalist.innerHTML = "";
  suggestions.forEach((suggestion) => {
    const option = document.createElement("option");
    option.value = suggestion;
    datalist.appendChild(option);
  });
}

async function fetchAddressSuggestions(query) {
  const normalized = query.trim();
  if (normalized.length < 6) {
    return [];
  }

  if (state.addressSuggestionCache.has(normalized)) {
    return state.addressSuggestionCache.get(normalized);
  }

  const url = new URL("https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/suggest");
  url.searchParams.set("f", "pjson");
  url.searchParams.set("countryCode", "USA");
  url.searchParams.set("maxSuggestions", "5");
  url.searchParams.set("text", normalized);
  const payload = await getExternalJson(url.toString());
  const suggestions = (payload || [])
    .suggestions?.map((match) => match.text)
    .filter(Boolean)
    .slice(0, 5);

  state.addressSuggestionCache.set(normalized, suggestions);
  return suggestions;
}

function scheduleAddressSuggestions(index) {
  const query = addressInputs[index].value.trim();
  if (state.addressSuggestionTimers.has(index)) {
    clearTimeout(state.addressSuggestionTimers.get(index));
  }

  if (query.length < 6) {
    setAddressSuggestions(index, []);
    return;
  }

  const timer = setTimeout(async () => {
    try {
      const suggestions = await fetchAddressSuggestions(query);
      if (addressInputs[index].value.trim() === query) {
        setAddressSuggestions(index, suggestions);
      }
    } catch (error) {
      if (addressInputs[index].value.trim() === query) {
        setAddressSuggestions(index, []);
      }
    }
  }, 220);

  state.addressSuggestionTimers.set(index, timer);
}

async function loadYearGeography(year) {
  if (!state.geoCache.has(year)) {
    state.geoCache.set(year, getJson(`./data/geo/${year}.json`));
  }
  return state.geoCache.get(year);
}

async function loadWages(year, source) {
  const key = `${year}:${source}`;
  if (!state.wageCache.has(key)) {
    state.wageCache.set(key, getJson(`./data/wages/${year}/${source}.json`));
  }
  return state.wageCache.get(key);
}

function populateControls() {
  state.meta.years.forEach((year) => {
    const option = document.createElement("option");
    option.value = year.year;
    option.textContent = year.year;
    yearSelect.appendChild(option);
  });

  state.meta.sources.forEach((source) => {
    const option = document.createElement("option");
    option.value = source.id;
    option.textContent = source.label;
    sourceSelect.appendChild(option);
  });

  state.selectedYear = state.meta.defaultYear;
  state.selectedState = "ALL";
  state.selectedSource = state.meta.defaultSource;
  state.selectedSocCode = state.meta.defaultSocCode;

  yearSelect.value = state.selectedYear;
  sourceSelect.value = state.selectedSource;
  stateSelect.value = state.selectedState;
  syncOccupationOptions();
  jobCodeInput.value = selectedOccupationLabel();
}

function selectedOccupationLabel() {
  const occupation = selectedOccupation();
  return occupation ? occupation.label : state.selectedSocCode;
}

function parseSocCode(rawValue) {
  const match = rawValue.match(/^(\d{2}-\d{4})/);
  return match ? match[1] : "";
}

function syncOccupationOptions() {
  const occupations = availableOccupations();
  jobCodes.innerHTML = "";
  occupations.forEach((occupation) => {
    const option = document.createElement("option");
    option.value = occupation.label;
    jobCodes.appendChild(option);
  });

  if (!occupations.find((occupation) => occupation.socCode === state.selectedSocCode)) {
    state.selectedSocCode = occupations[0]?.socCode || "";
  }
}

function syncStateOptions(rows) {
  const states = Array.from(new Set(rows.map((row) => row.state_ab)))
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b));

  stateSelect.innerHTML = "";
  const allOption = document.createElement("option");
  allOption.value = "ALL";
  allOption.textContent = "All states";
  stateSelect.appendChild(allOption);

  states.forEach((stateAb) => {
    const option = document.createElement("option");
    option.value = stateAb;
    option.textContent = stateAb;
    stateSelect.appendChild(option);
  });

  if (state.selectedState !== "ALL" && !states.includes(state.selectedState)) {
    state.selectedState = "ALL";
  }
  stateSelect.value = state.selectedState;
}

function visibleRows(rows) {
  if (state.selectedState === "ALL") return rows;
  return rows.filter((row) => row.state_ab === state.selectedState);
}

function buildCountyRows(geoRows, wageData, socCode) {
  const labels = wageData.labels || [""];
  const wageRows = wageData.rowsBySoc?.[socCode] || [];
  const wagesByArea = new Map(wageRows.map((row) => [row[0], row]));
  const rows = [];

  geoRows.rows.forEach((geoRow) => {
    const wageRow = wagesByArea.get(geoRow[4]);
    if (!wageRow) return;
    rows.push({
      county_fips: geoRow[0],
      county_name: geoRow[1],
      state_ab: geoRow[2],
      state_name: geoRow[3],
      area_code: geoRow[4],
      area_name: geoRow[5],
      level1: wageRow[1],
      level2: wageRow[2],
      level3: wageRow[3],
      level4: wageRow[4],
      average: wageRow[5],
      label: labels[wageRow[6]] || "",
    });
  });

  return rows;
}

function updateSummary(rows) {
  const occupation = selectedOccupation();
  selectionTitle.textContent = occupation
    ? `${occupation.title} (${occupation.socCode})`
    : state.selectedSocCode;
  selectionSubtitle.textContent = `${state.selectedYear} · ${selectedSourceLabel()} · ${metricLabel(
    state.selectedMetric
  )} · ${selectedStateLabel()}`;
  countyCount.textContent = rows.length.toLocaleString();
  areaCount.textContent = new Set(rows.map((row) => row.area_code)).size.toLocaleString();

  const coverage = state.meta.coverage[state.selectedYear];
  const pct = coverage
    ? ((coverage.matchedCountyRows / coverage.totalCountyRows) * 100).toFixed(1)
    : "0.0";
  coverageCount.textContent = `${pct}%`;
}

function renderMap(rows) {
  const values = rows.map((row) => row[state.selectedMetric]).filter((value) => value != null);
  const visibleStates = new Set(rows.map((row) => row.state_ab));
  const stateLabels = STATE_LABEL_POINTS.filter((item) => visibleStates.has(item.abbr));
  const populatedRows = rows.filter((row) => row[state.selectedMetric] != null);

  Plotly.newPlot(
    "county-map",
    [
      {
        type: "choropleth",
        geojson: state.geojson,
        featureidkey: "id",
        locations: populatedRows.map((row) => row.county_fips),
        z: populatedRows.map((row) => row[state.selectedMetric]),
        text: populatedRows.map((row) => `${row.county_name}, ${row.state_ab}`),
        customdata: populatedRows.map((row) => [
          row.area_name,
          row.level1,
          row.level2,
          row.level3,
          row.level4,
          row.label,
        ]),
        colorscale: [
          [0, "#deefe9"],
          [0.42, "#7cc0b5"],
          [0.72, "#23857a"],
          [1, "#0d5751"],
        ],
        marker: { line: { color: "#f7f0e5", width: 0.3 } },
        hovertemplate:
          "<b>%{text}</b><br>" +
          "Wage area: %{customdata[0]}<br>" +
          "Level 1 annual: %{customdata[1]:$,.2f}<br>" +
          "Level 2 annual: %{customdata[2]:$,.2f}<br>" +
          "Level 3 annual: %{customdata[3]:$,.2f}<br>" +
          "Level 4 annual: %{customdata[4]:$,.2f}<br>" +
          "Flag: %{customdata[5]}<extra></extra>",
        colorbar: { title: metricLabel(state.selectedMetric) },
      },
      {
        type: "scattergeo",
        mode: "text",
        lon: stateLabels.map((item) => item.lon),
        lat: stateLabels.map((item) => item.lat),
        text: stateLabels.map((item) => item.abbr),
        textfont: {
          family: '"Avenir Next", "Segoe UI", sans-serif',
          size: 10,
          color: "#33423f",
        },
        hoverinfo: "skip",
        showlegend: false,
      },
    ],
    {
      paper_bgcolor: "rgba(0,0,0,0)",
      margin: { t: 0, r: 0, b: 0, l: 0 },
      geo: {
        scope: "usa",
        projection: { type: "albers usa" },
        bgcolor: "rgba(0,0,0,0)",
        showlakes: false,
        showland: true,
        landcolor: palette.paper,
        showsubunits: true,
        subunitcolor: "#475754",
        subunitwidth: 1.8,
        showcountries: false,
      },
      annotations: values.length
        ? []
        : [
            {
              text: "No county rows for this selection.",
              x: 0.5,
              y: 0.5,
              xref: "paper",
              yref: "paper",
              showarrow: false,
              font: { size: 18, color: palette.ink },
            },
          ],
      font: { family: '"Avenir Next", "Segoe UI", sans-serif', color: palette.ink },
    },
    { responsive: true, displayModeBar: false }
  );
}

function renderHistogram(rows) {
  const values = rows.map((row) => row[state.selectedMetric]).filter((value) => value != null);

  Plotly.newPlot(
    "histogram",
    [
      {
        type: "histogram",
        x: values,
        marker: { color: palette.warm },
        hovertemplate: `${metricLabel(state.selectedMetric)}: %{x:$,.2f}<br>Count: %{y}<extra></extra>`,
      },
    ],
    {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      margin: { t: 10, r: 15, b: 55, l: 50 },
      xaxis: { title: "Annual wage", gridcolor: "rgba(23,34,36,0.08)" },
      yaxis: { title: "County rows", gridcolor: "rgba(23,34,36,0.08)" },
      font: { family: '"Avenir Next", "Segoe UI", sans-serif', color: palette.ink },
    },
    { responsive: true, displayModeBar: false }
  );
}

function renderTable(rows) {
  topCountyTable.innerHTML = "";
  rows
    .filter((row) => row[state.selectedMetric] != null)
    .sort((a, b) => b[state.selectedMetric] - a[state.selectedMetric])
    .slice(0, 12)
    .forEach((row) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${row.county_name}</td>
        <td>${row.state_ab}</td>
        <td>${row.area_name}</td>
        <td>${formatMoney(row[state.selectedMetric])}</td>
      `;
      topCountyTable.appendChild(tr);
    });
}

function pointInRing(point, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
    const intersects =
      yi > point[1] !== yj > point[1] &&
      point[0] < ((xj - xi) * (point[1] - yi)) / (yj - yi || Number.EPSILON) + xi;
    if (intersects) inside = !inside;
  }
  return inside;
}

function pointInPolygon(point, polygon) {
  if (!polygon.length || !pointInRing(point, polygon[0])) {
    return false;
  }
  for (let i = 1; i < polygon.length; i += 1) {
    if (pointInRing(point, polygon[i])) {
      return false;
    }
  }
  return true;
}

function featureContainsPoint(feature, point) {
  const geometry = feature?.geometry;
  if (!geometry) return false;
  if (geometry.type === "Polygon") {
    return pointInPolygon(point, geometry.coordinates);
  }
  if (geometry.type === "MultiPolygon") {
    return geometry.coordinates.some((polygon) => pointInPolygon(point, polygon));
  }
  return false;
}

function countyFeatureForPoint(lon, lat) {
  const point = [lon, lat];
  for (const row of state.currentRows) {
    const feature = state.countyFeaturesById.get(row.county_fips);
    if (feature && featureContainsPoint(feature, point)) {
      return feature;
    }
  }
  return null;
}

async function geocodeAddress(address) {
  const url = new URL(
    "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
  );
  url.searchParams.set("f", "pjson");
  url.searchParams.set("SingleLine", address);
  url.searchParams.set("outFields", "Match_addr,RegionAbbr");
  url.searchParams.set("maxLocations", "1");
  url.searchParams.set("sourceCountry", "USA");
  const payload = await getExternalJson(url.toString());
  const match = payload?.candidates?.[0];
  const location = match?.location;
  if (!match || !location) {
    return null;
  }

  const feature = countyFeatureForPoint(location.x, location.y);
  if (!feature) {
    return null;
  }

  return {
    matchedAddress: match.address || match.attributes?.Match_addr || address,
    countyFips: feature.id,
  };
}

function renderAddressComparison(results) {
  addressCompareBody.innerHTML = "";

  results.forEach((result) => {
    const tr = document.createElement("tr");

    if (result.error) {
      tr.innerHTML = `
        <td>${result.input}</td>
        <td colspan="7">${result.error}</td>
      `;
      addressCompareBody.appendChild(tr);
      return;
    }

    tr.innerHTML = `
      <td>${result.matchedAddress}</td>
      <td>${result.row.county_name}</td>
      <td>${result.row.state_ab}</td>
      <td>${result.row.area_name}</td>
      <td>${formatMoney(result.row.level1)}</td>
      <td>${formatMoney(result.row.level2)}</td>
      <td>${formatMoney(result.row.level3)}</td>
      <td>${formatMoney(result.row.level4)}</td>
    `;
    addressCompareBody.appendChild(tr);
  });
}

async function compareAddresses() {
  const addresses = addressInputs
    .map((input) => input.value.trim())
    .filter(Boolean)
    .slice(0, 3);

  if (!addresses.length) {
    compareStatus.textContent = "Enter at least one address to compare.";
    addressCompareBody.innerHTML = "";
    return;
  }

  compareAddressesButton.disabled = true;
  compareStatus.textContent = "Resolving addresses...";

  try {
    const results = await Promise.all(
      addresses.map(async (input) => {
        try {
          const geo = await geocodeAddress(input);
          if (!geo) {
            return { input, error: "No county match found for this address." };
          }

          const row = state.currentRows.find((item) => item.county_fips === geo.countyFips);
          if (!row) {
            return {
              input,
              matchedAddress: geo.matchedAddress,
              error: "County found, but no wage row is available for the current year/source/SOC code.",
            };
          }

          return {
            input,
            matchedAddress: geo.matchedAddress,
            row,
          };
        } catch (error) {
          return {
            input,
            error: error.message || "Address lookup failed.",
          };
        }
      })
    );

    renderAddressComparison(results);
    compareStatus.textContent = `Compared ${results.length} address${results.length === 1 ? "" : "es"} for ${selectedOccupationLabel()}.`;
  } finally {
    compareAddressesButton.disabled = false;
  }
}

async function loadMapData() {
  const [geoRows, wageData] = await Promise.all([
    loadYearGeography(state.selectedYear),
    loadWages(state.selectedYear, state.selectedSource),
  ]);
  state.currentRows = buildCountyRows(geoRows, wageData, state.selectedSocCode);
  compareStatus.textContent = "";
  addressCompareBody.innerHTML = "";
  syncStateOptions(state.currentRows);
  const rows = visibleRows(state.currentRows);
  updateSummary(rows);
  renderMap(rows);
  renderHistogram(rows);
  renderTable(rows);
}

async function init() {
  const [meta, geojson] = await Promise.all([
    getJson("./data/meta.json"),
    getJson("./us-counties.geojson"),
  ]);
  state.meta = meta;
  state.geojson = geojson;
  state.countyFeaturesById = new Map(
    (geojson.features || []).map((feature) => [String(feature.id).padStart(5, "0"), feature])
  );
  populateControls();

  yearSelect.addEventListener("change", async (event) => {
    state.selectedYear = event.target.value;
    state.selectedState = "ALL";
    syncOccupationOptions();
    jobCodeInput.value = selectedOccupationLabel();
    await loadMapData();
  });

  stateSelect.addEventListener("change", () => {
    state.selectedState = stateSelect.value;
    const rows = visibleRows(state.currentRows);
    updateSummary(rows);
    renderMap(rows);
    renderHistogram(rows);
    renderTable(rows);
  });

  sourceSelect.addEventListener("change", async (event) => {
    state.selectedSource = event.target.value;
    state.selectedState = "ALL";
    syncOccupationOptions();
    jobCodeInput.value = selectedOccupationLabel();
    await loadMapData();
  });

  metricSelect.addEventListener("change", () => {
    state.selectedMetric = metricSelect.value;
    const rows = visibleRows(state.currentRows);
    updateSummary(rows);
    renderMap(rows);
    renderHistogram(rows);
    renderTable(rows);
  });

  jobCodeInput.addEventListener("change", async () => {
    const socCode = parseSocCode(jobCodeInput.value);
    if (!socCode) {
      jobCodeInput.value = selectedOccupationLabel();
      return;
    }
    state.selectedSocCode = socCode;
    state.selectedState = "ALL";
    jobCodeInput.value = selectedOccupationLabel();
    await loadMapData();
  });

  compareAddressesButton.addEventListener("click", compareAddresses);
  addressInputs.forEach((input, index) => {
    input.addEventListener("input", () => scheduleAddressSuggestions(index));
  });

  await loadMapData();
}

init().catch((error) => {
  selectionTitle.textContent = "Dashboard failed to load.";
  selectionSubtitle.textContent = error.message;
});
