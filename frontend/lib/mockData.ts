/**
 * Contract-accurate mock fixtures matching backend/tests/fixtures/
 * Strictly preserves raw contribution units and honest source labeling.
 */

import type {
  Alert,
  CoverageResponse,
  DashboardSummary,
  ErrorResponse,
  FieldReport,
  HazardZone,
  HealthResponse,
  RoutePlanResponse,
  VehiclePosition,
} from "./types.ts";

export const MOCK_ROUTE_SUCCESS: RoutePlanResponse = {
  recommended_route_id: "route-2",
  generated_at: "2026-10-28T10:00:00+05:30",
  risk_source: "baseline",
  routes: [
    {
      route_id: "route-2",
      distance_km: 104.2,
      estimated_duration_minutes: 175,
      risk_score: 38,
      risk_level: "medium",
      geometry: {
        type: "LineString",
        coordinates: [
          [91.7362, 26.1445],
          [91.8, 25.98],
          [91.8933, 25.5788],
        ],
      },
      segments: [
        {
          segment_id: "s-101",
          risk_score: 22,
          coordinates: [
            [91.7362, 26.1445],
            [91.8, 25.98],
          ],
        },
        {
          segment_id: "s-102",
          risk_score: 55,
          coordinates: [
            [91.8, 25.98],
            [91.8933, 25.5788],
          ],
        },
      ],
      risk_factors: [
        { name: "moderate_rainfall", contribution: 18 },
        { name: "steep_terrain", contribution: 12 },
        { name: "past_disruptions", contribution: 8 },
      ],
      data_quality: "complete",
    },
    {
      route_id: "route-1",
      distance_km: 99.4,
      estimated_duration_minutes: 165,
      risk_score: 64,
      risk_level: "medium",
      geometry: {
        type: "LineString",
        coordinates: [
          [91.7362, 26.1445],
          [91.76, 25.9],
          [91.8933, 25.5788],
        ],
      },
      segments: [
        {
          segment_id: "s-201",
          risk_score: 48,
          coordinates: [
            [91.7362, 26.1445],
            [91.76, 25.9],
          ],
        },
        {
          segment_id: "s-202",
          risk_score: 78,
          coordinates: [
            [91.76, 25.9],
            [91.8933, 25.5788],
          ],
        },
      ],
      risk_factors: [
        { name: "heavy_rainfall", contribution: 30 },
        { name: "landslide_history", contribution: 22 },
        { name: "steep_terrain", contribution: 12 },
      ],
      data_quality: "complete",
    },
  ],
};

export const MOCK_ROUTE_PARTIAL: RoutePlanResponse = {
  recommended_route_id: "route-1",
  generated_at: "2026-10-28T10:00:00+05:30",
  risk_source: "baseline",
  routes: [
    {
      route_id: "route-1",
      distance_km: 99.4,
      estimated_duration_minutes: 165,
      risk_score: 47,
      risk_level: "medium",
      geometry: {
        type: "LineString",
        coordinates: [
          [91.7362, 26.1445],
          [91.76, 25.9],
          [91.8933, 25.5788],
        ],
      },
      segments: [
        {
          segment_id: "s-201",
          risk_score: 40,
          coordinates: [
            [91.7362, 26.1445],
            [91.76, 25.9],
          ],
        },
        {
          segment_id: "s-202",
          risk_score: 52,
          coordinates: [
            [91.76, 25.9],
            [91.8933, 25.5788],
          ],
        },
      ],
      risk_factors: [
        {
          name: "weather_unavailable",
          contribution: 0,
          detail: "Weather data could not be fetched; score uses road and history factors only.",
        },
        { name: "steep_terrain", contribution: 20 },
        { name: "landslide_history", contribution: 27 },
      ],
      data_quality: "partial",
    },
  ],
};

export const MOCK_ERROR_NO_ROUTE: ErrorResponse = {
  error: {
    code: "NO_ROUTE_FOUND",
    message: "No connected road path between the two points.",
    details: {
      origin_snapped: true,
      destination_snapped: true,
    },
  },
};

