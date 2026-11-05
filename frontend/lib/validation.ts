/**
 * Zod validation schemas for Smart Logistics Intelligence
 * Enforces API contract constraints client-side.
 */

import { z } from "zod";

export const coordinatesSchema = z.object({
  lat: z
    .number({ message: "Latitude must be a valid number" })
    .min(-90, "Latitude must be >= -90")
    .max(90, "Latitude must be <= 90"),
  lng: z
    .number({ message: "Longitude must be a valid number" })
    .min(-180, "Longitude must be >= -180")
    .max(180, "Longitude must be <= 180"),
});

export const vehicleTypeSchema = z.enum(["truck", "van", "car"], {
  message: "Vehicle type must be 'truck', 'van', or 'car'",
});

export const routePlanRequestSchema = z
  .object({
    origin: coordinatesSchema,
    destination: coordinatesSchema,
    vehicle_type: vehicleTypeSchema,
    departure_time: z
      .string()
      .optional()
      .refine(
        (val) => {
          if (!val) return true;
          // Validates ISO 8601 with offset or Z
          const parsed = Date.parse(val);
          return !isNaN(parsed);
        },
        { message: "Departure time must be a valid ISO 8601 timestamp with offset" }
      ),
  })
  .refine(
    (data) => {
      return (
        data.origin.lat !== data.destination.lat ||
        data.origin.lng !== data.destination.lng
      );
    },
    {
      message: "Destination coordinates must differ from origin coordinates",
      path: ["destination"],
    }
  );

/**
 * Checks if a [lng, lat] coordinate lies inside [minLng, minLat, maxLng, maxLat]
 */
export function isPointInBbox(
  point: { lat: number; lng: number },
  bbox: [number, number, number, number]
): boolean {
  const [minLng, minLat, maxLng, maxLat] = bbox;
  return (
    point.lng >= minLng &&
    point.lng <= maxLng &&
    point.lat >= minLat &&
    point.lat <= maxLat
  );
}

export type ValidatedRoutePlanRequest = z.infer<typeof routePlanRequestSchema>;
