"use client";

import React, { useState } from "react";
import { RiskSource, Route } from "../lib/types";
import { getRiskColor, getRiskLevel, RISK_LEVEL_CONFIG } from "../lib/constants";

interface RouteDetailsProps {
  route: Route;
  riskSource: RiskSource;
  isRecommended: boolean;
}

export default function RouteDetails({
  route,
  riskSource,
  isRecommended,
}: RouteDetailsProps) {
  const [showSegments, setShowSegments] = useState(false);
  const levelConfig = RISK_LEVEL_CONFIG[route.risk_level];

  // Helper to format factor names into human-readable labels
  const formatFactorName = (name: string) => {
    return name
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <div className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-slate-900">
              Route Details: {route.route_id.toUpperCase()}
            </h3>
            {isRecommended && (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-sky-600 text-white shadow-2xs">
                Recommended
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Distance: <span className="font-semibold text-slate-800">{route.distance_km} km</span> •
            Est. Time: <span className="font-semibold text-slate-800">{Math.round(route.estimated_duration_minutes)} min</span>
          </p>
        </div>

        <div className="text-right">
          <div
            className="text-2xl font-black font-mono leading-none"
            style={{ color: levelConfig.colorHex }}
          >
            {route.risk_score}
          </div>
          <span className="text-[10px] text-slate-400 font-medium">Risk Index</span>
        </div>
      </div>

      {/* Actual Risk Source Banner - Honest Labeling per Rule 1 */}
      <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-xs">
        <div className="flex items-center gap-2 font-semibold text-slate-900">
          <span>🛡️</span>
          <span>
            Risk Calculation Source:{" "}
            {riskSource === "baseline" ? (
              <span className="text-sky-700 font-mono font-bold">
                Deterministic Rules Baseline
              </span>
            ) : (
              <span className="text-purple-700 font-mono font-bold">
                Experimental Model Inference
              </span>
            )}
          </span>
        </div>
        <p className="text-[11px] text-slate-600 mt-1 leading-relaxed">
          {riskSource === "baseline"
            ? "Deterministic risk index calculated from road classification, terrain slope, rainfall hazard thresholds, and historical landslide disruption data. Not an uncalibrated black-box prediction."
            : "Experimental logistic regression/random forest classifier score trained on historical weather risk patterns."}
        </p>
      </div>

      {/* Data Quality Banner */}
      <div
        className={`p-3 rounded-lg border text-xs flex items-start gap-2.5 ${
          route.data_quality === "complete"
            ? "bg-emerald-50/70 border-emerald-200 text-emerald-900"
            : route.data_quality === "partial"
            ? "bg-amber-50/70 border-amber-200 text-amber-900"
            : "bg-rose-50/70 border-rose-200 text-rose-900"
        }`}
      >
        <span className="text-sm mt-0.5">
          {route.data_quality === "complete" ? "✅" : "⚠️"}
        </span>
        <div>
          <span className="font-bold capitalize">
            Data Quality: {route.data_quality}
          </span>
          <p className="text-[11px] opacity-90 mt-0.5 leading-relaxed">
            {route.data_quality === "complete"
              ? "All telemetry, road attributes, and weather data sources are fully verified."
              : route.data_quality === "partial"
              ? "Weather feed was unavailable or degraded during scoring. Risk calculated from road attributes and historical factors."
              : "Telemetry was stale or missing during assessment."}
          </p>
        </div>
      </div>

      {/* Contributing Risk Factors - RAW VALUES preserved */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs font-bold text-slate-800">
          <span>Contributing Risk Factors</span>
          <span className="text-[10px] text-slate-500 font-normal">
            Raw Score Contribution (Points, not %)
          </span>
        </div>

        {route.risk_factors.length === 0 ? (
          <p className="text-xs text-slate-500 italic">No significant risk factors flagged.</p>
        ) : (
          <div className="space-y-2">
            {route.risk_factors.map((factor, idx) => (
              <div
                key={idx}
                className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80"
              >
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="font-semibold text-slate-800">
                    {formatFactorName(factor.name)}
                  </span>
                  <span className="font-mono font-bold text-slate-900">
                    {factor.contribution > 0 ? `+${factor.contribution} pts` : `${factor.contribution} pts`}
                  </span>
                </div>

                {/* Progress bar visualizing relative points scale */}
                <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-amber-500 rounded-full"
                    style={{
                      width: `${Math.min(100, Math.max(5, (factor.contribution / 40) * 100))}%`,
                    }}
                  />
                </div>

                {factor.detail && (
                  <p className="text-[10px] text-slate-500 mt-1 italic">
                    {factor.detail}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Segment Level Inspection */}
      <div className="pt-2 border-t border-slate-100">
        <button
          type="button"
          onClick={() => setShowSegments(!showSegments)}
          className="w-full flex items-center justify-between text-xs font-bold text-slate-700 py-1.5 hover:text-slate-900 cursor-pointer"
        >
          <span>Segment Inspection ({route.segments.length} segments)</span>
          <span className="text-slate-400 font-mono text-[11px]">{showSegments ? "▲ Hide" : "▼ Show"}</span>
        </button>

        {showSegments && (
          <div className="mt-2.5 space-y-1.5 max-h-48 overflow-y-auto pr-1">
            {route.segments.map((seg) => {
              const segLevel = getRiskLevel(seg.risk_score);
              const segColor = getRiskColor(seg.risk_score);
              return (
                <div
                  key={seg.segment_id}
                  className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 border border-slate-200/80 text-xs"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2.5 h-2.5 rounded-full shadow-2xs"
                      style={{ backgroundColor: segColor }}
                    />
                    <span className="font-mono text-slate-700 font-medium">
                      {seg.segment_id}
                    </span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <span className="capitalize text-[11px] text-slate-500 font-medium">
                      {segLevel}
                    </span>
                    <span
                      className="font-mono font-bold"
                      style={{ color: segColor }}
                    >
                      {seg.risk_score}/100
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
