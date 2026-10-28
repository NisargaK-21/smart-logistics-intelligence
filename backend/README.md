# Smart Logistics Intelligence: Backend Service

**Role:** Person 3 (Backend Engineer)  
**Branch:** `feature/backend-api`  
**Framework:** FastAPI, Python 3.11+ / 3.13  
**Base Path:** `/api/v1`

---

## 1. Responsibilities & Deliverables

As Person 3, the backend owns:
- **API Contract & Architecture:** [`docs/api-contract.md`](../docs/api-contract.md) and [`docs/architecture.md`](../docs/architecture.md)
- **Central API Orchestrator:** Validates requests, queries GIS candidate routes, queries Risk segment scoring, aggregates route risk using weighted math, and ranks alternatives.
- **Sprint MVP Endpoints:**
  1. `POST /api/v1/routes/plan` — Candidate routes with multi-segment risk scoring, factors, and recommendation.
  2. `GET /api/v1/health` — Status of backend, GIS, and risk modules (503 if GIS/Risk down).
  3. `GET /api/v1/meta/coverage` — Study area bounding box (`[90.0, 25.0, 93.0, 27.0]`) and supported vehicle types.
- **Extended Real-Time & Post-Sprint Features:**
  4. `WebSocket /ws/vehicles` — Real-time simulated vehicle position streaming.
  5. `POST /api/v1/vehicles/simulate` & `GET /api/v1/vehicles/active` — Vehicle route trip simulation.
  6. `POST /api/v1/reports` & `GET /api/v1/reports` — Geo-tagged field reports with incident categorization.
  7. `GET /api/v1/alerts` & `POST /api/v1/alerts/subscribe` — Proximity / threshold alerts & notifications.
  8. `GET /api/v1/dashboard/summary` — Centralized operational metrics.
- **API Tests:** Comprehensive pytest test suite covering all error codes (400, 404, 422, 503, 500), math verification, fallback degradation, and mock switching.

---

## 2. Quickstart & Local Setup

### 2.1. Prerequisites
- Python 3.11+ (tested on Python 3.13.6)
- Virtual environment (optional but recommended)

### 2.2. Installation
```bash
# From repository root
cd backend
python -m pip install -r requirements.txt
```

### 2.3. Run the Development Server
You can launch the server either from the repository root:
```bash
# From repository root:
python -m uvicorn backend.app.main:app --reload --port 8000
```
Or directly from the `backend/` directory:
```bash
# From backend/ directory:
uvicorn app.main:app --reload --port 8000
```

The interactive documentation will be accessible at:
- **Swagger UI:** [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **ReDoc:** [http://localhost:8000/api/v1/redoc](http://localhost:8000/api/v1/redoc)

---

## 3. Running the Test Suite

Run all unit and integration tests with verbose reporting:
```bash
# From repository root:
python -m pytest backend/tests -v
```

All 20 test cases will execute and validate:
- Valid planning request & route ranking
- Mathematical formula verification: $0.7 \times \text{weighted\_mean} + 0.3 \times \text{worst\_segment}$
- Input validation (missing fields, coordinate ranges, identical origin/destination) $\rightarrow$ `400 INVALID_REQUEST`
- Study area bounding box check $\rightarrow$ `422 OUT_OF_COVERAGE`
- Disconnected route path $\rightarrow$ `404 NO_ROUTE_FOUND`
- GIS dependency failure $\rightarrow$ `503 DEPENDENCY_UNAVAILABLE`
- Risk dependency failure $\rightarrow$ `503 DEPENDENCY_UNAVAILABLE`
- Weather unavailability fallback $\rightarrow$ `200 OK` with `data_quality: "partial"` & `weather_unavailable` factor
- Dynamic switch between `baseline` and trained `model` risk sources
- Vehicle simulation, field reporting, alerts, and dashboard summaries

---

## 4. Configuration & Environment Variables

The backend reads settings from the environment or `.env` file:

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `API_V1_STR` | `/api/v1` | Base prefix for version 1 endpoints |
| `PROJECT_NAME` | `Smart Logistics Intelligence API` | OpenAPI application title |
| `RISK_SOURCE` | `baseline` | Set to `model` to enable trained ML model scoring, or `baseline` for rules |
| `GIS_SERVICE_ENABLED` | `true` | Toggle to simulate GIS module status |
| `RISK_SERVICE_ENABLED` | `true` | Toggle to simulate Risk module status |
| `WEATHER_AVAILABLE` | `true` | Toggle to simulate weather outage and test graceful partial scoring |

---

## 5. Uniform Error Shape

All endpoints return errors matching the agreed contract:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable explanation",
    "details": {}
  }
}
```
Standard error codes:
- `400`: `INVALID_REQUEST`
- `404`: `NO_ROUTE_FOUND`
- `422`: `OUT_OF_COVERAGE`
- `503`: `DEPENDENCY_UNAVAILABLE`
- `500`: `INTERNAL_ERROR`
