import test from "node:test";
import assert from "node:assert";
import { getRiskColor, getRiskLevel, RISK_THRESHOLDS } from "../lib/constants.ts";
import { MOCK_ROUTE_SUCCESS } from "../lib/mockData.ts";

test("Risk score thresholds: maps 0-33 to low risk", () => {
  assert.strictEqual(getRiskLevel(0), "low");
  assert.strictEqual(getRiskLevel(22), "low");
  assert.strictEqual(getRiskLevel(RISK_THRESHOLDS.LOW_MAX), "low");
  assert.strictEqual(getRiskColor(22), "#10b981");
});

test("Risk score thresholds: maps 34-66 to medium risk", () => {
  assert.strictEqual(getRiskLevel(34), "medium");
  assert.strictEqual(getRiskLevel(50), "medium");
  assert.strictEqual(getRiskLevel(RISK_THRESHOLDS.MEDIUM_MAX), "medium");
  assert.strictEqual(getRiskColor(55), "#f59e0b");
});

test("Risk score thresholds: maps 67-100 to high risk", () => {
  assert.strictEqual(getRiskLevel(67), "high");
  assert.strictEqual(getRiskLevel(78), "high");
  assert.strictEqual(getRiskLevel(100), "high");
  assert.strictEqual(getRiskColor(78), "#ef4444");
});

test("Risk factors: contributions are raw score units, not percentages", () => {
  const route = MOCK_ROUTE_SUCCESS.routes[0];
  assert.ok(route.risk_factors.length > 0);

  route.risk_factors.forEach((factor) => {
    // Verifies raw numeric contribution
    assert.strictEqual(typeof factor.contribution, "number");
    assert.ok(factor.contribution >= 0);
  });
});

test("Risk source labeling: verifies honest baseline disclosure", () => {
  assert.strictEqual(MOCK_ROUTE_SUCCESS.risk_source, "baseline");
});
