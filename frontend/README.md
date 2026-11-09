# NER-ResQ: Smart Logistics & Accessibility Intelligence Frontend

**Role:** Frontend Platform Development & System Integration  
**Framework:** Next.js 16 (App Router), React 19, Tailwind CSS v4  
**Mapping Engine:** MapLibre GL 6.11 with OpenStreetMap Raster Tiles  
**Validation & Types:** TypeScript 5, Zod 4  
**Testing:** Node.js 22 Native Test Runner (`node:test`, `node:assert`)  
**Status:** All 20 frontend unit & contract tests passing; 0 TypeScript errors; 0 ESLint warnings/errors; production build verified.

---

## 1. Overview & Multi-Page Architecture

The frontend serves as the operational intelligence dashboard for the **NER-ResQ Smart Logistics Platform**. It visualizes logistics corridors in the Northeast Region of India (specifically the Guwahati–Shillong NH-6 study corridor), evaluates multi-segment hazard risks, provides explainable contributing risk factors, tracks fleet movements in real-time, manages field incident reports with CSV export, and renders alternative route candidates with clear recommended routing.

All communication follows the strict contract defined in [`docs/api-contract.md`](../docs/api-contract.md).

```
                      USER / DISPATCHER
                             │
                [Next.js 16 App Router UI]
  ┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
  │    /     │  /routes │/risk-zones│  /fleet  │/analytics│ /reports │ /settings
[Dashboard]  [Planning]  [Hazards]  [Telemetry] [Insights] [Incidents] [Config]
  └──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
                             │
             [AppShell: Sidebar + Header + Context]
                             │
            [API Client / Offline Mock Engine]
                             │
              POST /api/v1/routes/plan
              GET  /api/v1/health
              GET  /api/v1/meta/coverage
              GET  /api/v1/dashboard/summary
              GET  /api/v1/vehicles/active
              POST /api/v1/vehicles/simulate
              WS   /ws/vehicles
              GET  /api/v1/reports
              POST /api/v1/reports
              GET  /api/v1/alerts
              POST /api/v1/alerts/subscribe
                             │
                    BACKEND ORCHESTRATOR
```

---

## 2. Complete Application Routes

The platform is structured as a full multi-page application with 7 independent routes wrapped in a persistent shared layout (`AppShell`, `Sidebar`, `Header`):

1. **Dashboard (`/`):**
   - High-level operational overview with 4 KPI cards (Active Hazard Alerts, High Risk Zones, Active Fleet Vehicles, Field Incidents).
   - Interactive GIS overview map with risk zones and active fleet markers.
   - Corridor operational status and real-time IST clock.
   - Weather and terrain overview (elevation profile, slope gradient, rainfall hazard).
   - Recent alerts feed and field activity log.
   - Risk distribution breakdown (Low, Medium, High).

2. **Routes (`/routes`):**
   - Dedicated route planning workspace.
   - Origin/destination coordinate inputs with one-click Guwahati–Shillong corridor presets.
   - Interactive "Pick on Map" coordinate selection with visual `crosshair` cursor.
   - Vehicle class selection (`truck`, `van`, `car`) with speed and clearance constraints.
   - Multi-route candidates with prominent recommended route highlighting.
   - Segment-wise risk inspection with raw score contribution points (`+pts`).
   - Side-by-side route comparison matrix.

3. **Risk Zones (`/risk-zones`):**
   - Spatial hazard monitoring along the NH-6 corridor.
   - Filterable by severity (All, High, Medium, Low) and hazard category (Landslides, Heavy Rainfall, High Winds, Severe Weather, Steep Slopes).
   - Clear distinction between physical hazard zones and dynamic contributing risk factors.
   - Explicit data fidelity badges (Historical Inventory, Topographic Calculation, Simulated Baseline Threshold).
   - Interactive map focusing on high-vulnerability road segments and slope hazard areas.
   - Detailed hazard cards with location names, coordinates, contributing factors, and data provenance.

4. **Fleet (`/fleet`):**
   - Real-time fleet tracking and dispatch management.
   - Active vehicle telemetry (speed, heading, vehicle class, coordinates, status).
   - Real-time WebSocket connection to `/ws/vehicles` with automatic reconnection and fallback.
   - Trip dispatch simulator (`POST /api/v1/vehicles/simulate`) to test route tracking.
   - Interactive GIS tracking map with color-coded vehicle markers and info popups.

5. **Analytics (`/analytics`):**
   - Empirical logistics evaluations across road classifications and terrain gradients.
   - Historical monthly disruption chart (GSI & CWC disaster history).
   - Elevation profile chart from Guwahati (55m ASL) to Shillong (1,496m ASL).
   - Vehicle class sensitivity breakdown and weather vulnerability indices.

6. **Reports (`/reports`):**
   - Verified on-ground field incident reporting system.
   - Submission modal (`POST /api/v1/reports`) for field officers to report hazards with GPS coordinates.
   - Filterable reports table by severity and category.
   - **One-click CSV Data Export** for logistics compliance and reporting.

