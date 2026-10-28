# GIS & Routing (Person 1)

Turns the Northeast road dataset into a graph and returns 1–3 candidate routes
for the backend. Branch: `feature/gis-routing`. Owns `routing/` and existing
`ml/scripts` road processors (those scripts are not modified unless a defect is
shown).

## What this module provides

```text
find_routes(origin, destination, vehicle_type)
    -> [{route_id, distance_km, duration_min, geometry, segment_ids}]

get_segments(segment_ids)
    -> [{segment_id, length_km, road_class, slope_deg, is_oneway, coordinates, ...}]

get_coverage()
    -> {bbox: [minLng, minLat, maxLng, maxLat], vehicle_types: [truck, van, car]}
```

Request points use `{lat, lng}`. Route geometry is GeoJSON LineString with
`[lng, lat]` vertices, CRS WGS84 / EPSG:4326.

Errors the backend should map:

| Exception | API code | When |
|---|---|---|
| `InvalidRequestError` | `INVALID_REQUEST` | Bad coords, unknown vehicle, same origin/destination |
| `OutOfCoverageError` | `OUT_OF_COVERAGE` | Point outside the study-area bounding box |
| `NoRouteFoundError` | `NO_ROUTE_FOUND` | Snapped but no path, or too far from any node |

## Setup

The full OSM extract (`*.pbf`, `*.gpkg`) stays out of Git. Tests and local
integration use the committed fixture network.

```powershell
cd c:\Nisarga\smart-logistics
python -m routing validate
python -m routing demo
python -m unittest discover -s routing/tests -v
```

No extra packages are required for the fixture path.

### Full dataset (optional)

1. Place `north-eastern-zone.osm.pbf` in `ml/data/raw/roads/`.
2. Run the existing processors (do not edit them):
   - `python ml/scripts/extract_roads.py`
   - `python ml/scripts/process_roads_final.py`
   - `python ml/scripts/validate_roads.py`
3. Route on the GeoPackage:

```powershell
$env:ROUTING_USE_FULL = "1"
# or
$env:ROUTING_DATA_PATH = "ml/data/final/roads/roads_final.gpkg"
python -m routing validate
```

`geopandas` is required only for the GeoPackage path (`routing/requirements.txt`).

If the full graph is slow or missing, keep `ROUTING_USE_FULL` unset so the
backend can integrate against the fixture.

## Demo query (fixture)

| | lat | lng |
|---|---|---|
| Origin (near node A) | 26.1801 | 91.7001 |
| Destination (near node I) | 26.1401 | 91.7399 |
| Vehicle | `truck`, `van` or `car` |

This corridor has two meaningfully different paths (north/east major roads vs
south collector). `seg-ab` and `seg-bc` are one-way eastbound. `seg-isolated`
is disconnected so no-route behaviour can be tested.

## Notes for other people

- Person 2: `get_segments` includes `length_km`, `road_class`, `slope_deg`,
  `is_oneway`, and `coordinates`. Missing slope on the full extract is `null`;
  do not treat that as safe.
- Person 3: import `find_routes`, `get_segments`, `get_coverage` from `routing`.
  Do not call into `ml/scripts`.
- Person 4: colour the map from `routes[].segment_ids` joined with
  `get_segments` coordinates, not from a single solid polyline colour.

Risk-weighted re-routing is out of scope for the sprint (weeks 2–3).
