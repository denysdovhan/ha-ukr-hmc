# meteo.gov.ua reverse‑engineering notes (2026‑02‑02)

## How the site loads weather data

The main JS bundle is `https://www.meteo.gov.ua/_/_.js?2025-03-11-2`. It defines `UANA.*` methods and fetches JSON from several `/_/m/*.js` endpoints and `/__e5m.json`.

### Core weather endpoints

1. **Current observations for one station**
   - URL: `https://www.meteo.gov.ua/_/m/{STATION_ID}.js`
   - Example: `https://www.meteo.gov.ua/_/m/33345.js`
   - Response: JSON array of the latest 8 observation times (3‑hour steps).

   **Schema (per entry)**
   - `CD` (string): date `YYYY-MM-DD`
   - `CT` (number): hour (0–23)
   - `C_T` (number): air temperature °C (can be decimal)
   - `C_V` (number): humidity %
   - `C_A` (number): air pressure (mm Hg)
   - `C_W` (number): wind speed (m/s)
   - `C_D` (number): wind direction code (index into `METEO_WINDS`)
   - `IM` (number): weather icon code (day)
   - `IM_N` (number): weather icon code (night)
   - `IT` (number): icon title selector (0/1, choose between `METEO_ICONS_TITLES0` vs `METEO_ICONS_TITLES`)
   - `TX` (number): icon title code
   - `C_I` (number): unknown (always 0 in sample)
   - `C_O` (number): unknown/phenomena (seen 0–7)
   - `SR` (string): sunrise time in `HHMM` (no colon)
   - `SS` (string): sunset time in `HHMM`

   **Sample (Kyiv 33345, first/last items)**
   ```json
   [
     {"CD":"2026-02-01","CT":11,"C_A":750,"C_V":73,"C_T":-15.2,"C_W":3,"C_D":35,"C_I":0,"C_O":0,"IM":41,"IT":0,"TX":0,"IM_N":66,"SR":"733","SS":"1650"},
     {"CD":"2026-02-02","CT":8,"C_A":750,"C_V":87,"C_T":-18.6,"C_W":1,"C_D":32,"C_I":0,"C_O":7,"IM":44,"IT":0,"TX":7,"IM_N":69,"SR":"732","SS":"1652"}
   ]
   ```

2. **Current observations for all stations (map layer)**
   - URL: `https://www.meteo.gov.ua/_/m/current.js`
   - Response: JSON object keyed by station id (string), each value is a single observation record (same fields as above).

   **Sample keys**: `"33049"`, `"33067"`, `"33075"` …

   **Sample record**
   ```json
   {
     "CD":"2026-02-02","CT":8,"C_A":749,"C_V":84,"C_T":-26.3,"C_W":0,
     "C_D":0,"C_I":0,"C_O":0,"IM":41,"IT":0,"TX":0,"IM_N":66,"SR":"730","SS":"1638"
   }
   ```

3. **Forecast for all stations**
   - URL: `https://www.meteo.gov.ua/_/m/prognoz.js`
   - Response: JSON object keyed by station id. Each station key maps to date‑keyed forecast objects.

   **Schema (per date)**
   - `T_N` (number): night temperature (single value)
   - `T_D` (number): day temperature (single value)
   - `T_IN_F` / `T_IN_T` (number): night temp range (from/to)
   - `T_ID_F` / `T_ID_T` (number): day temp range (from/to)
   - `I_D` (number): day icon code
   - `I_N` (number): night icon code
   - `HM` (string): cloudiness (UA)
   - `O_D`, `O_N` (string): precipitation (UA) day/night
   - `HM_EN`, `O_D_EN`, `O_N_EN` (string): English strings
   - `WD_N` (number): wind direction code for day
   - `WD_S` (string): wind speed range for day (e.g., `"5-10"`)
   - `WN_N` (number): wind direction code for night
   - `WN_S` (string): wind speed range for night (e.g., `"3-8"`)
   - `SR` / `SS` (string): sunrise/sunset `H:MM`
   - `MP` (number): unknown (seen 13)

   **Sample (Kyiv 33345, 2026‑02‑02)**
   ```json
   {
     "T_N":-23,"T_D":-15,"T_IN_F":-24,"T_IN_T":-22,"T_ID_F":-16,"T_ID_T":-14,
     "I_D":44,"I_N":69,
     "HM":"хмарно з проясненнями","O_D":"без опадів","O_N":"без опадів",
     "HM_EN":"cloudy with clearings","O_D_EN":"without precipitation","O_N_EN":"without precipitation",
     "WD_N":36,"WD_S":"5-10","WN_N":36,"WN_S":"3-8",
     "SR":"7:32","SS":"16:52","MP":13
   }
   ```

