# Smart Logistics Intelligence: API Reference & Contract

**Version:** 1.0.0 (Sprint MVP)  
**Base Path:** `/api/v1`  
**Data Format:** JSON, UTF-8  
**Owner:** Person 3 (Backend)  

---

## 1. Conventions & Principles

| Item | Rule |
| :--- | :--- |
| **Base path** | `/api/v1`, JSON, UTF-8 |
| **Coordinates** | GeoJSON format `[longitude, latitude]`, WGS84 standard.<br>Request input points use object format: `{"lat": float, "lng": float}` |
| **Units** | Distance in **km**, duration in **minutes**, timestamps in **ISO 8601 with offset** (e.g., `2026-10-28T10:00:00+05:30`) |
| **Risk Score** | Integer between `0–100`, where higher is riskier.<br>• **Low**: 0–33<br>• **Medium**: 34–66<br>• **High**: 67–100 |
| **Route Score** | $0.7 \times (\text{length-weighted mean of segment scores}) + 0.3 \times (\text{worst segment score})$ (rounded to nearest integer) |
| **Missing Data** | Never treated as safe; flagged in `data_quality`. If weather data is unavailable, score from remaining factors, set `data_quality = "partial"`, and append `weather_unavailable` factor. If risk module is down, return HTTP 503, never a fabricated score. |

---

## 2. Global Error Shape

All endpoints return a uniform error structure across the API on failure:

```json
{
  "error": {
    "code": "ERROR_CODE_STRING",
    "message": "Human readable description of the error.",
    "details": {}
  }
}
```

### Standard HTTP Status Codes & Error Codes

| HTTP Status | Error Code (`code`) | Trigger Condition | Example Details |
| :--- | :--- | :--- | :--- |
| `400 Bad Request` | `INVALID_REQUEST` | Missing or invalid fields, origin equals destination, latitude outside `[-90, 90]`, longitude outside `[-180, 180]`, invalid vehicle type. | `{"field": "destination", "issue": "must differ from origin"}` |
| `404 Not Found` | `NO_ROUTE_FOUND` | Points snapped to road network, but no traversable path connects them. | `{"origin_snapped": true, "destination_snapped": true}` |
| `422 Unprocessable` | `OUT_OF_COVERAGE` | Point lies outside the active routing graph's study-area bounding box. | `{"point": "origin", "coverage_bbox": [minLng, minLat, maxLng, maxLat]}` |
| `503 Service Unavailable` | `DEPENDENCY_UNAVAILABLE` | GIS or Risk module is down or unreachable. | `{"module": "gis"}` or `{"module": "risk"}` |
| `500 Internal Error` | `INTERNAL_ERROR` | Unexpected unhandled server exception. | `{"error_type": "RuntimeError"}` |

For `/api/v1/routes/plan`, validation errors (including missing fields and invalid coordinates) use the `400` error shape above rather than FastAPI's default `422` response. When origin and destination are identical, that validation runs before study-area coverage checks.

---

## 3. Endpoints

### 3.1. Plan Routes with Risk Assessment

- **Method:** `POST`
- **Path:** `/api/v1/routes/plan`
- **Description:** Accepts origin, destination, vehicle type, and optional departure time. Orchestrates GIS route candidates and Risk module scoring, aggregates segment risks into route-level scores, ranks routes, and returns candidate routes with a recommended route.

#### Request Headers
```http
Content-Type: application/json
Accept: application/json
```

#### Request Body Schema
```json
{
  "origin": {
    "lat": 26.1445,
    "lng": 91.7362
  },
  "destination": {
    "lat": 25.5788,
    "lng": 91.8933
  },
  "vehicle_type": "truck",
  "departure_time": "2026-10-28T10:00:00+05:30"
}
```

| Field | Type | Required | Constraints / Notes |
| :--- | :--- | :--- | :--- |
| `origin` | `object` | Yes | Coordinates `{lat, lng}`. `lat` between -90 and 90, `lng` between -180 and 180. |
| `destination` | `object` | Yes | Coordinates `{lat, lng}`. Must differ from `origin`. |
| `vehicle_type` | `string` | Yes | Allowed values: `"truck"`, `"van"`, `"car"`. |
| `departure_time` | `string` | No | ISO 8601 format string with offset. Defaults to current timestamp (`now`). |

