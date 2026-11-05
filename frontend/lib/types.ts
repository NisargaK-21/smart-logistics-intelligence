/**
 * TypeScript Type Definitions for Smart Logistics Intelligence Platform (NER-ResQ)
 * Strictly follows docs/api-contract.md conventions and schemas.
 */

export interface Coordinates {
  lat: number;
  lng: number;
}

export type VehicleType = "truck" | "van" | "car";

export interface RoutePlanRequest {
  origin: Coordinates;
  destination: Coordinates;
  vehicle_type: VehicleType;
  departure_time?: string; // ISO 8601 string with timezone offset
}

export interface GeoJSONLineString {
  type: "LineString";
  coordinates: [number, number][]; // [longitude, latitude]
}

export interface SegmentRisk {
  segment_id: string;
  risk_score: number; // 0–100 integer, higher = riskier
  coordinates: [number, number][]; // [[lng, lat], ...]
}

export interface RiskFactor {
  name: string;
  contribution: number; // Raw contribution score (points, NOT percentage)
  detail?: string;
}

export type RiskLevel = "low" | "medium" | "high";
export type DataQuality = "complete" | "partial" | "stale" | "unavailable";
export type RiskSource = "baseline" | "model";

export interface Route {
  route_id: string;
  distance_km: number;
  estimated_duration_minutes: number;
  risk_score: number; // 0–100 integer
  risk_level: RiskLevel; // low: 0-33, medium: 34-66, high: 67-100
  geometry: GeoJSONLineString;
  segments: SegmentRisk[];
  risk_factors: RiskFactor[];
  data_quality: DataQuality;
}

export interface RoutePlanResponse {
  recommended_route_id: string;
  risk_source: RiskSource;
  generated_at: string;
  routes: Route[];
}

export interface ErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ErrorResponse {
  error: ErrorDetail;
}

export interface ModuleStatus {
  gis: string; // "ok" | "degraded" | "unavailable"
  risk: string; // "ok" | "degraded" | "unavailable"
  weather: string; // "ok" | "degraded" | "unavailable"
}

export interface HealthResponse {
  status: string; // "ok" | "degraded" | "impaired"
  modules: ModuleStatus;
}

export interface CoverageResponse {
  bbox: [number, number, number, number]; // [minLng, minLat, maxLng, maxLat]
  vehicle_types: VehicleType[];
}

export interface RouteRiskSummary {
  route_id: string;
  risk_score: number;
  risk_level: string;
  active_vehicles: number;
}

export interface DashboardSummary {
  active_alerts_count: number;
  recent_reports_count: number;
  active_vehicles_count: number;
  overall_system_status: string;
  risk_by_route: RouteRiskSummary[];
  high_risk_zones_count: number;
}

export interface Alert {
  alert_id?: string;
  id?: string;
  route_id?: string;
  severity: "low" | "medium" | "high" | "critical";
  message: string;
  category?: string;
  timestamp?: string;
  created_at?: string;
}

export type MockScenario =
  | "success"
  | "partial_weather"
  | "no_route"
  | "out_of_coverage"
  | "dependency_error";
