import test from "node:test";
import assert from "node:assert";
import {
  planRoutes,
  getHealth,
  getCoverage,
  getDashboardSummary,
  ApiError,
} from "../lib/api.ts";

test("API Client: returns successful mock multi-route recommendation", async () => {
  const req = {
    origin: { lat: 26.1445, lng: 91.7362 },
    destination: { lat: 26.1801, lng: 91.7001 },
    vehicle_type: "truck" as const,
  };

  const res = await planRoutes(req, { mock: true, scenario: "success" });
  assert.strictEqual(res.recommended_route_id, "route-2");
  assert.strictEqual(res.risk_source, "baseline");
  assert.strictEqual(res.routes.length, 2);
  assert.strictEqual(res.routes[0].data_quality, "complete");
});

test("API Client: handles partial weather fallback scenario", async () => {
  const req = {
    origin: { lat: 26.1445, lng: 91.7362 },
    destination: { lat: 26.1801, lng: 91.7001 },
    vehicle_type: "truck" as const,
  };

  const res = await planRoutes(req, { mock: true, scenario: "partial_weather" });
  assert.strictEqual(res.routes[0].data_quality, "partial");
  const weatherFactor = res.routes[0].risk_factors.find(
    (f) => f.name === "weather_unavailable"
  );
  assert.ok(weatherFactor);
  assert.strictEqual(weatherFactor?.contribution, 0);
});

test("API Client: translates 404 NO_ROUTE_FOUND correctly", async () => {
  const req = {
    origin: { lat: 26.1445, lng: 91.7362 },
    destination: { lat: 26.1801, lng: 91.7001 },
    vehicle_type: "truck" as const,
  };

  await assert.rejects(
    async () => {
      await planRoutes(req, { mock: true, scenario: "no_route" });
    },
    (err: unknown) => {
      assert.ok(err instanceof ApiError);
      assert.strictEqual(err.code, "NO_ROUTE_FOUND");
      assert.strictEqual(err.status, 404);
      return true;
    }
  );
});

test("API Client: translates 422 OUT_OF_COVERAGE correctly", async () => {
  const req = {
    origin: { lat: 88.5, lng: 24.1 },
    destination: { lat: 26.1801, lng: 91.7001 },
    vehicle_type: "truck" as const,
  };

  await assert.rejects(
    async () => {
      await planRoutes(req, { mock: true, scenario: "out_of_coverage" });
    },
    (err: unknown) => {
      assert.ok(err instanceof ApiError);
      assert.strictEqual(err.code, "OUT_OF_COVERAGE");
      assert.strictEqual(err.status, 422);
      return true;
    }
  );
});

test("API Client: translates 503 DEPENDENCY_UNAVAILABLE correctly", async () => {
  const req = {
    origin: { lat: 26.1445, lng: 91.7362 },
    destination: { lat: 26.1801, lng: 91.7001 },
    vehicle_type: "truck" as const,
  };

  await assert.rejects(
    async () => {
      await planRoutes(req, { mock: true, scenario: "dependency_error" });
    },
    (err: unknown) => {
      assert.ok(err instanceof ApiError);
      assert.strictEqual(err.code, "DEPENDENCY_UNAVAILABLE");
      assert.strictEqual(err.status, 503);
      return true;
    }
  );
});

test("API Client: retrieves health check status in mock mode", async () => {
  const health = await getHealth({ mock: true });
  assert.strictEqual(health.status, "ok");
  assert.strictEqual(health.modules.gis, "ok");
  assert.strictEqual(health.modules.risk, "ok");
  assert.strictEqual(health.modules.weather, "degraded");
});

test("API Client: retrieves coverage metadata in mock mode", async () => {
  const coverage = await getCoverage({ mock: true });
  assert.strictEqual(coverage.bbox.length, 4);
  assert.ok(coverage.vehicle_types.includes("truck"));
});

test("API Client: retrieves dashboard summary metrics in mock mode", async () => {
  const summary = await getDashboardSummary({ mock: true });
  assert.ok(summary.active_alerts_count >= 0);
  assert.ok(summary.active_vehicles_count >= 0);
  assert.strictEqual(summary.overall_system_status, "operational");
});
