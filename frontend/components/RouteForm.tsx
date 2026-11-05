"use client";

import React, { useState } from "react";
import { Coordinates, VehicleType } from "../lib/types";
import { VEHICLE_OPTIONS } from "../lib/constants";
import { isPointInBbox } from "../lib/validation";

interface RouteFormProps {
  origin: Coordinates | null;
  destination: Coordinates | null;
  onOriginChange: (coords: Coordinates | null) => void;
  onDestinationChange: (coords: Coordinates | null) => void;
  vehicleType: VehicleType;
  onVehicleTypeChange: (type: VehicleType) => void;
  departureTime: string;
  onDepartureTimeChange: (time: string) => void;
  pickingMode: "origin" | "destination" | null;
  onTogglePickingMode: (mode: "origin" | "destination" | null) => void;
  coverageBbox: [number, number, number, number];
  onSubmit: () => void;
  isLoading: boolean;
  formError?: string | null;
}

export default function RouteForm({
  origin,
  destination,
  onOriginChange,
  onDestinationChange,
  vehicleType,
  onVehicleTypeChange,
  departureTime,
  onDepartureTimeChange,
  pickingMode,
  onTogglePickingMode,
  coverageBbox,
  onSubmit,
  isLoading,
  formError,
}: RouteFormProps) {
  const [prevOrigin, setPrevOrigin] = useState(origin);
  const [localOriginLat, setLocalOriginLat] = useState(origin?.lat.toString() || "");
  const [localOriginLng, setLocalOriginLng] = useState(origin?.lng.toString() || "");

  const [prevDest, setPrevDest] = useState(destination);
  const [localDestLat, setLocalDestLat] = useState(destination?.lat.toString() || "");
  const [localDestLng, setLocalDestLng] = useState(destination?.lng.toString() || "");
  const [clientValidationMsg, setClientValidationMsg] = useState<string | null>(null);

  // Sync state during rendering when prop changes (avoids setState in useEffect)
  if (origin !== prevOrigin) {
    setPrevOrigin(origin);
    setLocalOriginLat(origin?.lat.toString() || "");
    setLocalOriginLng(origin?.lng.toString() || "");
  }

  if (destination !== prevDest) {
    setPrevDest(destination);
    setLocalDestLat(destination?.lat.toString() || "");
    setLocalDestLng(destination?.lng.toString() || "");
  }

  const handleApplyOriginInput = (latStr: string, lngStr: string) => {
    setLocalOriginLat(latStr);
    setLocalOriginLng(lngStr);
    const lat = parseFloat(latStr);
    const lng = parseFloat(lngStr);
    if (!isNaN(lat) && !isNaN(lng)) {
      onOriginChange({ lat, lng });
    }
  };

  const handleApplyDestInput = (latStr: string, lngStr: string) => {
    setLocalDestLat(latStr);
    setLocalDestLng(lngStr);
    const lat = parseFloat(latStr);
    const lng = parseFloat(lngStr);
    if (!isNaN(lat) && !isNaN(lng)) {
      onDestinationChange({ lat, lng });
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setClientValidationMsg(null);

    const oLat = parseFloat(localOriginLat);
    const oLng = parseFloat(localOriginLng);
    const dLat = parseFloat(localDestLat);
    const dLng = parseFloat(localDestLng);

    if (isNaN(oLat) || isNaN(oLng)) {
      setClientValidationMsg("Please provide valid origin coordinates (or click 'Pick on Map').");
      return;
    }

    if (isNaN(dLat) || isNaN(dLng)) {
      setClientValidationMsg("Please provide valid destination coordinates (or click 'Pick on Map').");
      return;
    }

    if (oLat < -90 || oLat > 90 || dLat < -90 || dLat > 90) {
      setClientValidationMsg("Latitude must be between -90 and 90 degrees.");
      return;
    }

    if (oLng < -180 || oLng > 180 || dLng < -180 || dLng > 180) {
      setClientValidationMsg("Longitude must be between -180 and 180 degrees.");
      return;
    }

    if (oLat === dLat && oLng === dLng) {
      setClientValidationMsg("Origin and destination coordinates must be different.");
      return;
    }

    // Check coverage corridor bounds
    const originInBounds = isPointInBbox({ lat: oLat, lng: oLng }, coverageBbox);
    const destInBounds = isPointInBbox({ lat: dLat, lng: dLng }, coverageBbox);

    if (!originInBounds || !destInBounds) {
      const [minLng, minLat, maxLng, maxLat] = coverageBbox;
      setClientValidationMsg(
        `Coordinates must fall within the study corridor: Longitude [${minLng}, ${maxLng}], Latitude [${minLat}, ${maxLat}].`
      );
      return;
    }

    onOriginChange({ lat: oLat, lng: oLng });
    onDestinationChange({ lat: dLat, lng: dLng });
    onSubmit();
  };

  return (
    <form
      onSubmit={handleFormSubmit}
      className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 shadow-sm space-y-4"
    >
      <div className="flex items-center justify-between pb-2 border-b border-zinc-100 dark:border-zinc-800">
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
          <span>📍</span> Route Planning & Parameters
        </h2>
        <span className="text-[11px] text-zinc-500 font-mono">Guwahati–Shillong Corridor</span>
      </div>

      {/* Origin Input */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <label className="font-semibold text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block"></span>
            Origin Point (A)
          </label>
          <button
            type="button"
            onClick={() =>
              onTogglePickingMode(pickingMode === "origin" ? null : "origin")
            }
            className={`text-[11px] px-2 py-0.5 rounded font-medium transition-colors ${
              pickingMode === "origin"
                ? "bg-emerald-600 text-white shadow-sm"
                : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-200"
            }`}
          >
            {pickingMode === "origin" ? "Cancel Map Pick" : "🎯 Pick on Map"}
          </button>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <input
            type="number"
            step="any"
            placeholder="Latitude (e.g. 26.1445)"
            value={localOriginLat}
            onChange={(e) => handleApplyOriginInput(e.target.value, localOriginLng)}
            className="w-full text-xs font-mono px-2.5 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/60 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            required
          />
          <input
            type="number"
            step="any"
            placeholder="Longitude (e.g. 91.7362)"
            value={localOriginLng}
            onChange={(e) => handleApplyOriginInput(localOriginLat, e.target.value)}
            className="w-full text-xs font-mono px-2.5 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/60 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            required
          />
        </div>
      </div>

      {/* Destination Input */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <label className="font-semibold text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block"></span>
            Destination Point (B)
          </label>
          <button
            type="button"
            onClick={() =>
              onTogglePickingMode(pickingMode === "destination" ? null : "destination")
            }
            className={`text-[11px] px-2 py-0.5 rounded font-medium transition-colors ${
              pickingMode === "destination"
                ? "bg-rose-600 text-white shadow-sm"
                : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-200"
            }`}
          >
            {pickingMode === "destination" ? "Cancel Map Pick" : "🎯 Pick on Map"}
          </button>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <input
            type="number"
            step="any"
            placeholder="Latitude (e.g. 26.1801)"
            value={localDestLat}
            onChange={(e) => handleApplyDestInput(e.target.value, localDestLng)}
            className="w-full text-xs font-mono px-2.5 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/60 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-1 focus:ring-rose-500"
            required
          />
          <input
            type="number"
            step="any"
            placeholder="Longitude (e.g. 91.7001)"
            value={localDestLng}
            onChange={(e) => handleApplyDestInput(localDestLat, e.target.value)}
            className="w-full text-xs font-mono px-2.5 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/60 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-1 focus:ring-rose-500"
            required
          />
        </div>
      </div>

      {/* Vehicle Type Selection */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 block">
          Logistics Vehicle Class
        </label>
        <div className="grid grid-cols-3 gap-2">
          {VEHICLE_OPTIONS.map((v) => {
            const isSelected = vehicleType === v.id;
            return (
              <button
                key={v.id}
                type="button"
                onClick={() => onVehicleTypeChange(v.id as VehicleType)}
                className={`py-2 px-2 rounded-lg border text-left text-xs transition-all flex flex-col justify-between ${
                  isSelected
                    ? "border-sky-500 bg-sky-50 dark:bg-sky-950/40 text-sky-900 dark:text-sky-100 ring-1 ring-sky-500"
                    : "border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/40 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100"
                }`}
              >
                <div className="flex items-center gap-1.5 font-semibold">
                  <span>{v.icon}</span>
                  <span className="capitalize">{v.id}</span>
                </div>
                <span className="text-[10px] text-zinc-500 mt-1">{v.speed}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Departure Timestamp */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 flex items-center justify-between">
          <span>Scheduled Departure Time</span>
          <span className="text-[10px] text-zinc-500">Optional (Defaults to Now)</span>
        </label>
        <input
          type="datetime-local"
          value={departureTime}
          onChange={(e) => onDepartureTimeChange(e.target.value)}
          className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/60 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-1 focus:ring-sky-500"
        />
      </div>

      {/* Validation Message */}
      {(clientValidationMsg || formError) && (
        <div className="p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs text-rose-700 dark:text-rose-300 flex items-start gap-2">
          <span>⚠️</span>
          <span>{clientValidationMsg || formError}</span>
        </div>
      )}

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full py-2.5 px-4 bg-sky-600 hover:bg-sky-500 active:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-xs rounded-lg shadow-sm transition-colors flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <svg
              className="animate-spin h-3.5 w-3.5 text-white"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              ></circle>
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v8H4z"
              ></path>
            </svg>
            <span>Analyzing Road Network & Risk...</span>
          </>
        ) : (
          <>
            <span>⚡</span>
            <span>Plan Safer Logistics Route</span>
          </>
        )}
      </button>
    </form>
  );
}
