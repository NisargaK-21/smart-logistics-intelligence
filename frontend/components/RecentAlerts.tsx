"use client";

import React, { useState } from "react";
import { Alert } from "../lib/types";

interface RecentAlertsProps {
  alerts: Alert[];
  reportsCount: number;
}

export default function RecentAlerts({ alerts, reportsCount }: RecentAlertsProps) {
  const [filter, setFilter] = useState<"all" | "high">("all");

  const filteredIncidents =
    filter === "high"
      ? alerts.filter((alert) => alert.severity === "high" || alert.severity === "critical")
      : alerts;

  const getSeverityBadge = (severity: Alert["severity"]) => {
    switch (severity) {
      case "critical":
        return "bg-rose-100 text-rose-800 border-rose-200";
      case "high":
        return "bg-amber-100 text-amber-800 border-amber-200";
      case "medium":
        return "bg-sky-100 text-sky-800 border-sky-200";
      default:
        return "bg-emerald-100 text-emerald-800 border-emerald-200";
    }
  };

  return (
    <div className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs space-y-3.5">
      <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <span>🚨</span> Recent Alerts & Field Activity
          </h3>
          <p className="text-[11px] text-slate-500 mt-0.5">
            User-submitted reports and route alerts stored for this session
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg border border-slate-200">
          <button
            type="button"
            onClick={() => setFilter("all")}
            className={`px-2 py-0.5 text-[10px] font-semibold rounded-md transition-all cursor-pointer ${
              filter === "all"
                ? "bg-white text-slate-900 shadow-2xs font-bold"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            All ({alerts.length})
          </button>
          <button
            type="button"
            onClick={() => setFilter("high")}
            className={`px-2 py-0.5 text-[10px] font-semibold rounded-md transition-all cursor-pointer ${
              filter === "high"
                ? "bg-white text-rose-700 shadow-2xs font-bold"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            High Risk
          </button>
        </div>
      </div>

      {/* Incident List */}
      <div className="space-y-2.5">
        {filteredIncidents.map((alert) => (
          <div
            key={alert.alert_id}
            className="p-3 rounded-lg border border-slate-200/80 bg-slate-50/60 hover:bg-slate-50 transition-colors"
          >
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="font-bold text-slate-800">{alert.title}</span>
              <span
                className={`text-[9px] uppercase font-bold px-1.5 py-0.2 rounded border ${getSeverityBadge(alert.severity)}`}
              >
                {alert.severity}
              </span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">{alert.message}</p>
            <div className="mt-2 pt-1.5 border-t border-slate-200/50 flex items-center justify-between text-[10px] text-slate-400">
              <span className="font-medium text-slate-600 flex items-center gap-1">
                <span>📍</span>{" "}
                {alert.location
                  ? `${alert.location.lat.toFixed(3)}, ${alert.location.lng.toFixed(3)}`
                  : alert.route_id || "Route"}
              </span>
              <span>{new Date(alert.created_at).toLocaleString()}</span>
            </div>
          </div>
        ))}
        {filteredIncidents.length === 0 && (
          <p className="py-5 text-center text-xs text-slate-500">
            {alerts.length === 0
              ? "No route alerts have been reported."
              : "No high-severity alerts are currently reported."}
          </p>
        )}
      </div>

      {/* Summary Footer */}
      <div className="pt-2 border-t border-slate-100 flex items-center justify-end text-[11px] text-slate-500">
        <span className="font-semibold text-slate-700">{reportsCount} reports received</span>
      </div>
    </div>
  );
}
