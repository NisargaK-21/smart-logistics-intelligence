"use client";

import React from "react";
import { DashboardSummary } from "../lib/types";

interface DashboardMetricsProps {
  summary: DashboardSummary | null;
  isLoading: boolean;
}

export default function DashboardMetrics({
  summary,
  isLoading,
}: DashboardMetricsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 animate-pulse">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-20 bg-zinc-100 dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700/60"
          />
        ))}
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Active Alerts */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-3 shadow-xs">
          <div className="flex items-center justify-between text-xs text-zinc-500">
            <span>Active Hazard Alerts</span>
            <span>⚠️</span>
          </div>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="text-xl font-bold font-mono text-amber-600 dark:text-amber-400">
              {summary.active_alerts_count}
            </span>
            <span className="text-[10px] text-zinc-400">active</span>
          </div>
          <span className="text-[10px] text-zinc-400 block mt-0.5">Corridor risk advisories</span>
        </div>

        {/* High Risk Zones */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-3 shadow-xs">
          <div className="flex items-center justify-between text-xs text-zinc-500">
            <span>High Risk Zones</span>
            <span>🚨</span>
          </div>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="text-xl font-bold font-mono text-rose-600 dark:text-rose-400">
              {summary.high_risk_zones_count}
            </span>
            <span className="text-[10px] text-zinc-400">segments</span>
          </div>
          <span className="text-[10px] text-zinc-400 block mt-0.5">Landslide & flood prone</span>
        </div>

        {/* Monitored Vehicles */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-3 shadow-xs">
          <div className="flex items-center justify-between text-xs text-zinc-500">
            <span>Active Fleet Vehicles</span>
            <span>🚚</span>
          </div>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="text-xl font-bold font-mono text-sky-600 dark:text-sky-400">
              {summary.active_vehicles_count}
            </span>
            <span className="text-[10px] text-zinc-400">simulated</span>
          </div>
          <span className="text-[10px] text-zinc-400 block mt-0.5">GPS tracked along routes</span>
        </div>

        {/* Incident Field Reports */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-3 shadow-xs">
          <div className="flex items-center justify-between text-xs text-zinc-500">
            <span>Field Incident Reports</span>
            <span>📝</span>
          </div>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="text-xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
              {summary.recent_reports_count}
            </span>
            <span className="text-[10px] text-zinc-400">recorded</span>
          </div>
          <span className="text-[10px] text-zinc-400 block mt-0.5">Verified on-ground reports</span>
        </div>
      </div>
    </div>
  );
}
