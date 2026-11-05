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
      className={`p-3.5 rounded-xl border transition-all cursor-pointer relative ${
        isSelected
          ? "border-sky-500 bg-sky-50/70 dark:bg-sky-950/30 ring-2 ring-sky-500/50 shadow-md"
          : isRecommended
          ? "border-sky-300 dark:border-sky-800 bg-white dark:bg-zinc-900 hover:border-sky-400 shadow-sm"
          : "border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:border-zinc-300 dark:hover:border-zinc-700 shadow-sm"
      }`}
    >
      {/* Recommended Tag */}
      {isRecommended && (
        <div className="inline-flex items-center gap-1 mb-2 px-2 py-0.5 rounded-full bg-sky-500 text-white text-[10px] font-bold tracking-wide shadow-xs">
          <span>★</span>
          <span>RECOMMENDED ROUTE (LOWEST RISK)</span>
        </div>
      )}

      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-sm text-zinc-900 dark:text-zinc-100">
              {route.route_id.toUpperCase()}
            </h3>
            <span
              className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${levelConfig.badgeBg} ${levelConfig.badgeText} ${levelConfig.badgeBorder}`}
            >
              {levelConfig.label}
            </span>
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
            {route.segments.length} Road Segments • Quality:{" "}
            <span className="capitalize font-medium">{route.data_quality}</span>
          </p>
        </div>

        {/* Risk Score Pill */}
        <div className="text-right">
          <div className="flex items-baseline justify-end gap-1">
            <span
              className="text-lg font-black font-mono leading-none"
              style={{ color: levelConfig.colorHex }}
            >
              {route.risk_score}
            </span>
            <span className="text-[10px] text-zinc-400 font-mono">/100</span>
          </div>
          <span className="text-[10px] text-zinc-500 block">Risk Score</span>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 gap-2 mt-3 pt-2.5 border-t border-zinc-100 dark:border-zinc-800/80 text-xs">
        <div className="flex items-center gap-1.5 text-zinc-700 dark:text-zinc-300">
          <span className="text-zinc-400">📏</span>
          <div>
            <span className="font-semibold">{route.distance_km.toFixed(1)} km</span>
            <span className="text-[10px] text-zinc-400 block">Distance</span>
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-zinc-700 dark:text-zinc-300">
          <span className="text-zinc-400">⏱️</span>
          <div>
            <span className="font-semibold">
              {formatDuration(route.estimated_duration_minutes)}
            </span>
            <span className="text-[10px] text-zinc-400 block">Est. Duration</span>
          </div>
        </div>
      </div>
    </div>
  );
}