4. **Day/night flag + site alerts**
   - URL: `https://www.meteo.gov.ua/_/_e5m.json`
   - Response:
     - `dn`: object keyed by station id, `1` = night, `0` = day
     - `attns_meteo`, `attns_hydro`, `attns_snigo`, `attns_radio`, `attns_fire`: 0/1 flags

   **Sample**
   ```json
   {"dn":{"33345":0, "33347":0, ...},"attns_meteo":0,"attns_hydro":1,"attns_snigo":1,"attns_radio":0,"attns_fire":0}
   ```

### Station list (ID ↔ name/coords)

- URL: `https://www.meteo.gov.ua/ua/_meteo-stations.js?2025-02-11-0`
- Response defines two globals:
  - `METEO_OBLASTI`: oblast id → oblast name (UA)
  - `METEO_STATIONS`: sequential index → station metadata

**Station schema** (per entry in `METEO_STATIONS`):
- `i` (number): station id (used in API endpoints)
- `o` (number): oblast id (links to `METEO_OBLASTI`)
- `h` (number): altitude (meters)
- `k` (number): unknown station code
- `t` (string): station name (UA)
- `x`, `y` (string): latitude/longitude
- `z` (number): display zoom category (UI)
- `dx`, `dy` (number): map label offsets

Example:
```json
{"i":33345,"o":1,"h":167,"k":2,"t":"Київ","x":"50.391792297363","y":"30.53563117981","z":5,"dx":0,"dy":0}
```

### Icon and wind mappings

- Weather text mapping files:
  - `https://www.meteo.gov.ua/ua/_meteo-icons.js?211230`
    - `METEO_ICONS_TITLES` / `METEO_ICONS_TITLES0` (UA) 
  - `https://www.meteo.gov.ua/ua/_meteo-winds.js?211230`
    - `METEO_WINDS` array, each entry has:
      - `r`: short direction (e.g., `NNE`)
      - `t`: UA name (e.g., `Північно-Східний`)

These are used to interpret `IM/IM_N/TX/IT` and `C_D` / `WD_N` / `WN_N` codes.

## Other related data endpoints discovered

These are not core weather, but exist in the same JS bundle:
- `/_/m/hydroday.js?75{THASH}`: hydrology daily map data
- `/_/m/hydroauto.js?2{THASH}`: hydrology auto-post data
- `/_/m/radioday.js?4{THASH}`: radiation daily map data
- `/_/m/radioday.js{THASH}`: radiation table data
- `/_/m/snigost.js?{THASH}`: snow/avalanche station data


## Additional endpoints probed (details)

### Hydrology daily map data
- URL: `https://www.meteo.gov.ua/_/m/hydroday.js?75`
- Content-Type: `application/javascript` (body is JSON)
- Response: object keyed by hydrology post id; key `0` is update date string.

**Schema (per post id)**
- `PD` (string): date `DD.MM.YYYY`
- `FR` (number): actual water level (cm)
- `FR_BS` (number): water level above sea (m)
- `C_FR` (number): daily change (m)
- `TW` (number): water temperature °C
- `L` (number): danger level bucket (0+)

