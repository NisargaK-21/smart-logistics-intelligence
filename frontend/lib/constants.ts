/**
 * Constants and utility mappings for Smart Logistics Intelligence.
 * Strictly adheres to docs/api-contract.md.
 */

import type { RiskLevel } from "./types.ts";

/**
 * Risk Thresholds per API contract:
 * Low: 0–33
 * Medium: 34–66
 * High: 67–100
 */
export const RISK_THRESHOLDS = {
  LOW_MAX: 33,
  MEDIUM_MAX: 66,
  HIGH_MAX: 100,
} as const;

export const RISK_LEVEL_CONFIG: Record<
  RiskLevel,
  {
    label: string;
    badgeBg: string;
    badgeText: string;
    badgeBorder: string;
    colorHex: string;
    rangeText: string;
    description: string;
  }
> = {
  low: {
    label: "Low Risk",
    badgeBg: "bg-emerald-50 dark:bg-emerald-950/40",
    badgeText: "text-emerald-700 dark:text-emerald-300",
    badgeBorder: "border-emerald-200 dark:border-emerald-800",
    colorHex: "#10b981",
    rangeText: "0 – 33",
    description: "Standard road conditions; low hazard exposure",
  },
  medium: {
    label: "Medium Risk",
    badgeBg: "bg-amber-50 dark:bg-amber-950/40",
    badgeText: "text-amber-700 dark:text-amber-300",
    badgeBorder: "border-amber-200 dark:border-amber-800",
    colorHex: "#f59e0b",
    rangeText: "34 – 66",
    description: "Moderate hazard; increased vigilance required",
  },
  high: {
    label: "High Risk",
    badgeBg: "bg-rose-50 dark:bg-rose-950/40",
    badgeText: "text-rose-700 dark:text-rose-300",
    badgeBorder: "border-rose-200 dark:border-rose-800",
    colorHex: "#ef4444",
    rangeText: "67 – 100",
    description: "Severe hazard; alternative routing recommended",
  },
};

/**
 * Maps a numeric risk score (0-100) to its category level
 */
export function getRiskLevel(score: number): RiskLevel {
  const rounded = Math.round(score);
  if (rounded <= RISK_THRESHOLDS.LOW_MAX) return "low";
  if (rounded <= RISK_THRESHOLDS.MEDIUM_MAX) return "medium";
  return "high";
}

/**
 * Returns hex color code for a given risk score
 */
export function getRiskColor(score: number): string {
  const level = getRiskLevel(score);
  return RISK_LEVEL_CONFIG[level].colorHex;
}

/**
 * Default bounding box (Guwahati–Shillong study corridor) fallback
 * [minLng, minLat, maxLng, maxLat]
 */
export const DEFAULT_CORRIDOR_BBOX: [number, number, number, number] = [
  91.6895, 26.13, 91.9205, 26.31,
];

/**
 * Default map center [lng, lat]
 */
export const DEFAULT_MAP_CENTER: [number, number] = [91.7362, 26.1445];

/**
 * OpenStreetMap Tile Layer URL and Mandatory Legal Attribution
 */
export const OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
export const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors';

/**
 * Supported vehicle types per docs/api-contract.md
 */
export const VEHICLE_OPTIONS = [
  { id: "truck", label: "Commercial Truck", icon: "🚚", speed: "40-60 km/h" },
  { id: "van", label: "Delivery Van", icon: "🚐", speed: "50-70 km/h" },
  { id: "car", label: "Emergency / Utility Car", icon: "🚗", speed: "60-80 km/h" },
] as const;

/**
 * Standard backend error code descriptions
 */
export const ERROR_MESSAGES: Record<string, string> = {
  INVALID_REQUEST: "Invalid input parameters. Please check coordinates and vehicle type.",
  NO_ROUTE_FOUND: "No connected road path found between the origin and destination points.",
  OUT_OF_COVERAGE: "Selected coordinates lie outside the active Northeast road study area.",
  DEPENDENCY_UNAVAILABLE: "Required service dependency (GIS or Risk module) is currently unavailable.",
  INTERNAL_ERROR: "An internal server error occurred while calculating routes.",
};
