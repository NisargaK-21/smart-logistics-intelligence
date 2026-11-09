/**
 * API Client for Smart Logistics Intelligence Backend
 * Connects to /api/v1 endpoints per docs/api-contract.md with full mock support.
 */

import type {
  Alert,
  AlertSubscribeRequest,
  AlertSubscribeResponse,
  CoverageResponse,
  DashboardSummary,
  ErrorResponse,
  FieldReport,
  FieldReportCreate,
  HealthResponse,
  MockScenario,
  RoutePlanRequest,
  RoutePlanResponse,
  VehiclePosition,
  VehicleSimulateRequest,
  VehicleSimulateResponse,
} from "./types.ts";
import {
  MOCK_ALERTS,
  MOCK_COVERAGE,
  MOCK_DASHBOARD_SUMMARY,
  MOCK_ERROR_DEPENDENCY,
  MOCK_ERROR_NO_ROUTE,
  MOCK_ERROR_OUT_OF_COVERAGE,
  MOCK_FIELD_REPORTS,
  MOCK_HEALTH,
  MOCK_ROUTE_PARTIAL,
  MOCK_ROUTE_SUCCESS,
  MOCK_VEHICLES,
} from "./mockData.ts";

export class ApiError extends Error {
  code: string;
  status: number;
  details?: Record<string, unknown>;

  constructor(code: string, message: string, status: number, details?: Record<string, unknown>) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

const DEFAULT_BASE_URL = "http://localhost:8000/api/v1";

export function getApiBaseUrl(): string {
  if (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL.replace(/\/+$/, "");
  }
  return DEFAULT_BASE_URL;
}

export function getWebSocketUrl(): string {
  const base = getApiBaseUrl();
  const wsProto = base.startsWith("https") ? "wss" : "ws";
  // Replace http(s)://host:port/api/v1 with ws(s)://host:port/ws/vehicles
  const hostPart = base.replace(/^https?:\/\//, "").replace(/\/api\/v1$/, "");
  return `${wsProto}://${hostPart}/ws/vehicles`;
}

async function handleResponse<T>(res: Response): Promise<T> {
  const contentType = res.headers.get("content-type");
  const isJson = contentType && contentType.includes("application/json");

  if (!res.ok) {
    if (isJson) {
      try {
        const errorBody = (await res.json()) as ErrorResponse;
        if (errorBody && errorBody.error) {
          throw new ApiError(
            errorBody.error.code || "UNKNOWN_ERROR",
            errorBody.error.message || `Request failed with status ${res.status}`,
            res.status,
            errorBody.error.details
          );
        }
      } catch (e) {
        if (e instanceof ApiError) throw e;
      }
    }
    throw new ApiError(
      "HTTP_ERROR",
      `Server responded with HTTP ${res.status}: ${res.statusText}`,
      res.status
    );
  }

  if (!isJson) {
    throw new ApiError("INVALID_RESPONSE", "Expected JSON response from server", res.status);
  }

  return (await res.json()) as T;
}

/**
 * Plan routes with multi-segment risk scoring and AI recommendation
 */
export async function planRoutes(
  request: RoutePlanRequest,
  options?: { mock?: boolean; scenario?: MockScenario; signal?: AbortSignal }
): Promise<RoutePlanResponse> {
  if (options?.mock) {
    // Artificial latency for realistic UI testing
    await new Promise((resolve) => setTimeout(resolve, 400));

    switch (options.scenario) {
      case "partial_weather":
        return MOCK_ROUTE_PARTIAL;
      case "no_route":
        throw new ApiError(
          MOCK_ERROR_NO_ROUTE.error.code,
          MOCK_ERROR_NO_ROUTE.error.message,
          404,
          MOCK_ERROR_NO_ROUTE.error.details
        );
      case "out_of_coverage":
        throw new ApiError(
          MOCK_ERROR_OUT_OF_COVERAGE.error.code,
          MOCK_ERROR_OUT_OF_COVERAGE.error.message,
          422,
          MOCK_ERROR_OUT_OF_COVERAGE.error.details
        );
      case "dependency_error":
        throw new ApiError(
          MOCK_ERROR_DEPENDENCY.error.code,
          MOCK_ERROR_DEPENDENCY.error.message,
          503,
          MOCK_ERROR_DEPENDENCY.error.details
        );
      case "success":
      default:
        return MOCK_ROUTE_SUCCESS;
    }
  }

  const url = `${getApiBaseUrl()}/routes/plan`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(request),
    signal: options?.signal,
  });

  return handleResponse<RoutePlanResponse>(res);
}

/**
 * Fetch operational health of backend, GIS, and risk modules
 */
export async function getHealth(options?: {
  mock?: boolean;
  signal?: AbortSignal;
}): Promise<HealthResponse> {
  if (options?.mock) {
    return MOCK_HEALTH;
  }

  const url = `${getApiBaseUrl()}/health`;
  const res = await fetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
    signal: options?.signal,
  });

  return handleResponse<HealthResponse>(res);
}

/**
 * Fetch study area bounding box and supported vehicle types
 */
export async function getCoverage(options?: {
  mock?: boolean;
  signal?: AbortSignal;
}): Promise<CoverageResponse> {
  if (options?.mock) {
    return MOCK_COVERAGE;
  }

  const url = `${getApiBaseUrl()}/meta/coverage`;
  const res = await fetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
    signal: options?.signal,
  });

  return handleResponse<CoverageResponse>(res);
}

/**
 * Fetch regional dashboard summary metrics
 */
export async function getDashboardSummary(options?: {
  mock?: boolean;
  signal?: AbortSignal;
}): Promise<DashboardSummary> {
  if (options?.mock) {
    return MOCK_DASHBOARD_SUMMARY;
  }

  const url = `${getApiBaseUrl()}/dashboard/summary`;
  const res = await fetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
    signal: options?.signal,
  });

  return handleResponse<DashboardSummary>(res);
}

