"use client";

import React, { useState } from "react";
import { DashboardSummary } from "../lib/types";

interface RecentAlertsProps {
  summary: DashboardSummary | null;
}

interface IncidentItem {
  id: string;
  title: string;
  location: string;
  severity: "critical" | "high" | "medium" | "info";
  time: string;
  description: string;
}

const DEFAULT_INCIDENTS: IncidentItem[] = [
  {
    id: "inc-101",
    title: "Slope Instability & Debris on Roadway",
    location: "NH-6 KM 48 (Near Byrnihat)",
    severity: "high",
    time: "15 min ago",
    description: "Slight mud accumulation after heavy rain. Heavy freight advised caution.",
  },
  {
    id: "inc-102",
    title: "Waterlogging at Drainage Culvert",
    location: "Nongpoh Bypass Junction",
    severity: "medium",
    time: "42 min ago",
    description: "Water level receding; standard commercial trucks operating normally.",
  },
  {
    id: "inc-103",
    title: "Field Officer Ground Verification",
    location: "Umiam Lake Viewpoint Sector",
    severity: "info",
    time: "1 hr ago",
    description: "Road geometry cleared of previous construction barriers; both lanes open.",
  },
];

export default function RecentAlerts({ summary }: RecentAlertsProps) {
  const [filter, setFilter] = useState<"all" | "high">("all");

  const filteredIncidents =
    filter === "high"
      ? DEFAULT_INCIDENTS.filter((i) => i.severity === "high" || i.severity === "critical")
      : DEFAULT_INCIDENTS;

  const getSeverityBadge = (severity: IncidentItem["severity"]) => {
    switch (severity) {
      case "critical":
        return "bg-rose-100 text-rose-800 border-rose-200";
      case "high":
        return "bg-amber-100 text-amber-800 border-amber-200";
      case "medium":
        return "bg-sky-100 text-sky-800 border-sky-200";
      case "info":
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
            Active ground incident reports along monitored logistics corridors
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
            All ({DEFAULT_INCIDENTS.length})
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
        {filteredIncidents.map((inc) => (
          <div
            key={inc.id}
            className="p-3 rounded-lg border border-slate-200/80 bg-slate-50/60 hover:bg-slate-50 transition-colors"
          >
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="font-bold text-slate-800">{inc.title}</span>
              <span
                className={`text-[9px] uppercase font-bold px-1.5 py-0.2 rounded border ${getSeverityBadge(
                  inc.severity
                )}`}
              >
                {inc.severity}
              </span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">{inc.description}</p>
            <div className="mt-2 pt-1.5 border-t border-slate-200/50 flex items-center justify-between text-[10px] text-slate-400">
              <span className="font-medium text-slate-600 flex items-center gap-1">
                <span>📍</span> {inc.location}
              </span>
              <span>{inc.time}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Summary Footer */}
      {summary && (
        <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
          <span>Active Telemetry Streams: 4 sensors</span>
          <span className="font-semibold text-slate-700">
            {summary.recent_reports_count} reports filed today
          </span>
        </div>
      )}
    </div>
  );
}