7. **Settings (`/settings`):**
   - Regional corridor selection and bounding box inspection.
   - Dispatch preferences (default vehicle, risk alert threshold, alert audio).
   - Alert email subscription (`POST /api/v1/alerts/subscribe`).
   - Live backend service dependency diagnostics (Backend API, GIS & Routing Engine, Risk Assessment Service, Weather Data Service).
   - Direct Live API / Mock Fixtures switcher.

---

## 3. Global Pointer & Interaction System

The application adheres to a strict, professional light theme and an accessible pointer system:
- **Consistent Pointers:** All clickable buttons, links, navigation items, interactive cards, tabs, dropdowns, and map controls enforce `cursor-pointer`.
- **Form Inputs:** Text, number, search, and date-time inputs explicitly use `cursor-text`.
- **Coordinate Picking:** The GIS map canvas dynamically switches to a `crosshair` cursor when coordinate picking is activated.
- **Disabled State:** Disabled buttons and inputs enforce `cursor: not-allowed`.
- **Keyboard Accessibility:** Clear `:focus-visible` ring using `#0284c7` (Sky-600) with 2px offset.
- **Native Cursors Only:** Standard operating-system cursors are preserved; no invasive animated cursor wrappers.

---

## 4. Key Technical Capabilities

### 4.1. MapLibre GL Integration (`components/MapView.tsx`)
- **Map Engine:** MapLibre GL rendering OpenStreetMap raster tiles with distributed mirror subdomains (`https://{a,b,c}.tile.openstreetmap.org/{z}/{x}/{y}.png`).
- **Legal Compliance:** Mandatory OpenStreetMap attribution: `© OpenStreetMap contributors`, explicitly placed via an uncrowded `AttributionControl` at `bottom-left` so it never overlaps or is obscured by legends or cards.
- **Graceful Tile Error Handling:** Intercepts raster tile AJAXErrors (403/429/offline) so transient network limits never crash the application or pollute the dev overlay; vector routing, risk zones, and fleet waypoints remain fully interactive with a user-friendly retry indicator.
- **Worker Configuration:** Preserves exact local worker path:
  ```ts
  maplibregl.setWorkerUrl("/vendor/maplibre-gl/maplibre-gl-worker.mjs");
  ```
- **Segment-Level Risk Colouring:**
  - **Low Risk (0–33):** `#10b981` (Emerald Green)
  - **Medium Risk (34–66):** `#f59e0b` (Amber Orange)
  - **High Risk (67–100):** `#ef4444` (Vivid Red)

### 4.2. Research Integrity & Explainability
- **Honest Risk Source Labeling:** Accurately identifies `risk_source`:
  - `baseline`: Labeled as **Deterministic Rules Baseline** (heuristic risk calculation based on road class, terrain slope, rainfall hazard thresholds, and historical disruptions). Never labeled as an unverified "AI black-box prediction".
  - `model`: Labeled as **Experimental Risk Classifier**.
- **Raw Contribution Units:** Contributing risk factors are displayed as **raw score points** (e.g., `+30 pts`, `+22 pts`), NOT deceptive percentages.
- **Data Quality Indicator:** Badges indicate whether data is `complete`, `partial` (e.g. weather data unavailable fallback), `stale`, or `unavailable`.

---

## 5. Teammate Deployment Handover Guide

This section is prepared for teammates taking over the frontend for staging and production deployment.

### 5.1. System Requirements & Prerequisites
- **Node.js:** v20.x or newer (recommended LTS v22.x)
- **npm:** v10.x or newer
- **Backend Service:** FastAPI backend running on port 8000 (or configured via environment variable)

### 5.2. Environment Configuration
Create a `.env.local` or `.env.production` file in `frontend/`:

```env
# URL of the backend orchestrator (default: http://localhost:8000/api/v1)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1

# Optional WebSocket URL for real-time fleet telemetry (default: ws://localhost:8000/ws/vehicles)
NEXT_PUBLIC_WS_BASE_URL=ws://localhost:8000/ws/vehicles
```

### 5.3. Local Development
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### 5.4. Production Build & Start (Node.js / PM2)
```bash
cd frontend
# Clean install dependencies
npm ci

# Build optimized production bundle
npm run build

# Start production server on port 3000
npm start
```

To run with PM2 process manager in production:
```bash
pm2 start npm --name "ner-resq-frontend" -- start -- -p 3000
```

### 5.5. Docker / Container Deployment
If deploying via Docker, use the following multi-stage build:

```dockerfile
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
```

---

## 6. Verification Commands & QA Checklist

Before merging or promoting to production, verify all automated checks pass:

```bash
cd frontend

# 1. Unit & Contract Tests (Node.js test runner)
npm test

# 2. TypeScript Typecheck (0 errors required)
npm run typecheck

# 3. ESLint Verification (0 warnings/errors required)
npm run lint

# 4. Production Build (Prerenders all 7 routes)
npm run build
```
