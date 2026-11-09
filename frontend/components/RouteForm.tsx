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

const PRESET_CORRIDORS = [
  {
    name: "Guwahati Central → North Depot",
    origin: { lat: 26.1445, lng: 91.7362 },
    destination: { lat: 26.1801, lng: 91.7001 },
  },
  {
    name: "Dispur Hub → Khanapara Checkpoint",
    origin: { lat: 26.1400, lng: 91.7800 },
    destination: { lat: 26.1320, lng: 91.8200 },
  },
  {
    name: "Jalukbari Transit → Beltola Center",
    origin: { lat: 26.1550, lng: 91.7100 },
    destination: { lat: 26.1350, lng: 91.7900 },
  },
];

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

  // Sync state during rendering when prop changes
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

  const applyPreset = (preset: (typeof PRESET_CORRIDORS)[0]) => {
    onOriginChange(preset.origin);
    onDestinationChange(preset.destination);
    setLocalOriginLat(preset.origin.lat.toString());
    setLocalOriginLng(preset.origin.lng.toString());
    setLocalDestLat(preset.destination.lat.toString());
    setLocalDestLng(preset.destination.lng.toString());
    setClientValidationMsg(null);
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
      className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs space-y-4"
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div>
          <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <span className="text-sky-600">📍</span> Route Planning & Parameters
          </h2>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Evaluate road risks & calculate multi-segment alternatives
          </p>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 bg-slate-100 rounded text-slate-600 border border-slate-200">
          NH-6 Corridor
        </span>
      </div>

      {/* Preset Corridor Selector */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-slate-700 block">
          Corridor Presets (Quick Load)
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-1.5">
          {PRESET_CORRIDORS.map((p, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => applyPreset(p)}
              className="text-[11px] text-left px-2.5 py-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-sky-50 hover:border-sky-300 text-slate-700 transition-colors truncate"
              title={p.name}
            >
              {p.name}
            </button>
          ))}
        </div>
      </div>

      {/* Origin Input */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <label className="font-semibold text-slate-800 flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block shadow-2xs"></span>
            Origin Point (A)
          </label>
          <button
            type="button"
            onClick={() =>
              onTogglePickingMode(pickingMode === "origin" ? null : "origin")
            }
            className={`text-[11px] px-2.5 py-1 rounded-md font-semibold transition-all ${
              pickingMode === "origin"
                ? "bg-emerald-600 text-white shadow-xs"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200/80"
            }`}
          >
            {pickingMode === "origin" ? "✕ Cancel Picking" : "🎯 Pick on Map"}
          </button>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className="text-[10px] text-slate-400 font-mono mb-0.5 block">Latitude</span>
            <input
              type="number"
              step="any"
              placeholder="e.g. 26.1445"
              value={localOriginLat}
              onChange={(e) => handleApplyOriginInput(e.target.value, localOriginLng)}
              className="w-full text-xs font-mono px-3 py-2 rounded-lg border border-slate-200 bg-slate-50/70 text-slate-900 focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:bg-white"
              required
            />
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-mono mb-0.5 block">Longitude</span>
            <input
              type="number"
              step="any"
              placeholder="e.g. 91.7362"
              value={localOriginLng}
              onChange={(e) => handleApplyOriginInput(localOriginLat, e.target.value)}
              className="w-full text-xs font-mono px-3 py-2 rounded-lg border border-slate-200 bg-slate-50/70 text-slate-900 focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:bg-white"
              required
            />
          </div>
        </div>
      </div>

      {/* Destination Input */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <label className="font-semibold text-slate-800 flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block shadow-2xs"></span>
            Destination Point (B)
          </label>
          <button
            type="button"
            onClick={() =>
              onTogglePickingMode(pickingMode === "destination" ? null : "destination")
            }
            className={`text-[11px] px-2.5 py-1 rounded-md font-semibold transition-all ${
              pickingMode === "destination"
                ? "bg-rose-600 text-white shadow-xs"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200/80"
            }`}
          >
            {pickingMode === "destination" ? "✕ Cancel Picking" : "🎯 Pick on Map"}
          </button>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className="text-[10px] text-slate-400 font-mono mb-0.5 block">Latitude</span>
            <input
              type="number"
              step="any"
              placeholder="e.g. 26.1801"
              value={localDestLat}
              onChange={(e) => handleApplyDestInput(e.target.value, localDestLng)}
              className="w-full text-xs font-mono px-3 py-2 rounded-lg border border-slate-200 bg-slate-50/70 text-slate-900 focus:outline-none focus:ring-1 focus:ring-rose-500 focus:bg-white"
              required
            />
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-mono mb-0.5 block">Longitude</span>
            <input
              type="number"
              step="any"
              placeholder="e.g. 91.7001"
              value={localDestLng}
              onChange={(e) => handleApplyDestInput(localDestLat, e.target.value)}
              className="w-full text-xs font-mono px-3 py-2 rounded-lg border border-slate-200 bg-slate-50/70 text-slate-900 focus:outline-none focus:ring-1 focus:ring-rose-500 focus:bg-white"
              required
            />
          </div>
        </div>
      </div>

      {/* Vehicle Type Selection */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-slate-800 block">
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
                className={`py-2 px-2.5 rounded-lg border text-left text-xs transition-all flex flex-col justify-between ${
                  isSelected
                    ? "border-sky-600 bg-sky-50/80 text-sky-900 ring-1 ring-sky-600 shadow-2xs font-medium"
                    : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50/80"
                }`}
              >
                <div className="flex items-center gap-1.5 font-bold">
                  <span className="text-base">{v.icon}</span>
                  <span className="capitalize">{v.id}</span>
                </div>
                <span className="text-[10px] text-slate-500 mt-1 font-mono">{v.speed}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Departure Timestamp */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-slate-800 flex items-center justify-between">
          <span>Scheduled Departure Time</span>
          <span className="text-[10px] text-slate-500 font-normal">Optional (Defaults to Now)</span>
        </label>
        <input
          type="datetime-local"
          value={departureTime}
          onChange={(e) => onDepartureTimeChange(e.target.value)}
          className="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 bg-slate-50/70 text-slate-900 focus:outline-none focus:ring-1 focus:ring-sky-500 focus:bg-white"
        />
      </div>

      {/* Validation Message */}
      {(clientValidationMsg || formError) && (
        <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-start gap-2 shadow-2xs">
          <span className="text-base leading-none">⚠️</span>
          <span className="leading-relaxed font-medium">{clientValidationMsg || formError}</span>
        </div>
      )}

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full py-2.5 px-4 bg-sky-600 hover:bg-sky-500 active:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-xs rounded-lg shadow-sm transition-all flex items-center justify-center gap-2 cursor-pointer"
      >
        {isLoading ? (
          <>
            <svg
              className="animate-spin h-4 w-4 text-white"
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
            <span>Evaluating Terrain, Weather & Hazard Network...</span>
          </>
        ) : (
          <>
            <span>⚡</span>
            <span>Plan Disaster-Resilient Route</span>
          </>
        )}
      </button>
    </form>
  );
}