**Sample**
```json
{
  "0":"02.02.2026",
  "44025":{"PD":"02.02.2026","FR":93,"FR_BS":647.43,"C_FR":0.01,"TW":0,"L":0}
}
```

### Hydrology auto‑posts (near‑real‑time)
- URL: `https://www.meteo.gov.ua/_/m/hydroauto.js?2`
- Content-Type: `application/javascript` (body is JSON)
- Response: object keyed by post id; key `0` is update timestamp.

**Schema (per post id)**
- `DT` (string): date/time `DD.MM.YYYY, HH:MM`
- `HH` (number): water level (cm; can be negative)

**Sample**
```json
{
  "0":"02.02.2026, 11:00",
  "42137":{"DT":"02.02.2026, 11:00","HH":137}
}
```

### Radiation daily data
- URL (map layer): `https://www.meteo.gov.ua/_/m/radioday.js?4`
- URL (table): `https://www.meteo.gov.ua/_/m/radioday.js`
- Content-Type: `application/javascript` (body is JSON)
- Response: object keyed by station id; key `0` is update date string.

**Schema (per station id)**
- `CD` (string): date `DD.MM.YYYY`
- `CH` (string): time `HH:MM:SS`
- `VR` (number): exposure dose rate (µR/hour)
- `VZ` (number): dose rate (nSv/h)

**Sample**
```json
{
  "0":"02.02.2026",
  "33156":{"CD":"02.02.2026","CH":"11:00:00","VR":13,"VZ":114}
}
```

### Snow/avalanche station data
- URL: `https://www.meteo.gov.ua/_/m/snigost.js`
- Content-Type: `application/javascript` (body is JSON)
- Response: object keyed by station id; key `0` is update date string.

**Schema (per station id)**
- `ST` (number): station id
- `TT` (number): air temperature °C
- `SN` (number): snow cover height (cm)
- `SD` (number): snow density (unknown units)
- `WD` (number): wind direction code
- `WS` (number): wind speed
- `VL` (number): humidity %
- `HT` (string): cloudiness (UA)
- `OT` (string): phenomena (UA)

**Sample**
```json
{
  "0":"02.02.2026",
  "9":{"ST":9,"TT":-4,"SN":11,"SD":0,"WD":0,"WS":0,"VL":96,"HT":"Хмарно","OT":"Туман б/змін,небо ..."}
}
```

### Avalanche area polygons (geo)
- URL: `https://www.meteo.gov.ua/_/geo/sl/a/{AREA}.json?2024-12-24-0` (AREA = 1..5)
- Response: GeoJSON `GeometryCollection` with `geometries` array.

## Location / city / region mapping

### Meteorological stations (cities)
- Station list: `https://www.meteo.gov.ua/ua/_meteo-stations.js?2025-02-11-0`
- Each station provides a **station id** (`i`), city name (`t`), coords (`x`,`y`), and oblast id (`o`).
- The **station id** is the key used in weather endpoints:
  - current: `/_/m/{station_id}.js`
  - forecast: `/_/m/prognoz.js` (top‑level key = station id)
  - current map: `/_/m/current.js` (top‑level key = station id)

### Regions (oblasts)
- `METEO_OBLASTI` maps oblast id → oblast name (UA).
- This is used to group stations in the city selector (regions → cities).

### Hydrology posts & radiation stations (locations)
- Hydrology posts list: `https://www.meteo.gov.ua/ua/_hydro-posts.js?221207-0`
  - `HYDRO_POSTS` entries contain river name (`R`), post name (`P`), and coordinates (`X`,`Y`).
- Radiation stations list: `https://www.meteo.gov.ua/ua/_radio-posts.js?221207-0`
  - `RADIO_POSTS` entries contain station name (`P`), coordinates (`X`,`Y`), and altitude (`H`).

## Content‑Type vs payload note

