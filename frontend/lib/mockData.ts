/**
 * Contract-accurate mock fixtures matching backend/tests/fixtures/
 * Strictly preserves raw contribution units and honest source labeling.
 */

import type {
  CoverageResponse,
  DashboardSummary,
  ErrorResponse,
  HealthResponse,
  RoutePlanResponse,
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
