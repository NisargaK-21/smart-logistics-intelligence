"use client";

import React from "react";
import { DashboardSummary, Route } from "../lib/types";

interface DashboardMetricsProps {
  summary: DashboardSummary | null;
  routes?: Route[];
  isLoading: boolean;
}

export default function DashboardMetrics({
  summary,
  routes = [],
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
  const highRiskRouteCount = routes.filter((route) => route.risk_level === "high").length;
  const highRiskHazardsCount = summary.high_risk_zones_count || 0;

  // If routes have been evaluated, show the route-level high risk count, otherwise show monitored high-risk hazard zones
  const highRiskDisplayCount = routes.length > 0 ? highRiskRouteCount : highRiskHazardsCount;
  const highRiskBadge =
    routes.length > 0
      ? `${routes.length} options evaluated`
      : `${highRiskHazardsCount} active corridor zones`;
  const highRiskSubtext =
    routes.length > 0 ? "Evaluated route candidates" : "Monitored hazard locations";

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* 1. Active Hazard Alerts */}
      <div className="bg-white border border-slate-200/90 rounded-xl p-4 shadow-xs hover:border-slate-300 transition-all">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-500 inline-block"></span>
            Reported Alerts
          </span>
          <span className="text-base">⚠️</span>
        </div>
        <div className="mt-2 flex items-baseline justify-between">
          <span className="text-2xl font-bold font-mono text-slate-900 tracking-tight">
            {summary.active_alerts_count}
          </span>
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200/60">
            Current count
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
          <span>Current alert records</span>
          <span className="font-medium text-amber-600">Backend</span>
        </div>
      </div>

      {/* 2. High-risk route candidates & active corridor hazard zones */}
      <div className="bg-white border border-slate-200/90 rounded-xl p-4 shadow-xs hover:border-slate-300 transition-all">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-rose-500 inline-block"></span>
            High-Risk Hazards & Routes
          </span>
          <span className="text-base">🚨</span>
        </div>
        <div className="mt-2 flex items-baseline justify-between">
          <span className="text-2xl font-bold font-mono text-slate-900 tracking-tight">
            {highRiskDisplayCount}
          </span>
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200/60">
            {highRiskBadge}
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
          <span>{highRiskSubtext}</span>
          <span className="font-medium text-rose-600">Risk Assessment</span>
        </div>
      </div>

      {/* 3. Active Fleet Vehicles */}
      <div className="bg-white border border-slate-200/90 rounded-xl p-4 shadow-xs hover:border-slate-300 transition-all">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-sky-500 inline-block"></span>
            Simulated Vehicles
          </span>
          <span className="text-base">🚚</span>
        </div>
        <div className="mt-2 flex items-baseline justify-between">
          <span className="text-2xl font-bold font-mono text-slate-900 tracking-tight">
            {summary.active_vehicles_count}
          </span>
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-sky-50 text-sky-700 border border-sky-200/60">
            Current records
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
          <span>Started in this session</span>
          <span className="font-medium text-sky-600">Simulation</span>
        </div>
      </div>

      {/* 4. Field Incident Reports */}
      <div className="bg-white border border-slate-200/90 rounded-xl p-4 shadow-xs hover:border-slate-300 transition-all">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block"></span>
            Session Reports
          </span>
          <span className="text-base">📝</span>
        </div>
        <div className="mt-2 flex items-baseline justify-between">
          <span className="text-2xl font-bold font-mono text-slate-900 tracking-tight">
            {summary.recent_reports_count}
          </span>
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/60">
            Received reports
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
          <span>Stored in</span>
          <span className="font-medium text-emerald-600">Current session</span>
        </div>
      </div>
    </div>
  );
}
