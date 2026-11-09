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
  alert_id: string;
  id?: string;
  route_id?: string | null;
  vehicle_id?: string | null;
  severity: "low" | "medium" | "high" | "critical";
  title: string;
  message: string;
  location?: Coordinates | null;
  distance_to_risk_km?: number | null;
  category?: string;
  timestamp?: string;
  created_at: string;
}

export interface AlertSubscribeRequest {
  email: string;
  route_id: string;
  threshold_risk_score?: number;
}

export interface AlertSubscribeResponse {
  status: string;
  subscription_id: string;
  email: string;
  route_id: string;
  threshold_risk_score: number;
  message: string;
}

export interface VehiclePosition {
  vehicle_id: string;
  lat: number;
  lng: number;
  speed_kmh: number;
  heading_deg?: number;
  ts: string;
  vehicle_class?: VehicleType;
  status?: "in_transit" | "idle" | "scheduled" | "maintenance";
  assigned_route?: string;
  risk_status?: RiskLevel;
  driver_name?: string;
}

export interface VehicleSimulateRequest {
  vehicle_id: string;
  route_id: string;
  speed_kmh?: number;
}

export interface VehicleSimulateResponse {
  status: string;
  vehicle_id: string;
  route_id: string;
  total_waypoints: number;
  message: string;
}

export interface FieldReport {
  report_id: string;
  category: "landslide" | "waterlogging" | "road_blockage" | "accident" | string;
  severity: "low" | "medium" | "high" | "critical" | string;
  location: Coordinates;
  location_name?: string;
  description: string;
  photo_url?: string | null;
  reporter_name?: string | null;
  created_at: string;
  status?: "verified" | "investigating" | "resolved";
}

export interface FieldReportCreate {
  category: string;
  severity: string;
  location: Coordinates;
  location_name?: string;
  description: string;
  photo_url?: string | null;
  reporter_name?: string;
}

export type HazardCategory =
  | "all"
  | "landslide"
  | "flash_flood"
  | "heavy_rainfall"
  | "high_winds"
  | "severe_weather"
  | "steep_slope"
  | "slope"
  | "flood"
  | "blockage";

export interface HazardContributingFactor {
  factor: string;
  value: string;
  impact: "High" | "Medium" | "Low";
}

export interface HazardZone {
  id: string;
  name: string;
  category:
    | "landslide"
    | "flash_flood"
    | "heavy_rainfall"
    | "high_winds"
    | "severe_weather"
    | "steep_slope"
    | "slope"
    | "flood"
    | "blockage";
  severity: "low" | "medium" | "high" | "critical";
  coordinates: [number, number]; // [lng, lat]
  risk_score: number;
  corridor_km: string;
  description: string;
  last_inspected: string;
  data_source: string;
  active_status: "Active Watch" | "Elevated Risk" | "Monitored";
  contributing_factors?: HazardContributingFactor[];
  data_fidelity?: "Historical Inventory" | "Topographic Calculation" | "Simulated Baseline Threshold";
}

export type MockScenario =
  | "success"
  | "partial_weather"
  | "no_route"
  | "out_of_coverage"
  | "dependency_error";