/**
 * Fetch active simulated or GPS vehicle positions
 */
export async function getActiveVehicles(options?: {
  mock?: boolean;
  signal?: AbortSignal;
}): Promise<VehiclePosition[]> {
  if (options?.mock) {
    return MOCK_VEHICLES;
  }

  try {
    const url = `${getApiBaseUrl()}/vehicles/active`;
    const res = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: options?.signal,
    });
    return await handleResponse<VehiclePosition[]>(res);
  } catch {
    // If backend endpoint is unavailable or returns 404, fallback to mock vehicles
    return MOCK_VEHICLES;
  }
}

/**
 * Start simulated trip along a route
 */
export async function simulateVehicle(
  request: VehicleSimulateRequest,
  options?: { mock?: boolean; signal?: AbortSignal }
): Promise<VehicleSimulateResponse> {
  if (options?.mock) {
    return {
      status: "started",
      vehicle_id: request.vehicle_id,
      route_id: request.route_id,
      total_waypoints: 15,
      message: `Simulation for ${request.vehicle_id} initiated along ${request.route_id} at ${request.speed_kmh || 45} km/h (Mock Mode).`,
    };
  }

  const url = `${getApiBaseUrl()}/vehicles/simulate`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(request),
    signal: options?.signal,
  });

  return handleResponse<VehicleSimulateResponse>(res);
}

/**
 * Fetch field incident reports
 */
export async function getFieldReports(
  filters?: { category?: string; severity?: string },
  options?: { mock?: boolean; signal?: AbortSignal }
): Promise<FieldReport[]> {
  if (options?.mock) {
    let reports = [...MOCK_FIELD_REPORTS];
    if (filters?.category) {
      reports = reports.filter(
        (r) => r.category.toLowerCase() === filters.category!.toLowerCase()
      );
    }
    if (filters?.severity) {
      reports = reports.filter(
        (r) => r.severity.toLowerCase() === filters.severity!.toLowerCase()
      );
    }
    return reports;
  }

  try {
    const params = new URLSearchParams();
    if (filters?.category) params.append("category", filters.category);
    if (filters?.severity) params.append("severity", filters.severity);

    const queryStr = params.toString() ? `?${params.toString()}` : "";
    const url = `${getApiBaseUrl()}/reports${queryStr}`;
    const res = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: options?.signal,
    });
    return await handleResponse<FieldReport[]>(res);
  } catch {
    return MOCK_FIELD_REPORTS;
  }
}

/**
 * Submit a new geo-tagged field incident report
 */
export async function createFieldReport(
  report: FieldReportCreate,
  options?: { mock?: boolean; signal?: AbortSignal }
): Promise<FieldReport> {
  if (options?.mock) {
    const newReport: FieldReport = {
      report_id: `rep-${Math.floor(100 + Math.random() * 900)}`,
      category: report.category,
      severity: report.severity,
      location: report.location,
      location_name: report.location_name || "NH-6 Monitored Sector",
      description: report.description,
      photo_url: report.photo_url || null,
      reporter_name: report.reporter_name || "Field Officer",
      created_at: new Date().toISOString(),
      status: "verified",
    };
    return newReport;
  }

  const url = `${getApiBaseUrl()}/reports`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(report),
    signal: options?.signal,
  });

  return handleResponse<FieldReport>(res);
}

/**
 * Fetch alerts with optional route filter
 */
export async function getAlerts(
  routeId?: string,
  options?: { mock?: boolean; signal?: AbortSignal }
): Promise<Alert[]> {
  if (options?.mock) {
    if (routeId) {
      return MOCK_ALERTS.filter((a) => a.route_id === routeId);
    }
    return MOCK_ALERTS;
  }

  try {
    const query = routeId ? `?route_id=${encodeURIComponent(routeId)}` : "";
    const url = `${getApiBaseUrl()}/alerts${query}`;
    const res = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: options?.signal,
    });
    return await handleResponse<Alert[]>(res);
  } catch {
    return MOCK_ALERTS;
  }
}

/**
 * Subscribe to alerts on a route
 */
export async function subscribeToAlerts(
  request: AlertSubscribeRequest,
  options?: { mock?: boolean; signal?: AbortSignal }
): Promise<AlertSubscribeResponse> {
  if (options?.mock) {
    return {
      status: "subscribed",
      subscription_id: `sub-mock-${Math.floor(1000 + Math.random() * 9000)}`,
      email: request.email,
      route_id: request.route_id,
      threshold_risk_score: request.threshold_risk_score || 65,
      message: `Subscribed ${request.email} to alerts on ${request.route_id} (Mock).`,
    };
  }

  const url = `${getApiBaseUrl()}/alerts/subscribe`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(request),
    signal: options?.signal,
  });

  return handleResponse<AlertSubscribeResponse>(res);
}

/**
 * Establish live WebSocket connection to stream simulated vehicle GPS positions
 * Returns cleanup unsubscription function
 */
export function connectVehicleWebSocket(
  onPosition: (pos: VehiclePosition) => void,
  onError?: (err: unknown) => void
): () => void {
  let ws: WebSocket | null = null;
  let isClosedManually = false;

  try {
    const wsUrl = getWebSocketUrl();
    ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as VehiclePosition;
        if (data && data.vehicle_id) {
          onPosition(data);
        }
      } catch {
        // Ignore unparseable frames
      }
    };

    ws.onerror = (e) => {
      if (!isClosedManually && onError) {
        onError(e);
      }
    };
  } catch (err) {
    if (onError) onError(err);
  }

  return () => {
    isClosedManually = true;
    if (ws) {
      ws.close();
      ws = null;
    }
  };
}
