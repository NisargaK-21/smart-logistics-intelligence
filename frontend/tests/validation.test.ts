import test from "node:test";
import assert from "node:assert";
import {
  coordinatesSchema,
  routePlanRequestSchema,
  vehicleTypeSchema,
  isPointInBbox,
} from "../lib/validation.ts";

test("Coordinates validation: accepts valid coordinates", () => {
  const valid = { lat: 26.1445, lng: 91.7362 };
  const result = coordinatesSchema.safeParse(valid);
  assert.strictEqual(result.success, true);
});

test("Coordinates validation: rejects latitude outside [-90, 90]", () => {
  const invalid1 = { lat: 91.5, lng: 91.7362 };
  const invalid2 = { lat: -95.0, lng: 91.7362 };
  assert.strictEqual(coordinatesSchema.safeParse(invalid1).success, false);
  assert.strictEqual(coordinatesSchema.safeParse(invalid2).success, false);
});

test("Coordinates validation: rejects longitude outside [-180, 180]", () => {
  const invalid = { lat: 26.1445, lng: 185.0 };
  assert.strictEqual(coordinatesSchema.safeParse(invalid).success, false);
});

test("Vehicle class validation: only accepts truck, van, car", () => {
  assert.strictEqual(vehicleTypeSchema.safeParse("truck").success, true);
  assert.strictEqual(vehicleTypeSchema.safeParse("van").success, true);
  assert.strictEqual(vehicleTypeSchema.safeParse("car").success, true);
  assert.strictEqual(vehicleTypeSchema.safeParse("motorcycle").success, false);
  assert.strictEqual(vehicleTypeSchema.safeParse("plane").success, false);
});

test("Route plan request: rejects identical origin and destination", () => {
  const request = {
    origin: { lat: 26.1445, lng: 91.7362 },
    destination: { lat: 26.1445, lng: 91.7362 },
    vehicle_type: "truck",
  };
  const result = routePlanRequestSchema.safeParse(request);
  assert.strictEqual(result.success, false);
  if (!result.success) {
    const issue = result.error.issues[0];
    assert.strictEqual(
      issue.message,
      "Destination coordinates must differ from origin coordinates"
    );
  }
});

test("Route plan request: accepts valid distinct origin and destination", () => {
  const request = {
    origin: { lat: 26.1445, lng: 91.7362 },
    destination: { lat: 26.1801, lng: 91.7001 },
    vehicle_type: "truck",
    departure_time: "2026-10-28T10:00:00+05:30",
  };
  const result = routePlanRequestSchema.safeParse(request);
  assert.strictEqual(result.success, true);
});

test("Bounding box check: verifies points within study corridor", () => {
  const bbox: [number, number, number, number] = [91.6895, 26.13, 91.9205, 26.31];

  const inside = { lat: 26.1445, lng: 91.7362 };
  const outsideLat = { lat: 24.1, lng: 91.7362 };
  const outsideLng = { lat: 26.1445, lng: 88.5 };

  assert.strictEqual(isPointInBbox(inside, bbox), true);
  assert.strictEqual(isPointInBbox(outsideLat, bbox), false);
  assert.strictEqual(isPointInBbox(outsideLng, bbox), false);
});