#### Response 200 OK Schema
```json
{
  "recommended_route_id": "route-2",
  "risk_source": "baseline",
  "generated_at": "2026-10-28T10:00:00+05:30",
  "routes": [
    {
      "route_id": "route-2",
      "distance_km": 104.2,
      "estimated_duration_minutes": 175,
      "risk_score": 38,
      "risk_level": "medium",
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [91.7362, 26.1445],
          [91.8000, 25.9800],
          [91.8933, 25.5788]
        ]
      },
      "segments": [
        {
          "segment_id": "s-101",
          "risk_score": 22,
          "coordinates": [
            [91.7362, 26.1445],
            [91.8000, 25.9800]
          ]
        },
        {
          "segment_id": "s-102",
          "risk_score": 55,
          "coordinates": [
            [91.8000, 25.9800],
            [91.8933, 25.5788]
          ]
        }
      ],
      "risk_factors": [
        { "name": "moderate_rainfall", "contribution": 18 },
        { "name": "steep_terrain", "contribution": 12 },
        { "name": "past_disruptions", "contribution": 8 }
      ],
      "data_quality": "complete"
    },
    {
      "route_id": "route-1",
      "distance_km": 99.4,
      "estimated_duration_minutes": 165,
      "risk_score": 64,
      "risk_level": "medium",
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [91.7362, 26.1445],
          [91.7600, 25.9000],
          [91.8933, 25.5788]
        ]
      },
      "segments": [
        {
          "segment_id": "s-201",
          "risk_score": 48,
          "coordinates": [
            [91.7362, 26.1445],
            [91.7600, 25.9000]
          ]
        },
        {
          "segment_id": "s-202",
          "risk_score": 78,
          "coordinates": [
            [91.7600, 25.9000],
            [91.8933, 25.5788]
          ]
        }
      ],
      "risk_factors": [
        { "name": "heavy_rainfall", "contribution": 30 },
        { "name": "landslide_history", "contribution": 22 },
        { "name": "steep_terrain", "contribution": 12 }
      ],
      "data_quality": "complete"
    }
  ]
}
```

---

### 3.2. Health Check

- **Method:** `GET`
- **Path:** `/api/v1/health`
- **Description:** Returns operational status of the backend orchestrator and internal dependencies (`gis`, `risk`, `weather`). Used by the frontend on load to display a system status badge.
- **Success Status:** `200 OK` (when backend, gis, and risk are healthy). Note: `weather` may be `"degraded"` while still returning 200.
- **Dependency Failure Status:** `503 Service Unavailable` if either `gis` or `risk` is down.

#### Response 200 OK Example
```json
{
  "status": "ok",
  "modules": {
    "gis": "ok",
    "risk": "ok",
    "weather": "degraded"
  }
}
```

#### Response 503 Dependency Unavailable Example
```json
{
  "error": {
    "code": "DEPENDENCY_UNAVAILABLE",
    "message": "Core dependency 'gis' is unavailable.",
    "details": {
      "module": "gis"
    }
  }
}
```

---

### 3.3. Metadata Coverage & Supported Vehicles

- **Method:** `GET`
- **Path:** `/api/v1/meta/coverage`
- **Description:** Provides the geographic bounding box of the active road network and the list of supported vehicle types. Values are read from Person 1's routing graph, so the fixture and full-dataset modes stay aligned. Used by the frontend map to bound interactive clicks and zoom viewports.

#### Response 200 OK Example
```json
{
  "bbox": [91.6895, 26.13, 91.9205, 26.31],
  "vehicle_types": [
    "truck",
    "van",
    "car"
  ]
}
```
*Note: `bbox` format is `[minLongitude, minLatitude, maxLongitude, maxLatitude]`.*

---

## 4. Internal Module Interfaces

The backend connects to the GIS module (Person 1) and Risk module (Person 2) using defined interfaces:

### 4.1. GIS Module Interface (Person 1)
- `find_routes(origin: dict, destination: dict, vehicle_type: str) -> list[dict]`
  - Returns 1–3 route candidate objects:
    ```python
    [
      {
        "route_id": "route-1",
        "distance_km": 99.4,
        "duration_min": 165.0,
        "geometry": {
          "type": "LineString",
          "coordinates": [[91.7362, 26.1445], [91.76, 25.90], [91.8933, 25.5788]]
        },
        "segment_ids": ["s-201", "s-202"]
      }
    ]
    ```
- `get_segments(segment_ids: list[str]) -> dict[str, dict]`
  - Returns dictionary mapping `segment_id` to its road attributes:
    ```python
    {
      "s-201": {
        "length_km": 45.2,
        "road_class": "national_highway",
        "slope": 3.2,
        "one_way": False,
        "coordinates": [[91.7362, 26.1445], [91.76, 25.90]]
      }
    }
    ```

### 4.2. Risk Module Interface (Person 2)
- `score(segments: list[dict], context: dict) -> dict[str, dict]`
  - Takes segment attributes and context (`{"vehicle_type": str, "departure_time": str}`).
  - Returns dictionary mapping `segment_id` to risk details:
    ```python
    {
      "s-201": {
        "score": 40,
        "factors": [
          {"name": "steep_terrain", "contribution": 20},
          {"name": "landslide_history", "contribution": 20}
        ],
        "data_quality": "complete"
      }
    }
    ```