export const MOCK_ERROR_OUT_OF_COVERAGE: ErrorResponse = {
  error: {
    code: "OUT_OF_COVERAGE",
    message: "Coordinates are outside the supported study-area coverage bounding box.",
    details: {
      point: "origin",
      coordinates: [88.5, 24.1],
      coverage_bbox: [91.6895, 26.13, 91.9205, 26.31],
    },
  },
};

export const MOCK_ERROR_DEPENDENCY: ErrorResponse = {
  error: {
    code: "DEPENDENCY_UNAVAILABLE",
    message: "Required dependency service is unreachable or unhealthy.",
    details: {
      module: "gis",
    },
  },
};

export const MOCK_HEALTH: HealthResponse = {
  status: "ok",
  modules: {
    gis: "ok",
    risk: "ok",
    weather: "degraded",
  },
};

export const MOCK_COVERAGE: CoverageResponse = {
  bbox: [91.6895, 26.13, 91.9205, 26.31],
  vehicle_types: ["truck", "van", "car"],
};

export const MOCK_DASHBOARD_SUMMARY: DashboardSummary = {
  active_alerts_count: 3,
  recent_reports_count: 12,
  active_vehicles_count: 5,
  overall_system_status: "operational",
  risk_by_route: [
    {
      route_id: "route-1",
      risk_score: 64,
      risk_level: "medium",
      active_vehicles: 1,
    },
    {
      route_id: "route-2",
      risk_score: 38,
      risk_level: "medium",
      active_vehicles: 1,
    },
  ],
  high_risk_zones_count: 2,
};

export const MOCK_VEHICLES: VehiclePosition[] = [
  {
    vehicle_id: "V001",
    lat: 26.05,
    lng: 91.75,
    speed_kmh: 42.0,
    heading_deg: 175.0,
    ts: "2026-11-06T10:15:00+05:30",
    vehicle_class: "truck",
    status: "in_transit",
    assigned_route: "route-1",
    risk_status: "high",
    driver_name: "T. Gogoi",
  },
  {
    vehicle_id: "V002",
    lat: 25.82,
    lng: 91.81,
    speed_kmh: 48.0,
    heading_deg: 160.0,
    ts: "2026-11-06T10:14:30+05:30",
    vehicle_class: "van",
    status: "in_transit",
    assigned_route: "route-2",
    risk_status: "medium",
    driver_name: "R. Sangma",
  },
  {
    vehicle_id: "V003",
    lat: 26.1445,
    lng: 91.7362,
    speed_kmh: 0.0,
    heading_deg: 0.0,
    ts: "2026-11-06T10:12:00+05:30",
    vehicle_class: "car",
    status: "idle",
    assigned_route: "Unassigned",
    risk_status: "low",
    driver_name: "M. Das",
  },
  {
    vehicle_id: "V004",
    lat: 25.5788,
    lng: 91.8933,
    speed_kmh: 0.0,
    heading_deg: 90.0,
    ts: "2026-11-06T10:05:00+05:30",
    vehicle_class: "truck",
    status: "scheduled",
    assigned_route: "route-2",
    risk_status: "low",
    driver_name: "K. Syiem",
  },
];

export const MOCK_FIELD_REPORTS: FieldReport[] = [
  {
    report_id: "rep-001",
    category: "landslide",
    severity: "high",
    location: { lat: 25.9, lng: 91.76 },
    location_name: "Umsning Bypass (NH-6 KM 52)",
    description: "Mudslide across northbound lane near Umsning bypass. One lane passable with flagger.",
    photo_url: null,
    reporter_name: "Officer Sharma",
    created_at: "2026-11-06T08:30:00+05:30",
    status: "verified",
  },
  {
    report_id: "rep-002",
    category: "waterlogging",
    severity: "medium",
    location: { lat: 26.112, lng: 91.751 },
    location_name: "Byrnihat Bridge Approach",
    description: "Surface water accumulation on low-lying culvert approach. Freight trucks operating with caution.",
    photo_url: null,
    reporter_name: "Field Patrol B",
    created_at: "2026-11-06T09:15:00+05:30",
    status: "verified",
  },
  {
    report_id: "rep-003",
    category: "road_blockage",
    severity: "critical",
    location: { lat: 25.81, lng: 91.82 },
    location_name: "Nongpoh Hairpin Curve Sector",
    description: "Fallen tree blocking both lanes. Emergency road clearing crew dispatched.",
    photo_url: null,
    reporter_name: "Highway Patrol Alpha",
    created_at: "2026-11-06T09:45:00+05:30",
    status: "investigating",
  },
  {
    report_id: "rep-004",
    category: "slope",
    severity: "low",
    location: { lat: 25.65, lng: 91.88 },
    location_name: "Umiam Lake Overlook Sector",
    description: "Minor gravel spillage on shoulder. Roadway clear for commercial traffic.",
    photo_url: null,
    reporter_name: "Eng. Lyngdoh",
    created_at: "2026-11-06T10:00:00+05:30",
    status: "resolved",
  },
];

