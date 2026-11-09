"use client";

import React from "react";
import { HealthResponse } from "../lib/types";

interface WeatherTerrainOverviewProps {
  health: HealthResponse | null;
  isMockMode: boolean;
}

export default function WeatherTerrainOverview({
  health,
  isMockMode,
}: WeatherTerrainOverviewProps) {
  const isWeatherDegraded = health?.modules.weather === "degraded";

  return (
    <div className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs space-y-3.5">
      <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <span>🌦️</span> Weather & Terrain Overview
          </h3>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Guwahati–Shillong Corridor (Elev. 55m – 1,496m)
          </p>
        </div>
        <span
          className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
            isWeatherDegraded
              ? "bg-amber-50 text-amber-700 border-amber-200"
              : "bg-emerald-50 text-emerald-700 border-emerald-200"
          }`}
        >
          {isWeatherDegraded ? "Degraded Weather" : "Feed Active"}
        </span>
      </div>

      {/* Grid of Key Atmospheric & Topographical Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80">
          <span className="text-[10px] text-slate-500 block font-medium">Monsoon Rainfall</span>
          <span className="text-base font-bold font-mono text-slate-900 block mt-0.5">
            18.5 mm/h
          </span>
          <span className="text-[10px] text-amber-600 font-semibold">Moderate Intensity</span>
        </div>

        <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80">
          <span className="text-[10px] text-slate-500 block font-medium">Slope Gradient</span>
          <span className="text-base font-bold font-mono text-slate-900 block mt-0.5">
            8.4° – 14.2°
          </span>
          <span className="text-[10px] text-rose-600 font-semibold">Steep Hillside</span>
        </div>

        <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80">
          <span className="text-[10px] text-slate-500 block font-medium">Elevation Delta</span>
          <span className="text-base font-bold font-mono text-slate-900 block mt-0.5">
            +1,440 m
          </span>
          <span className="text-[10px] text-sky-600 font-semibold">Plateau Ascent</span>
        </div>

        <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80">
          <span className="text-[10px] text-slate-500 block font-medium">Landslide Factor</span>
          <span className="text-base font-bold font-mono text-slate-900 block mt-0.5">
            Tier-3
          </span>
          <span className="text-[10px] text-amber-600 font-semibold">High Vulnerability</span>
        </div>
      </div>

      {/* Data Disclosure Notice */}
      <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/70 text-[11px] text-slate-500 leading-relaxed flex items-start gap-2">
        <span className="text-slate-400 mt-0.5">ℹ️</span>
        <p>
          {isMockMode
            ? "Mock Weather Engine: Simulating historical Northeast monsoon precipitation anomalies along NH-6."
            : "Live Weather Telemetry: OpenWeatherMap standard feed combined with GIS digital elevation model (DEM) slope calculations."}
        </p>
      </div>
    </div>
  );
}
