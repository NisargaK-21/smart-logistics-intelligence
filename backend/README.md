# Smart Logistics Intelligence Backend

**Owner:** Person 3 — Backend  
**Framework:** FastAPI  
**API prefix:** `/api/v1`  
**Status:** Backend tests pass locally (29/29 passing); see [Known limitations](#known-limitations).

The backend validates route-planning requests, connects the routing and risk modules, aggregates segment scores into route scores, and exposes the API to the frontend. It also provides prototype endpoints for health, coverage, vehicle simulation, field reports, alerts, and dashboard summaries.

---

## Contents

- [Setup and startup](#setup-and-startup)
- [Configuration](#configuration)
- [Sprint API](#sprint-api)
- [Route planning behavior](#route-planning-behavior)
- [Errors](#errors)
- [Extended prototype APIs](#extended-prototype-apis)
- [Tests and fixtures](#tests-and-fixtures)
- [Project documentation](#project-documentation)
- [Known limitations](#known-limitations)

---

## Setup and startup

### Requirements

- **Python:** 3.11 or newer (tested on Python 3.13)
- **Backend dependencies:** from `backend/requirements.txt`
- **Routing graph:** Uses the committed Guwahati–Shillong fixture road network by default. For full road-network mode, see the GIS dependencies described in `routing/README.md`.

### Install dependencies

From the repository root:

```bash
python -m pip install -r backend/requirements.txt
```

### Run the development server

Launch the Uvicorn ASGI server from the repository root:

```bash
# From repository root:
python -m uvicorn backend.app.main:app --reload --port 8000
```

Alternatively, from the `backend/` directory:

```bash
# From backend/ directory:
uvicorn app.main:app --reload --port 8000
```

The interactive documentation will be accessible at:
- **Swagger UI:** [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **ReDoc:** [http://localhost:8000/api/v1/redoc](http://localhost:8000/api/v1/redoc)
- **OpenAPI Schema:** [http://localhost:8000/api/v1/openapi.json](http://localhost:8000/api/v1/openapi.json)

### Docker container

To build and run the backend container, execute from the repository root (to ensure both `backend` and `routing` packages are bundled in the build context):

```bash
docker build -t smart-logistics-backend -f backend/Dockerfile .
docker run -p 8000:8000 smart-logistics-backend
```

---

## Configuration

The backend reads settings from the environment or `.env` file:

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `API_V1_STR` | `/api/v1` | Base prefix for version 1 endpoints |
| `PROJECT_NAME` | `Smart Logistics Intelligence API` | OpenAPI application title |
| `VERSION` | `1.0.0` | API version string |
| `RISK_SOURCE` | `baseline` | Request model scoring (`model`); reports `baseline` until Person 2's trained-model adapter is available |
| `GIS_SERVICE_ENABLED` | `true` | Toggle to simulate GIS module health/outage |
| `RISK_SERVICE_ENABLED` | `true` | Toggle to simulate Risk module health/outage |
| `WEATHER_AVAILABLE` | `true` | Toggle to simulate weather outage and test graceful partial scoring |

---

## Sprint API

The backend exposes three core endpoints defined in the Sprint API contract:

### 1. `POST /api/v1/routes/plan`
Plans 1–3 candidate routes between origin and destination coordinates, scores each road segment using the Risk module, aggregates route-level scores, and ranks candidate routes with a recommended route.

- **Request Body:**
  ```json
  {
    "origin": { "lat": 26.1445, "lng": 91.7362 },
    "destination": { "lat": 25.5788, "lng": 91.8933 },
    "vehicle_type": "truck",
    "departure_time": "2026-10-28T10:00:00+05:30"
  }
  ```
- **Response (200 OK):**
  - `recommended_route_id`: ID of the top recommended route.
  - `risk_source`: `"baseline"` or `"model"`.
  - `generated_at`: ISO 8601 timestamp with offset.
  - `routes`: Array of route candidates containing `distance_km`, `estimated_duration_minutes`, `risk_score` (0–100), `risk_level` (`"low"`, `"medium"`, `"high"`), GeoJSON `geometry`, detailed `segments` with individual scores, consolidated `risk_factors`, and `data_quality`.

### 2. `GET /api/v1/health`
Operational readiness probe for backend orchestrator and its internal module dependencies.
- **Success (200 OK):** Returned when `gis` and `risk` are `"ok"` (note that `weather` may be `"degraded"` while still returning 200).
  ```json
  {
    "status": "ok",
    "modules": {
      "gis": "ok",
      "risk": "ok",
      "weather": "ok"
    }
  }
  ```
- **Failure (503 Service Unavailable):** Returned if either `gis` or `risk` is down.

### 3. `GET /api/v1/meta/coverage`
Returns the active study-area bounding box (`[minLng, minLat, maxLng, maxLat]`) and supported vehicle types (`["truck", "van", "car"]`) read dynamically from Person 1's routing graph.

---

## Route planning behavior

1. **Validation & Snapping:**
   - Validates latitude $\in [-90, 90]$ and longitude $\in [-180, 180]$.
   - Validates that origin and destination differ. Identical points immediately return `400 INVALID_REQUEST` before graph queries.
   - Requires `departure_time` to include an ISO 8601 UTC timezone offset when provided.
   - Enforces coverage bounding box check $\rightarrow$ `422 OUT_OF_COVERAGE`.
2. **Orchestration Flow:**
   - Queries `find_routes` from Person 1's `routing` module.
   - Collects unique segment IDs and retrieves road attributes via `get_segments`.
   - Sends segment data and context to Person 2's Risk module.
3. **Route Risk Aggregation Formula:**
   Segment risk scores are aggregated into a single route risk score using the weighted formula:
   $$\text{weighted\_mean} = \frac{\sum_{i=1}^n (\text{length}_i \times \text{risk\_score}_i)}{\sum_{i=1}^n \text{length}_i}$$
   $$\text{route\_risk\_score} = \text{round}(0.7 \times \text{weighted\_mean} + 0.3 \times \max_{i} (\text{risk\_score}_i))$$
4. **Risk Categorization:**
   - **Low Risk:** 0 – 33
   - **Medium Risk:** 34 – 66
   - **High Risk:** 67 – 100
5. **Ranking & Recommendation:**
   - Routes are sorted by `risk_score` ascending (safest route first).
   - Ties are broken by `distance_km` ascending, then `estimated_duration_minutes` ascending.
   - The top route becomes `recommended_route_id`.
6. **Graceful Degradation & Missing Data:**
   - Missing data is never treated as safe (0 risk).
   - If weather data is unavailable, the backend scores using terrain and road factors, sets `data_quality = "partial"`, and appends the `weather_unavailable` risk factor (`contribution: 0`).
   - If slope data is missing, `terrain_unavailable` is attached and `data_quality` is flagged `partial`.
   - If `RISK_SOURCE=model` is selected but the trained model adapter is unavailable or errors, the backend automatically falls back to baseline rules with `risk_source="baseline"`.

---

## Errors

All error responses strictly follow the unified contract schema:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable summary of the error.",
    "details": {}
  }
}
```

### Standard Error Mapping

| HTTP Status | Error Code (`code`) | Trigger Condition | Example Details |
| :--- | :--- | :--- | :--- |
| `400 Bad Request` | `INVALID_REQUEST` | Missing fields, coordinate bounds violations, identical origin/destination, invalid vehicle type. | `{"field": "destination"}` |
| `404 Not Found` | `NO_ROUTE_FOUND` | Points snapped to network but no traversable path connects them. | `{"origin_snapped": true, "destination_snapped": true}` |
| `422 Unprocessable` | `OUT_OF_COVERAGE` | Point lies outside active routing graph bounding box. | `{"point": "origin", "coverage_bbox": [...]}` |
| `503 Service Unavailable` | `DEPENDENCY_UNAVAILABLE` | GIS or Risk module is down, unhealthy, or unreachable. | `{"module": "gis"}` or `{"module": "risk"}` |
| `500 Internal Error` | `INTERNAL_ERROR` | Unexpected unhandled server exception. | `{"error_type": "RuntimeError"}` |

---

## Extended prototype APIs

In addition to core sprint endpoints, the backend provides prototype services for real-time fleet operations and field incident management:

1. **`WebSocket /ws/vehicles`**  
   Streams real-time simulated vehicle positions (`{vehicle_id, lat, lng, speed_kmh, heading_deg, ts}`).
2. **`POST /api/v1/vehicles/simulate` & `GET /api/v1/vehicles/active`**  
   Initiate simulated trips along planned routes and retrieve active vehicle coordinates.
3. **`POST /api/v1/reports` & `GET /api/v1/reports`**  
   Submit and query geo-tagged field incident reports (mudslides, waterlogging, accidents) with category and severity filters.
4. **`GET /api/v1/alerts` & `POST /api/v1/alerts/subscribe`**  
   Query proximity/hazard alerts and register subscriptions for automated notifications.
5. **`GET /api/v1/dashboard/summary`**  
   Provides operational dashboard KPIs (active alerts, recent reports, vehicle counts, route summaries, and dynamic system status).

---

## Tests and fixtures

### Running the test suite

Run all unit and integration tests with verbose reporting:

```bash
# From repository root:
python -m pytest backend/tests -v
```

### Test coverage (29 passed tests)

The test suite validates:
- Valid route planning request, ranking, and structure (`test_plan_routes_success`, `test_plan_routes_valid_contract_query`)
- Exact aggregation formula $0.7 \times \text{weighted\_mean} + 0.3 \times \text{worst\_segment}$ (`test_route_score_aggregation_formula`)
- Input validation: same origin/destination, coordinate range, invalid vehicle type, missing fields, timezone offset requirement (`test_validation_error_*`)
- Geographic bounding box coverage validation $\rightarrow$ `422 OUT_OF_COVERAGE` (`test_out_of_coverage_422`, `test_get_coverage_metadata`)
- Disconnected graph node $\rightarrow$ `404 NO_ROUTE_FOUND` (`test_no_connected_route_404`)
- Core module dependency failures $\rightarrow$ `503 DEPENDENCY_UNAVAILABLE` (`test_gis_dependency_down_503`, `test_risk_dependency_down_503`)
- Weather and terrain degradation fallbacks with `partial` data quality (`test_weather_unavailable_partial_data_quality`, `test_missing_terrain_data_is_partial_not_silently_safe`)
- Dynamic recommendation change under simulated heavy rain (`test_heavy_rain_can_change_recommended_route`)
- Graceful `RISK_SOURCE` fallback (`test_model_source_switch`)
- OpenAPI schema declarations for all error responses (`test_route_plan_openapi_declares_error_responses`)
- Unhandled exception trapping into standard error envelope (`test_unhandled_exception_uses_contract_error_shape`)
- Verification against published mock JSON fixtures (`test_published_mock_responses_match_contract`)
- Health status checks (200 OK, 503 down, weather degraded) (`test_health_*`)
- Extended endpoints and WebSocket streaming (`test_vehicles_*`, `test_field_reports_*`, `test_alerts_*`, `test_dashboard_summary`, `test_websocket_vehicles_streaming`)

### Fixture library

Published contract fixtures are maintained in `backend/tests/fixtures/`:
- `route-success.json`: Reference 200 OK multi-route plan response.
- `route-partial.json`: Reference response under weather data degradation.
- `error-no-route.json`: Reference 404 NO_ROUTE_FOUND error payload.

---

## Project documentation

- **API Reference & Contract:** [`docs/api-contract.md`](../docs/api-contract.md)
- **System Architecture & Data Flow:** [`docs/architecture.md`](../docs/architecture.md)
- **GIS & Routing Module (Person 1):** [`routing/README.md`](../routing/README.md)
- **ML & Risk Module (Person 2):** [`ml/README.md`](../ml/README.md)
- **Frontend Web Application (Person 4):** [`frontend/README.md`](../frontend/README.md)

---

## Known limitations

1. **Trained ML Model Adapter (Person 2):**
   - The backend currently scores routes using the baseline rules engine and automatically reports `risk_source="baseline"`.
   - When Person 2 delivers the trained model adapter/pipeline, the backend is architecturally wired to execute it when `RISK_SOURCE=model`.
2. **Road Network Modes (Person 1):**
   - The default development and test environment uses the committed Guwahati–Shillong fixture network.
   - Running the full Northeast OSM road network requires the external GeoPackage and optional GIS dependencies (`geopandas`, `shapely`) with `ROUTING_USE_FULL=1`.
3. **Prototype In-Memory Storage:**
   - Extended prototype endpoints (vehicle simulations, field incident reports, and alert subscriptions) store state in-memory within singleton service instances. Data resets upon server restart.
4. **Static Route Re-routing:**
   - The Sprint MVP evaluates risk over candidate routes provided by the GIS routing engine. Dynamically adjusting GIS graph edge weights based on real-time risk before pathfinding is scheduled for post-sprint milestones.
