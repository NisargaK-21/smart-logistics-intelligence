# NER-ResQ: Smart Logistics & Accessibility Intelligence Frontend

**Role:** Person 4 — Frontend Developer  
**Framework:** Next.js 16 (App Router), React 19, Tailwind CSS v4  
**Mapping Engine:** MapLibre GL 6.11 with OpenStreetMap Raster Tiles  
**Validation & Types:** TypeScript 5, Zod 4  
**Testing:** Node.js 22 Native Test Runner (`node:test`, `node:assert`)  
**Status:** All 20 frontend unit & contract tests passing; production build verified.

---

## 1. Overview & Architectural Role

The frontend dashboard serves as the operational intelligence center for the **NER-ResQ Smart Logistics Platform**. It visualizes logistics corridors in the Northeast Region of India (specifically the Guwahati–Shillong study corridor), evaluates multi-segment hazard risks, provides explainable contributing risk factors, and renders alternative route candidates with clear recommended routing.

All communication follows the strict contract defined in [`docs/api-contract.md`](../docs/api-contract.md).

```
                      USER / DISPATCHER
                             │
                  [Interactive Next.js UI]
        ┌────────────────────┼────────────────────┐
        │                    │                    │
 [Route Planning Form]  [OpenStreetMap]  [Results & Explainability]
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                    [API Client / Mock]
                             │
              POST /api/v1/routes/plan
              GET  /api/v1/health
              GET  /api/v1/meta/coverage
              GET  /api/v1/dashboard/summary
                             │
                    BACKEND ORCHESTRATOR
```

---

## 2. Key Capabilities & Implementation Details

