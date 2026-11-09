"use client";

import React from "react";
import { Route } from "../lib/types";
import { RISK_LEVEL_CONFIG } from "../lib/constants";

interface RouteCardProps {
  route: Route;
  isRecommended: boolean;
  isSelected: boolean;
  onSelect: () => void;
}

export default function RouteCard({
  route,
  isRecommended,
  isSelected,
  onSelect,
}: RouteCardProps) {
  const levelConfig = RISK_LEVEL_CONFIG[route.risk_level];

  const formatDuration = (mins: number) => {
    const hours = Math.floor(mins / 60);
    const remainingMins = Math.round(mins % 60);
    if (hours === 0) return `${remainingMins}m`;
    return `${hours}h ${remainingMins}m`;
  };

  return (
    <div
      onClick={onSelect}
      className={`p-4 rounded-xl border transition-all cursor-pointer relative ${
        isSelected
          ? "border-sky-600 bg-sky-50/60 ring-2 ring-sky-500/40 shadow-xs"
          : isRecommended
          ? "border-sky-200 bg-white hover:border-sky-400 shadow-xs"
          : "border-slate-200 bg-white hover:border-slate-300 shadow-xs"
      }`}
    >
      {/* Recommended Tag */}
      {isRecommended && (
        <div className="inline-flex items-center gap-1 mb-2 px-2.5 py-0.5 rounded-full bg-sky-600 text-white text-[10px] font-bold tracking-wide shadow-2xs">
          <span>★</span>
          <span>RECOMMENDED (LOWEST RISK)</span>
        </div>
      )}

      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-sm text-slate-900 tracking-tight">
              {route.route_id.toUpperCase()}
            </h3>
            <span
              className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${levelConfig.badgeBg.replace(/dark:[^\s]+/g, "")} ${levelConfig.badgeText.replace(/dark:[^\s]+/g, "")} ${levelConfig.badgeBorder.replace(/dark:[^\s]+/g, "")}`}
            >
              {levelConfig.label}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {route.segments.length} Road Segments • Telemetry:{" "}
            <span className="capitalize font-medium text-slate-700">{route.data_quality}</span>
          </p>
        </div>

        {/* Risk Score Pill */}
        <div className="text-right">
          <div className="flex items-baseline justify-end gap-1">
            <span
              className="text-xl font-black font-mono leading-none"
              style={{ color: levelConfig.colorHex }}
            >
              {route.risk_score}
            </span>
            <span className="text-[10px] text-slate-400 font-mono">/100</span>
          </div>
          <span className="text-[10px] text-slate-500 block mt-0.5 font-medium">Risk Score</span>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 gap-3 mt-3 pt-3 border-t border-slate-100 text-xs">
        <div className="flex items-center gap-2 text-slate-700">
          <span className="text-slate-400">📏</span>
          <div>
            <span className="font-bold text-slate-900">{route.distance_km.toFixed(1)} km</span>
            <span className="text-[10px] text-slate-400 block">Total Distance</span>
          </div>
        </div>

        <div className="flex items-center gap-2 text-slate-700">
          <span className="text-slate-400">⏱️</span>
          <div>
            <span className="font-bold text-slate-900">
              {formatDuration(route.estimated_duration_minutes)}
            </span>
            <span className="text-[10px] text-slate-400 block">Est. Duration</span>
          </div>
        </div>
      </div>
    </div>
  );
}
