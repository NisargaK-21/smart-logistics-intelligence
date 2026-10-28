# Day 1 validation notes (Person 1)

Signed-off GIS interfaces live in `README.md`. This file records dataset
checks so routing is not built on an untrusted extract.

## Expected schema (from `ml/scripts/process_roads_final.py`)

Required for the graph:

| Field | Role |
|---|---|
| `road_id` | Segment id (`osm_way_<osm_id>` on the full extract) |
| `geometry` | LineString / MultiLineString, EPSG:4326 |
| `length_km` | Edge weight; recomputed from vertices if missing |
| `road_class` | `major`, `collector`, `local`, `special`, `unknown` |
| `road_type` | Original OSM highway tag |
| `is_oneway` / `oneway` | Directed edge if true |
| `lat`, `lon` | Representative point (not used as graph nodes) |

Useful for Person 2, returned by `get_segments`:

- `slope_deg` (fixture only until terrain is joined)
- `surface`

CRS: WGS84. Request points `{lat, lng}`; GeoJSON coordinates `[lng, lat]`.

## Checks implemented (`python -m routing validate`)

1. Feature collection is not empty.
2. Geometries are line types with at least two vertices.
3. Coordinates sit in valid WGS84 ranges (proxy for CRS).
4. `road_id` values are unique.
5. `length_km` is present and positive (or can be derived).
6. One-way flags are counted (not treated as an error).
7. Weakly connected components are counted. More than one component is a
   warning: queries that snap onto different islands return `NO_ROUTE_FOUND`.

The committed fixture is designed so validation **passes** with a warning for
two components (`seg-isolated` is intentional).

## Full extract (~239,150 segments)

The GeoPackage is gitignored. When it is on disk:

```powershell
$env:ROUTING_DATA_PATH = "ml/data/final/roads/roads_final.gpkg"
python -m routing validate
```

Existing `ml/scripts/validate_roads.py` remains the processor-side structural
check. This module does not rewrite those scripts.

Known follow-ups on the full file (not blockers for fixture integration):

- Confirm `make_valid()` did not drop needed through-routes.
- Inspect the largest connected component vs small service islands.
- Join slope from terrain later; until then `slope_deg` may be null.

## Interface sign-off (Day 1)

Agreed with the sprint API plan:

```python
find_routes(origin: {lat, lng}, destination: {lat, lng}, vehicle_type: str)
    -> list[{route_id, distance_km, duration_min, geometry, segment_ids}]

get_segments(segment_ids: list[str])
    -> list[{segment_id, length_km, road_class, road_type, slope_deg,
             is_oneway, coordinates, surface}]
```

`vehicle_type` is `truck` | `van` | `car`. It changes duration, not topology.
Risk-weighted costs are out of scope for the sprint.
