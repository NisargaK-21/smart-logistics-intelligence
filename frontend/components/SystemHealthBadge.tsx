"use client";

import React, { useState } from "react";
import { HealthResponse } from "../lib/types";

interface SystemHealthBadgeProps {
  health: HealthResponse | null;
  isLoading: boolean;
  onRefresh: () => void;
  isMockMode: boolean;
}

export default function SystemHealthBadge({
  health,
  isLoading,
  onRefresh,
  isMockMode,
}: SystemHealthBadgeProps) {
  const [isOpen, setIsOpen] = useState(false);

  const getStatusDisplay = () => {
    if (isMockMode) {
      return {
        label: "Mock Telemetry (Offline)",
        colorBg: "bg-sky-50",
        colorDot: "bg-sky-500",
        colorText: "text-sky-800",
        borderColor: "border-sky-200",
      };
    }

    if (!health) {
      return {
        label: "Pinging Backend...",
        colorBg: "bg-slate-100",
        colorDot: "bg-slate-400",
        colorText: "text-slate-600",
        borderColor: "border-slate-200",
      };
    }

    if (health.status === "ok") {
      // If weather is degraded, show amber status
      if (health.modules.weather === "degraded") {
        return {
          label: "Degraded (Weather Fallback)",
          colorBg: "bg-amber-50",
          colorDot: "bg-amber-500",
          colorText: "text-amber-800",
          borderColor: "border-amber-200",
        };
      }
      return {
        label: "Live Confirmed Active",
        colorBg: "bg-emerald-50",
        colorDot: "bg-emerald-500",
        colorText: "text-emerald-800",
        borderColor: "border-emerald-200",
      };
    }

    return {
      label: "Backend Service Impaired",
      colorBg: "bg-rose-50",
      colorDot: "bg-rose-500",
      colorText: "text-rose-800",
      borderColor: "border-rose-200",
    };
  };

  const status = getStatusDisplay();

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer ${status.colorBg} ${status.colorText} ${status.borderColor} shadow-2xs hover:shadow-xs`}
        title="View system & dependency health"
      >
        <span
          className={`w-2 h-2 rounded-full ${status.colorDot} ${
            health?.status === "ok" ? "animate-pulse" : ""
          }`}
        />
        <span>{status.label}</span>
        <span className="text-[10px] opacity-60">▼</span>
      </button>

      {/* Popover Breakdown */}
      {isOpen && (
        <div className="absolute right-0 top-10 w-80 p-4 bg-white border border-slate-200 rounded-xl shadow-xl z-50 text-xs space-y-3.5">
          <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
            <span className="font-bold text-slate-900">
              System Dependencies Status
            </span>
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="text-[11px] text-sky-600 hover:text-sky-700 font-bold cursor-pointer"
            >
              {isLoading ? "Refreshing..." : "↻ Refresh"}
            </button>
          </div>

          <div className="space-y-2.5">
            {/* Backend API */}
            <div className="flex items-center justify-between">
              <span className="text-slate-600 font-medium">Backend API</span>
              <span
                className={`font-mono uppercase text-[10px] font-bold px-2 py-0.5 rounded border ${
                  isMockMode
                    ? "text-sky-700 bg-sky-50 border-sky-200"
                    : health?.status === "ok"
                    ? "text-emerald-700 bg-emerald-50 border-emerald-200"
                    : "text-rose-700 bg-rose-50 border-rose-200"
                }`}
              >
                {isMockMode ? "MOCK FIXTURE" : health?.status === "ok" ? "OPERATIONAL" : "UNREACHABLE"}
              </span>
            </div>

            {/* GIS & Routing Engine */}
            <div className="flex items-center justify-between">
              <span className="text-slate-600 font-medium">GIS & Routing Engine</span>
              <span
                className={`font-mono uppercase text-[10px] font-bold px-2 py-0.5 rounded border ${
                  isMockMode
                    ? "text-sky-700 bg-sky-50 border-sky-200"
                    : health?.modules.gis === "ok"
                    ? "text-emerald-700 bg-emerald-50 border-emerald-200"
                    : "text-rose-700 bg-rose-50 border-rose-200"
                }`}
              >
                {isMockMode ? "SIMULATED" : health?.modules.gis === "ok" ? "OPERATIONAL" : "UNAVAILABLE"}
              </span>
            </div>

            {/* Risk Assessment Service */}
            <div className="flex items-center justify-between">
              <span className="text-slate-600 font-medium">Risk Assessment Service</span>
              <span
                className={`font-mono uppercase text-[10px] font-bold px-2 py-0.5 rounded border ${
                  isMockMode
                    ? "text-sky-700 bg-sky-50 border-sky-200"
                    : health?.modules.risk === "ok"
                    ? "text-emerald-700 bg-emerald-50 border-emerald-200"
                    : "text-rose-700 bg-rose-50 border-rose-200"
                }`}
              >
                {isMockMode ? "BASELINE (MOCK)" : health?.modules.risk === "ok" ? "OPERATIONAL" : "UNAVAILABLE"}
              </span>
            </div>

            {/* Weather Data Service */}
            <div className="space-y-1.5 pt-2 border-t border-slate-100">
              <div className="flex items-center justify-between">
                <span className="text-slate-600 font-medium">Weather Data Service</span>
                <span
                  className={`font-mono uppercase text-[10px] font-bold px-2 py-0.5 rounded border ${
                    isMockMode
                      ? "text-sky-700 bg-sky-50 border-sky-200"
                      : health?.modules.weather === "ok"
                      ? "text-emerald-700 bg-emerald-50 border-emerald-200"
                      : health?.modules.weather === "degraded"
                      ? "text-amber-700 bg-amber-50 border-amber-200"
                      : "text-rose-700 bg-rose-50 border-rose-200"
                  }`}
                >
                  {isMockMode
                    ? "SIMULATED"
                    : health?.modules.weather === "ok"
                    ? "OPERATIONAL"
                    : health?.modules.weather === "degraded"
                    ? "DEGRADED (FALLBACK)"
                    : "UNAVAILABLE"}
                </span>
              </div>
              <p className="text-[10px] text-slate-500 italic leading-relaxed">
                {isMockMode
                  ? "Configured Mock Weather: Simulating historical Northeast monsoon precipitation anomalies along NH-6."
                  : "Configured/Simulated Weather Fallback: OpenWeatherMap free-tier / cached sample. Certified live radar/satellite feeds unavailable."}
              </p>
            </div>
          </div>

          <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
            <span>Mode: {isMockMode ? "Mock Fixtures" : "Live Backend"}</span>
            <button
              onClick={() => setIsOpen(false)}
              className="text-slate-400 hover:text-slate-600 font-medium cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