### 2.1. Interactive OpenStreetMap Visualisation (`components/MapView.tsx`)
- **Map Engine:** MapLibre GL rendering OpenStreetMap raster tiles (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`).
- **Legal Compliance:** Complies with OpenStreetMap tile usage policies with mandatory attribution:  
  `© OpenStreetMap contributors`.
- **Dynamic Bounding Box:** Bounded to the active study area retrieved from `/api/v1/meta/coverage` (Guwahati–Shillong corridor `[91.6895, 26.13, 91.9205, 26.31]`).
- **Segment-Level Risk Colouring:**
  - **Low Risk (0–33):** `#10b981` (Emerald Green)
  - **Medium Risk (34–66):** `#f59e0b` (Amber Orange)
  - **High Risk (67–100):** `#ef4444` (Vivid Red)
- **Multi-Route Contrast:** The recommended route (`recommended_route_id`) is prominently emphasized with a bright casing glow and wider polyline; candidate alternatives are displayed with distinct styling.
- **Segment Hover & Click Popups:** Shows Route ID, Segment ID, Risk Score, and Hazard Factor summary.
- **Interactive Pin Placement:** Click-to-set origin and destination pins directly on the road corridor.
- **Viewport Controls:** One-click "Fit Route" and "Reset Corridor" actions.

### 2.2. Route Planning & Parameter Selection (`components/RouteForm.tsx`)
- Numeric inputs for Origin `{lat, lng}` and Destination `{lat, lng}`.
- "Pick on Map" mode allowing dispatchers to select points interactively.
- Vehicle selection supporting commercial class constraints: `"truck"`, `"van"`, `"car"`.
- Optional departure timestamp picker (ISO 8601 with timezone offset).
- Client-side validation prevents invalid submissions:
  - Enforces origin $\ne$ destination.
  - Verifies latitude in $[-90, 90]$ and longitude in $[-180, 180]$.
  - Warns if points fall outside the active corridor bounding box.

### 2.3. Explainability & Recommendation Display (`components/RouteDetails.tsx`, `components/RouteCard.tsx`)
- **Honest Risk Source Labeling:** Accurately identifies `risk_source`:
  - `baseline`: Labeled as **Deterministic Rules Baseline** (heuristic risk calculation based on road class, terrain slope, rainfall hazard thresholds, and historical disruptions). Never labeled as an unverified "AI black-box prediction".
  - `model`: Labeled as **Experimental Risk Classifier**.
- **Raw Contribution Units:** In strict adherence to the project contract, contributing risk factors are displayed as **raw score points** (e.g., `+30 pts`, `+22 pts`), NOT deceptive percentages.
- **Data Quality Indicator:** Badges indicate whether data is `complete`, `partial` (e.g. weather data unavailable fallback), `stale`, or `unavailable`.
- **Segment Inspection:** Collapsible table detailing individual road segments, lengths, and hazard scores.

### 2.4. System Health & Operational Telemetry (`components/SystemHealthBadge.tsx`, `components/DashboardMetrics.tsx`)
- System health badge with live polling of `/api/v1/health`.
- Status indicators: **Operational** (Green), **Degraded** (Amber, e.g. weather fallback), **Service Impaired** (Red).
- Detailed module health breakdown for GIS, Risk, and Weather dependencies.
- **Weather Status Disclosure:** Distinguishes configured/simulated weather feeds from live official radar telemetry.
- Regional dashboard overview displaying active hazard alerts, high-risk zones, active fleet vehicles, and on-ground field reports.

### 2.5. Mock Mode & Contract Scenario Testing
A toggle in the header enables offline mock mode backed by the exact fixtures from `backend/tests/fixtures/`:
1. **Multi-Route Success:** 2 route candidates, Route 2 recommended with lower risk.
2. **Partial Weather Fallback:** Degraded weather feed, `data_quality: "partial"`, `weather_unavailable` risk factor.
3. **404 No Connected Route:** `NO_ROUTE_FOUND` error shape.
4. **422 Out of Coverage Area:** `OUT_OF_COVERAGE` error shape.
5. **503 Dependency Unavailable:** `DEPENDENCY_UNAVAILABLE` error shape.

---

## 3. Directory Structure

```
frontend/
├── app/
│   ├── favicon.ico
│   ├── globals.css                # Tailwind CSS v4 + MapLibre styles
│   ├── layout.tsx                 # Root layout with Geist font & metadata
│   └── page.tsx                   # Main Dashboard page (responsive 2-column layout)
├── components/
│   ├── Header.tsx                 # Top bar, Live/Mock switcher, Scenario selector
│   ├── MapView.tsx                # Dynamic MapLibre GL map with OSM tiles & risk polylines
│   ├── RouteForm.tsx              # Coordinate inputs, map picking, vehicle selection
│   ├── RouteCard.tsx              # Candidate route summary with recommendation badge
│   ├── RouteDetails.tsx           # Risk source disclosure, raw points & segment list
│   ├── SystemHealthBadge.tsx      # System health badge with dependency popover
│   ├── DashboardMetrics.tsx       # Regional telemetry summary cards
│   └── ErrorBanner.tsx            # Global error banner translating API error codes
├── lib/
│   ├── api.ts                     # Robust API client with timeout & mock fallback
│   ├── types.ts                   # Strict TypeScript interfaces matching docs/api-contract.md
│   ├── validation.ts              # Zod validation schemas for requests & responses
│   ├── constants.ts               # Risk thresholds (0-33, 34-66, 67-100), OSM tile URLs
│   └── mockData.ts                # Contract-accurate mock fixtures
├── tests/
│   ├── validation.test.ts         # Zod validator & bounding box tests
│   ├── risk-scoring.test.ts       # Risk score thresholds & raw contribution tests
│   └── api.test.ts                # API client & mock scenario tests
├── README.md                      # Comprehensive frontend documentation
├── package.json
└── next.config.ts
```

---

## 4. Getting Started

### 4.1. Prerequisites
- **Node.js:** v20 or newer (tested on Node v22.18)
- **npm:** v10 or newer

### 4.2. Installation
From the repository root or `frontend/` directory:

```bash
cd frontend
npm install
```

### 4.3. Environment Configuration
Create a `.env.local` file inside `frontend/` if connecting to a custom backend host:

```env
# Optional: Defaults to http://localhost:8000/api/v1
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

### 4.4. Running the Development Server
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 5. Verification & Quality Assurance Commands

Run the following commands to verify code quality and production readiness:

```bash
# 1. Code Linting (ESLint 9)
npm run lint

# 2. TypeScript Static Typecheck
npm run typecheck

# 3. Unit & Contract Test Suite (Node.js 22 Test Runner)
npm test

# 4. Production Build (Next.js 16 Turbopack)
npm run build
```

---

## 6. Honest Disclosures & Known Limitations

1. **Weather Telemetry:** Weather inputs use free-tier APIs or configured fallback fixtures. They are explicitly marked as "Configured / Simulated Weather" and should not be treated as certified real-time aviation/radar observations.
2. **Risk Model Baseline:** Route planning uses the deterministic rules baseline by default. Scores represent heuristic vulnerability indices combining road classification, slope, rainfall thresholds, and historical landslide data, not uncalibrated black-box probabilities.
3. **Road Network Coverage:** The current sprint operates on the verified Guwahati–Shillong corridor fixture network (`[91.6895, 26.13, 91.9205, 26.31]`). Points snapped outside this bounding box return HTTP 422 `OUT_OF_COVERAGE`.
