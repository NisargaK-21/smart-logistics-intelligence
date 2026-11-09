"use client";

import React from "react";
import { Route } from "../lib/types";
import { RISK_THRESHOLDS } from "../lib/constants";

interface RiskDistributionProps {
  route: Route | null;
}

export default function RiskDistribution({ route }: RiskDistributionProps) {
  if (!route || !route.segments || route.segments.length === 0) {
    return null;
  }

  const total = route.segments.length;
  let lowCount = 0;
  let medCount = 0;
  let highCount = 0;

  route.segments.forEach((seg) => {
    if (seg.risk_score <= RISK_THRESHOLDS.LOW_MAX) lowCount++;
    else if (seg.risk_score <= RISK_THRESHOLDS.MEDIUM_MAX) medCount++;
    else highCount++;
  });

  const lowPct = Math.round((lowCount / total) * 100);
  const medPct = Math.round((medCount / total) * 100);
  const highPct = Math.round((highCount / total) * 100);

  return (
    <div className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs space-y-3">
      <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <span>📊</span> Risk Level Distribution
          </h3>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Segment composition for {route.route_id.toUpperCase()} ({total} total segments)
          </p>
        </div>
        <span className="text-[11px] font-mono font-bold text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
          Score: {route.risk_score}/100
        </span>
      </div>

      {/* Multi-segment distribution stacked bar */}
      <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden flex shadow-inner">
        {lowPct > 0 && (
          <div
            className="h-full bg-emerald-500 transition-all duration-500"
            style={{ width: `${lowPct}%` }}
            title={`Low Risk: ${lowCount} segments (${lowPct}%)`}
          />
        )}
        {medPct > 0 && (
          <div
            className="h-full bg-amber-500 transition-all duration-500"
            style={{ width: `${medPct}%` }}
            title={`Medium Risk: ${medCount} segments (${medPct}%)`}
          />
        )}
        {highPct > 0 && (
          <div
            className="h-full bg-rose-500 transition-all duration-500"
            style={{ width: `${highPct}%` }}
            title={`High Risk: ${highCount} segments (${highPct}%)`}
          />
        )}
      </div>

      {/* Breakdown Metrics */}
      <div className="grid grid-cols-3 gap-2 pt-1 text-center text-xs">
        <div className="p-2 rounded-lg bg-emerald-50/60 border border-emerald-100">
          <span className="text-[10px] text-emerald-800 font-semibold block">Low (0–33)</span>
          <span className="text-sm font-bold font-mono text-emerald-700">{lowCount} segs</span>
          <span className="text-[10px] text-emerald-600 block">{lowPct}%</span>
        </div>

        <div className="p-2 rounded-lg bg-amber-50/60 border border-amber-100">
          <span className="text-[10px] text-amber-800 font-semibold block">Medium (34–66)</span>
          <span className="text-sm font-bold font-mono text-amber-700">{medCount} segs</span>
          <span className="text-[10px] text-amber-600 block">{medPct}%</span>
        </div>

        <div className="p-2 rounded-lg bg-rose-50/60 border border-rose-100">
          <span className="text-[10px] text-rose-800 font-semibold block">High (67–100)</span>
          <span className="text-sm font-bold font-mono text-rose-700">{highCount} segs</span>
          <span className="text-[10px] text-rose-600 block">{highPct}%</span>
        </div>
      </div>
    </div>
  );
}