export const MOCK_ALERTS: Alert[] = [
  {
    alert_id: "alt-101",
    route_id: "route-1",
    vehicle_id: "V001",
    severity: "high",
    title: "Approaching High-Risk Landslide Zone",
    message: "Vehicle V001 is within 2.5 km of high-risk segment s-202 (Umsning sector).",
    location: { lat: 25.75, lng: 91.85 },
    distance_to_risk_km: 2.1,
    created_at: "2026-11-06T09:45:00+05:30",
  },
  {
    alert_id: "alt-102",
    route_id: "route-1",
    vehicle_id: null,
    severity: "medium",
    title: "Route Risk Elevation",
    message: "Heavy rainfall has increased route-1 aggregate risk score past threshold (64).",
    location: null,
    distance_to_risk_km: null,
    created_at: "2026-11-06T10:00:00+05:30",
  },
  {
    alert_id: "alt-103",
    route_id: "route-2",
    vehicle_id: "V002",
    severity: "high",
    title: "Monsoon Precipitation Advisory",
    message: "Precipitation rate of 18.5 mm/h recorded on NH-6 hill ascent. Maintain safe braking interval.",
    location: { lat: 25.82, lng: 91.81 },
    distance_to_risk_km: 1.4,
    created_at: "2026-11-06T10:10:00+05:30",
  },
];