- Note: Both rules baseline and trained model must adhere strictly to this identical signature. A configuration switch (`RISK_SOURCE=baseline` / `RISK_SOURCE=model`) controls backend invocation. Until a trained-model adapter is supplied, or if it fails, the backend automatically falls back to baseline with `risk_source="baseline"`.

---

## 5. Mock Response Library

Machine-readable copies of the success, partial-weather, and no-route examples are kept in `backend/tests/fixtures/` and validated against the API response schemas by the backend tests.

### 5.1. Success with Multi-Route Comparison & Recommendation
```json
{
  "recommended_route_id": "route-2",
  "risk_source": "baseline",
  "generated_at": "2026-10-28T10:00:00+05:30",
  "routes": [
    {
      "route_id": "route-2",
      "distance_km": 104.2,
      "estimated_duration_minutes": 175,
      "risk_score": 38,
      "risk_level": "medium",
      "geometry": {
        "type": "LineString",
        "coordinates": [[91.7362, 26.1445], [91.80, 25.98], [91.8933, 25.5788]]
      },
      "segments": [
        { "segment_id": "s-101", "risk_score": 22, "coordinates": [[91.7362, 26.1445], [91.80, 25.98]] },
        { "segment_id": "s-102", "risk_score": 55, "coordinates": [[91.80, 25.98], [91.8933, 25.5788]] }
      ],
      "risk_factors": [
        { "name": "moderate_rainfall", "contribution": 18 },
        { "name": "steep_terrain", "contribution": 12 },
        { "name": "past_disruptions", "contribution": 8 }
      ],
      "data_quality": "complete"
    },
    {
      "route_id": "route-1",
      "distance_km": 99.4,
      "estimated_duration_minutes": 165,
      "risk_score": 64,
      "risk_level": "medium",
      "geometry": {
        "type": "LineString",
        "coordinates": [[91.7362, 26.1445], [91.76, 25.90], [91.8933, 25.5788]]
      },
      "segments": [
        { "segment_id": "s-201", "risk_score": 48, "coordinates": [[91.7362, 26.1445], [91.76, 25.90]] },
        { "segment_id": "s-202", "risk_score": 78, "coordinates": [[91.76, 25.90], [91.8933, 25.5788]] }
      ],
      "risk_factors": [
        { "name": "heavy_rainfall", "contribution": 30 },
        { "name": "landslide_history", "contribution": 22 },
        { "name": "steep_terrain", "contribution": 12 }
      ],
      "data_quality": "complete"
    }
  ]
}
```

### 5.2. Success with Partial Weather Data Fallback
```json
{
  "recommended_route_id": "route-1",
  "risk_source": "baseline",
  "generated_at": "2026-10-28T10:00:00+05:30",
  "routes": [
    {
      "route_id": "route-1",
      "distance_km": 99.4,
      "estimated_duration_minutes": 165,
      "risk_score": 47,
      "risk_level": "medium",
      "geometry": {
        "type": "LineString",
        "coordinates": [[91.7362, 26.1445], [91.76, 25.90], [91.8933, 25.5788]]
      },
      "segments": [
        { "segment_id": "s-201", "risk_score": 40, "coordinates": [[91.7362, 26.1445], [91.76, 25.90]] },
        { "segment_id": "s-202", "risk_score": 52, "coordinates": [[91.76, 25.90], [91.8933, 25.5788]] }
      ],
      "risk_factors": [
        {
          "name": "weather_unavailable",
          "contribution": 0,
          "detail": "Weather data could not be fetched; score uses road and history factors only."
        },
        { "name": "steep_terrain", "contribution": 20 },
        { "name": "landslide_history", "contribution": 27 }
      ],
      "data_quality": "partial"
    }
  ]
}
```

### 5.3. Error: No Connected Road Path (404)
```json
{
  "error": {
    "code": "NO_ROUTE_FOUND",
    "message": "No connected road path between the two points.",
    "details": {
      "origin_snapped": true,
      "destination_snapped": true
    }
  }
}
```

### 5.4. Error: Out of Coverage Area (422)
```json
{
  "error": {
    "code": "OUT_OF_COVERAGE",
    "message": "Coordinates are outside the supported study-area coverage bounding box.",
    "details": {
      "point": "origin",
      "coordinates": [88.5, 24.1],
      "coverage_bbox": [90.0, 25.0, 93.0, 27.0]
    }
  }
}
```

### 5.5. Error: Dependency Down (503)
```json
{
  "error": {
    "code": "DEPENDENCY_UNAVAILABLE",
    "message": "Required dependency service is unreachable or unhealthy.",
    "details": {
      "module": "gis"
    }
  }
}
```

### 5.6. Error: Invalid Request (400)
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Origin and destination coordinates must be different.",
    "details": {
      "field": "destination"
    }
  }
}
```
