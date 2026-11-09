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
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-24 bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs"
          >
            <div className="h-3 w-24 bg-slate-200 rounded mb-3"></div>
            <div className="h-6 w-16 bg-slate-200 rounded"></div>
          </div>
        ))}
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* 1. Active Hazard Alerts */}
      <div className="bg-white border border-slate-200/90 rounded-xl p-4 shadow-xs hover:border-slate-300 transition-all">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-500 inline-block"></span>
            Active Hazard Alerts
          </span>
          <span className="text-base">⚠️</span>
        </div>
        <div className="mt-2 flex items-baseline justify-between">
          <span className="text-2xl font-bold font-mono text-slate-900 tracking-tight">
            {summary.active_alerts_count}
          </span>
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200/60">
            Advisories Active
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
          <span>Corridor risk level</span>
          <span className="font-medium text-amber-600">Elevated</span>
        </div>
      </div>

      {/* 2. High Risk Zones */}
      <div className="bg-white border border-slate-200/90 rounded-xl p-4 shadow-xs hover:border-slate-300 transition-all">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-rose-500 inline-block"></span>
            High Risk Zones
          </span>
          <span className="text-base">🚨</span>
        </div>
        <div className="mt-2 flex items-baseline justify-between">
          <span className="text-2xl font-bold font-mono text-slate-900 tracking-tight">
            {summary.high_risk_zones_count}
          </span>
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200/60">
            Critical Segments
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
          <span>Landslide & flood prone</span>
          <span className="font-medium text-rose-600">Monitored</span>
        </div>
      </div>

      {/* 3. Active Fleet Vehicles */}
      <div className="bg-white border border-slate-200/90 rounded-xl p-4 shadow-xs hover:border-slate-300 transition-all">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-sky-500 inline-block"></span>
            Active Fleet Vehicles
          </span>
          <span className="text-base">🚚</span>
        </div>
        <div className="mt-2 flex items-baseline justify-between">
          <span className="text-2xl font-bold font-mono text-slate-900 tracking-tight">
            {summary.active_vehicles_count}
          </span>
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-sky-50 text-sky-700 border border-sky-200/60">
            GPS Connected
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
          <span>Active corridor trips</span>
          <span className="font-medium text-sky-600">Simulated / Live</span>
        </div>
      </div>

      {/* 4. Field Incident Reports */}
      <div className="bg-white border border-slate-200/90 rounded-xl p-4 shadow-xs hover:border-slate-300 transition-all">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block"></span>
            Field Incident Reports
          </span>
          <span className="text-base">📝</span>
        </div>
        <div className="mt-2 flex items-baseline justify-between">
          <span className="text-2xl font-bold font-mono text-slate-900 tracking-tight">
            {summary.recent_reports_count}
          </span>
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/60">
            Verified On-Ground
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
          <span>Telemetry accuracy</span>
          <span className="font-medium text-emerald-600">Confirmed</span>
        </div>
      </div>
    </div>
  );
}