export const MOCK_HAZARD_ZONES: HazardZone[] = [
  {
    id: "hzd-001",
    name: "Byrnihat Slope Failure Zone",
    category: "landslide",
    severity: "high",
    coordinates: [91.758, 26.115],
    risk_score: 78,
    corridor_km: "NH-6 KM 42",
    description: "Historical slope instability on western cut-slope triggered during sustained monsoon rainfall.",
    last_inspected: "2026-11-05 16:30",
    data_source: "GSI National Landslide Susceptibility Mapping (NLSM) Archive",
    active_status: "Active Watch",
    data_fidelity: "Historical Inventory",
    contributing_factors: [
      { factor: "Terrain Slope", value: "~14° cut-slope (DEM estimate)", impact: "High" },
      { factor: "Rainfall Threshold", value: ">25 mm/h baseline threshold", impact: "High" },
      { factor: "Lithology", value: "Weathered shale/siltstone", impact: "Medium" },
    ],
  },
  {
    id: "hzd-002",
    name: "Nongpoh Stream Culvert Catchment (Illustrative)",
    category: "heavy_rainfall",
    severity: "medium",
    coordinates: [91.88, 25.9],
    risk_score: 55,
    corridor_km: "NH-6 KM 68",
    description: "Illustrative study segment: Low-lying culvert modeled for drainage overflow when baseline rainfall rate exceeds 20 mm/hr. No live sensor installed.",
    last_inspected: "2026-11-06 07:15",
    data_source: "Illustrative Highway Drainage Model (Based on Nongpoh basin hydrology)",
    active_status: "Elevated Risk",
    data_fidelity: "Simulated Baseline Threshold",
    contributing_factors: [
      { factor: "Precipitation Baseline", value: ">20 mm/h threshold (Simulated model)", impact: "High" },
      { factor: "Culvert Geometry", value: "1.8 m² cross-section (Engineering estimate)", impact: "Medium" },
      { factor: "Surface Runoff", value: "Modeled sheetflow (Illustrative)", impact: "Medium" },
    ],
  },
  {
    id: "hzd-003",
    name: "Umsning Hillside Debris Section",
    category: "landslide",
    severity: "high",
    coordinates: [91.85, 25.75],
    risk_score: 82,
    corridor_km: "NH-6 KM 84",
    description: "Steep terrain slope with thick weathered overburden prone to debris slides during multi-day rain.",
    last_inspected: "2026-11-06 08:00",
    data_source: "Highway Geotechnical Survey & GSI Landslide Archive",
    active_status: "Active Watch",
    data_fidelity: "Historical Inventory",
    contributing_factors: [
      { factor: "Terrain Slope", value: "16.1° natural grade (DEM calculated)", impact: "High" },
      { factor: "Soil Saturation Index", value: "Estimated saturation index (Calculated proxy)", impact: "High" },
      { factor: "Road Classification", value: "NH-6 2-lane divided corridor", impact: "Low" },
    ],
  },
  {
    id: "hzd-004",
    name: "Umiam Lake Overlook Ridge (Illustrative)",
    category: "high_winds",
    severity: "medium",
    coordinates: [91.91, 25.64],
    risk_score: 48,
    corridor_km: "NH-6 KM 96",
    description: "Illustrative ridgeline profile: Exposed causeway modeled for crosswind shear (>50 km/h gusts) and dense orographic fog. No live anemometer installed.",
    last_inspected: "2026-11-06 09:20",
    data_source: "Topographic Ridgeline DEM Model & Climatology (Illustrative Profile)",
    active_status: "Elevated Risk",
    data_fidelity: "Topographic Calculation",
    contributing_factors: [
      { factor: "Modeled Wind Shear", value: "48-56 km/h gusts (Modeled estimate; no live sensor)", impact: "High" },
      { factor: "Orographic Cloud Base", value: "<120 m visibility (Seasonal climatology)", impact: "Medium" },
      { factor: "Vehicle Sensitivity", value: "High-cube box trailers & container trucks", impact: "High" },
    ],
  },
  {
    id: "hzd-005",
    name: "Barapani Gorge Inflow Catchment (Illustrative)",
    category: "severe_weather",
    severity: "high",
    coordinates: [91.895, 25.68],
    risk_score: 72,
    corridor_km: "NH-6 KM 91",
    description: "Illustrative drainage segment: Gorge convergence modeled for rapid surface runoff during extreme thunderstorm downpours (>35 mm/hr). No live radar installed.",
    last_inspected: "2026-11-06 08:45",
    data_source: "Catchment Hydrology Baseline Model (Illustrative GIS Simulation)",
    active_status: "Active Watch",
    data_fidelity: "Simulated Baseline Threshold",
    contributing_factors: [
      { factor: "Downpour Index", value: ">35 mm/h baseline threshold (Simulated trigger)", impact: "High" },
      { factor: "Catchment Area", value: "3.2 km² basin convergence (GIS delineated)", impact: "High" },
      { factor: "Surface Drainage", value: "Unpaved shoulder runoff (Estimated)", impact: "Medium" },
    ],
  },
  {
    id: "hzd-006",
    name: "Shillong Plateau Ascent Grade",
    category: "steep_slope",
    severity: "low",
    coordinates: [91.905, 25.59],
    risk_score: 28,
    corridor_km: "NH-6 KM 99",
    description: "Continuous 9.2° climbing grade; reinforced concrete retaining structures in place. Regular monitoring active.",
    last_inspected: "2026-11-04 11:00",
    data_source: "SRTM DEM 30m Digital Elevation Model Profile",
    active_status: "Monitored",
    data_fidelity: "Topographic Calculation",
    contributing_factors: [
      { factor: "Continuous Grade", value: "9.2° mean highway grade (+380 m ascent)", impact: "Low" },
      { factor: "Structural Retaining", value: "Roadside gabion retaining structure (Field noted)", impact: "Low" },
    ],
  },
];
