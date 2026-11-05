/**
 * API Client for Smart Logistics Intelligence Backend
 * Connects to /api/v1 endpoints per docs/api-contract.md with full mock support.
 */

import type {
  CoverageResponse,
  DashboardSummary,
  ErrorResponse,
  HealthResponse,
  MockScenario,
  RoutePlanRequest,
  RoutePlanResponse,
} from "./types.ts";
import {
  MOCK_COVERAGE,
  MOCK_DASHBOARD_SUMMARY,
  MOCK_ERROR_DEPENDENCY,
  MOCK_ERROR_NO_ROUTE,
  MOCK_ERROR_OUT_OF_COVERAGE,
  MOCK_HEALTH,
  MOCK_ROUTE_PARTIAL,
  MOCK_ROUTE_SUCCESS,
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