Many `/_/m/*.js` endpoints return **JSON payloads** but are served with
`Content-Type: application/javascript`. The code in `/_/_.js` still calls `fetch(...).json()`
for these endpoints, which works because the body is valid JSON.

**Implication:** you can `curl` these endpoints directly and parse them as JSON.
The `.js` extension does not mean you must evaluate JavaScript. The body is plain JSON text.

## Notes for Home Assistant integration

- Station discovery: parse `METEO_STATIONS` for station id, name, and coordinates.
- Current conditions: use `/_/m/{station_id}.js` (latest entry by `CD`+`CT`).
- Forecast: use `/_/m/prognoz.js` and pick `station_id` then date keys.
- Sunrise/sunset are provided per observation/forecast.
- Wind direction codes require `METEO_WINDS` mapping.
- Icon/condition text can be derived from `METEO_ICONS_TITLES` + `TX` and `IT`.


## Endpoint notes (additional probing)

- `/_/m/hydroday.js?4` appears to return the **same JSON** as `/_/m/hydroday.js?75` (at least on 2026‑02‑02). The numeric query likely selects a layer or map scope, but both returned identical data in this probe.
- `/_/m/radioday.js?4` and `/_/m/radioday.js` returned identical data in this probe.

## Location / city / region lookup workflow

The site does not expose a separate “city search” API. Instead it uses a **station catalog** and selects a station id:

1. **List all stations** with `/_meteo-stations.js` and build a lookup by name and oblast.
2. **Pick a station id** and call:
   - current: `/_/m/{station_id}.js`
   - forecast: `/_/m/prognoz.js` → `forecast[station_id][date]`

### Region (oblast) mapping
- `METEO_OBLASTI` provides oblast names by id.
- Stations reference oblast via `o`.
- To get “all stations in a region,” filter `METEO_STATIONS` by `o`.

### City lookup (by name)
- Match user city name against `METEO_STATIONS[*].t` (UA names).
- Station id is `METEO_STATIONS[*].i`.
- If you need English, `/_/m/prognoz.js` includes `HM_EN`, `O_D_EN`, `O_N_EN`, but station names are UA in the station list.

### Geolocation → nearest station
The site picks the nearest station to a lat/lon by scanning all stations and minimizing `abs(lat - x) + abs(lon - y)`. This is implemented in `UANA.MYGEO()` in `/_/_.js`. You can reproduce this to map arbitrary coordinates to the nearest station.

## Exported mappings (JSON)

For Home Assistant use, I exported the full mappings:
- `meteo_icons.json` → `METEO_ICONS_TITLES` and `METEO_ICONS_TITLES0`
- `meteo_winds.json` → `METEO_WINDS`

Files are at:
- `/Users/denysd/meteo_icons.json`
- `/Users/denysd/meteo_winds.json`


## English endpoints

The site has English versions of the static JS datasets (same schema, translated strings):

- Stations (oblast + station names in EN):
  - `https://www.meteo.gov.ua/en/_meteo-stations.js?2025-02-11-0`

- Icon titles in EN:
  - `https://www.meteo.gov.ua/en/_meteo-icons.js?211230`

- Wind direction names in EN:
  - `https://www.meteo.gov.ua/en/_meteo-winds.js?211230`

- Hydrology posts (river/post names in EN):
  - `https://www.meteo.gov.ua/en/_hydro-posts.js?221207-0`

- Radiation posts (station names in EN):
  - `https://www.meteo.gov.ua/en/_radio-posts.js?221207-0`

These endpoints are useful for English UI labels, while the **data endpoints** (`/_/m/*.js`, `/_/_e5m.json`) remain the same.


**Language independence note:** the primary data endpoints `/_/m/*.js` and `/_/_e5m.json` are language‑independent; only the static lookup tables under `/ua/` or `/en/` change the human‑readable labels (station names, oblast names, icon titles, wind names, etc.).
