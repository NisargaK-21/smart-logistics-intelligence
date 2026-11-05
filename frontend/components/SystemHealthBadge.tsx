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
    if (!health) {
      return {
        label: "Checking Health",
        colorBg: "bg-zinc-100 dark:bg-zinc-800",
        colorDot: "bg-zinc-400",
        colorText: "text-zinc-600 dark:text-zinc-400",
      };
    }

    if (health.status === "ok") {
      // If weather is degraded, show amber status
      if (health.modules.weather === "degraded") {
        return {
          label: "Degraded (Weather Fallback)",
          colorBg: "bg-amber-50 dark:bg-amber-950/40",
          colorDot: "bg-amber-500",
          colorText: "text-amber-700 dark:text-amber-300",
        };
      }
      return {
        label: "Systems Operational",
        colorBg: "bg-emerald-50 dark:bg-emerald-950/40",
        colorDot: "bg-emerald-500",
        colorText: "text-emerald-700 dark:text-emerald-300",
      };
    }

    return {
      label: "Service Impaired",
      colorBg: "bg-rose-50 dark:bg-rose-950/40",
      colorDot: "bg-rose-500",
      colorText: "text-rose-700 dark:text-rose-300",
    };
  };

  const status = getStatusDisplay();

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium border border-zinc-200 dark:border-zinc-700 transition-all ${status.colorBg} ${status.colorText}`}
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
        <div className="absolute right-0 top-9 w-72 p-3 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-xl z-50 text-xs space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-zinc-100 dark:border-zinc-800">
            <span className="font-bold text-zinc-900 dark:text-zinc-100">
              System Dependencies Status
            </span>
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="text-[11px] text-sky-600 hover:text-sky-500 font-semibold"
            >
              {isLoading ? "Refreshing..." : "↻ Refresh"}
            </button>
          </div>

          <div className="space-y-2">
            {/* GIS Module */}
            <div className="flex items-center justify-between">
              <span className="text-zinc-600 dark:text-zinc-400">GIS & Road Graph</span>
              <span className="font-mono uppercase font-semibold text-emerald-600 dark:text-emerald-400">
                {health?.modules.gis || "UNKNOWN"}
              </span>
            </div>

            {/* Risk Module */}
            <div className="flex items-center justify-between">
              <span className="text-zinc-600 dark:text-zinc-400">Risk Assessment Engine</span>
              <span className="font-mono uppercase font-semibold text-emerald-600 dark:text-emerald-400">
                {health?.modules.risk || "UNKNOWN"}
              </span>
            </div>

            {/* Weather Module - Explicit Labeling per Rule 4 */}
            <div className="space-y-1 pt-1 border-t border-zinc-100 dark:border-zinc-800">
              <div className="flex items-center justify-between">
                <span className="text-zinc-600 dark:text-zinc-400">Weather Telemetry Feed</span>
                <span className="font-mono uppercase font-semibold text-amber-600 dark:text-amber-400">
                  {health?.modules.weather || "UNKNOWN"}
                </span>
              </div>
              <p className="text-[10px] text-zinc-500 dark:text-zinc-400 italic">
                {isMockMode
                  ? "Configured Mock Weather: Simulates monsoon rainfall hazard."
                  : "Configured/Simulated Weather Fallback: OpenWeatherMap free-tier / cached sample. Not official live radar/satellite."}
              </p>
            </div>
          </div>

          <div className="pt-2 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-between text-[11px] text-zinc-500">
            <span>Mode: {isMockMode ? "Mock Fixtures" : "Live Backend"}</span>
            <button
              onClick={() => setIsOpen(false)}
              className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
