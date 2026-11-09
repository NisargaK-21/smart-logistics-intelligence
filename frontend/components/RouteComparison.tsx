"use client";

import React from "react";
import { Route } from "../lib/types";
import { RISK_LEVEL_CONFIG } from "../lib/constants";

interface RouteComparisonProps {
  routes: Route[];
  recommendedRouteId: string;
  selectedRouteId: string;
  onSelectRoute: (routeId: string) => void;
}

export default function RouteComparison({
  routes,
  recommendedRouteId,
  selectedRouteId,
  onSelectRoute,
}: RouteComparisonProps) {
  if (routes.length < 2) return null;

  // Calculate worst segment risk for each route
  const getWorstSegment = (route: Route) => {
    if (!route.segments || route.segments.length === 0) return 0;
    return Math.max(...route.segments.map((s) => s.risk_score));
  };

  const recRoute = routes.find((r) => r.route_id === recommendedRouteId) || routes[0];
  const otherRoutes = routes.filter((r) => r.route_id !== recRoute.route_id);

  return (
    <div className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs space-y-3.5">
      <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <span>⚖️</span> Route Comparison Matrix
          </h3>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Comparative safety vs travel time trade-offs across candidates
          </p>
        </div>
        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-sky-50 text-sky-700 border border-sky-200/60">
          {routes.length} Candidates Evaluated
        </span>
      </div>

      {/* Safety Delta Highlight */}
      {otherRoutes.length > 0 && (
        <div className="p-3 rounded-lg bg-sky-50/80 border border-sky-200 text-xs text-sky-900 flex items-start gap-2">
          <span className="text-base mt-0.5">💡</span>
          <div>
            <span className="font-bold">Recommendation Analysis:</span>
            <p className="text-[11px] text-sky-800 mt-0.5 leading-relaxed">
              <span className="font-semibold">{recRoute.route_id.toUpperCase()}</span> has a risk score of{" "}
              <span className="font-bold font-mono">{recRoute.risk_score}</span> vs{" "}
              <span className="font-semibold">{otherRoutes[0].route_id.toUpperCase()}</span> ({otherRoutes[0].risk_score}).{" "}
              {otherRoutes[0].risk_score > recRoute.risk_score
                ? `Route ${recRoute.route_id.toUpperCase()} reduces hazard risk by ${otherRoutes[0].risk_score - recRoute.risk_score} points.`
                : "Provides the safest balance across road classifications."}
            </p>
          </div>
        </div>
      )}

      {/* Comparison Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-100 text-slate-500 font-semibold text-[11px]">
              <th className="py-2 pr-3">Route ID</th>
              <th className="py-2 px-3">Distance</th>
              <th className="py-2 px-3">Est. Duration</th>
              <th className="py-2 px-3">Risk Score</th>
              <th className="py-2 px-3">Worst Segment</th>
              <th className="py-2 pl-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {routes.map((route) => {
              const isRec = route.route_id === recommendedRouteId;
              const isSel = route.route_id === (selectedRouteId || recommendedRouteId);
              const levelCfg = RISK_LEVEL_CONFIG[route.risk_level];
              const worstSeg = getWorstSegment(route);

              return (
                <tr
                  key={route.route_id}
                  className={`hover:bg-slate-50/80 transition-colors ${
                    isSel ? "bg-sky-50/50 font-semibold" : ""
                  }`}
                >
                  <td className="py-2.5 pr-3">
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono font-bold text-slate-800">
                        {route.route_id.toUpperCase()}
                      </span>
                      {isRec && (
                        <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-sky-600 text-white">
                          ★ Best
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-slate-700">
                    {route.distance_km.toFixed(1)} km
                  </td>
                  <td className="py-2.5 px-3 text-slate-700">
                    {Math.round(route.estimated_duration_minutes)} min
                  </td>
                  <td className="py-2.5 px-3">
                    <span
                      className="font-mono font-bold"
                      style={{ color: levelCfg.colorHex }}
                    >
                      {route.risk_score}
                    </span>
                    <span className="text-[10px] text-slate-400">/100</span>
                  </td>
                  <td className="py-2.5 px-3 text-slate-600 font-mono">
                    {worstSeg}/100
                  </td>
                  <td className="py-2.5 pl-3 text-right">
                    <button
                      type="button"
                      onClick={() => onSelectRoute(route.route_id)}
                      className={`text-[11px] px-2.5 py-1 rounded font-semibold transition-all cursor-pointer ${
                        isSel
                          ? "bg-sky-600 text-white shadow-2xs"
                          : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                      }`}
                    >
                      {isSel ? "Selected" : "Select"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
