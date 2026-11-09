"use client";

import React, { useState } from "react";
import { useApp } from "../../lib/context";
import MapView from "../../components/MapView";
import { MOCK_HAZARD_ZONES } from "../../lib/mockData";
import { RISK_LEVEL_CONFIG } from "../../lib/constants";

export default function RiskZonesPage() {
  const { activeBbox, routes } = useApp();
  const [selectedSeverity, setSelectedSeverity] = useState<string>("all");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedZoneId, setSelectedZoneId] = useState<string>("hzd-001");

  const filteredZones = MOCK_HAZARD_ZONES.filter((z) => {
    if (selectedSeverity !== "all" && z.severity !== selectedSeverity) return false;
    if (selectedCategory !== "all" && z.category !== selectedCategory) return false;
    return true;
  });

  const activeZone =
    filteredZones.find((z) => z.id === selectedZoneId) || filteredZones[0] || MOCK_HAZARD_ZONES[0];

  return (
    <div className="space-y-6">
      {/* Page Title & Provenance Disclosure */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200/80">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <span>⚠️</span> Hazard Risk Zones & Corridor Monitoring
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Geospatial surveillance of landslide vulnerabilities, flash flood culverts, and slope gradients
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] px-2.5 py-1 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono">
            {filteredZones.length} Active Monitored Zones
          </span>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white border border-slate-200/90 rounded-xl p-4 shadow-xs flex flex-wrap items-center justify-between gap-4">
        {/* Severity Filters */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-600">Severity:</span>
          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200">
            {["all", "high", "medium", "low"].map((sev) => (
              <button
                key={sev}
                type="button"
                onClick={() => setSelectedSeverity(sev)}
                className={`px-3 py-1 text-xs font-semibold rounded-md transition-all cursor-pointer capitalize ${
                  selectedSeverity === sev
                    ? "bg-white text-slate-900 shadow-2xs font-bold"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                {sev === "all" ? "All Levels" : `${sev} Risk`}
              </button>
            ))}
          </div>
        </div>

        {/* Category Filters */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-600">Hazard Category:</span>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50 text-slate-800 focus:outline-none focus:ring-1 focus:ring-sky-500 cursor-pointer"
          >
            <option value="all">All Hazard Categories</option>
            <option value="landslide">Landslides & Slope Failure (GSI)</option>
            <option value="heavy_rainfall">Heavy Rainfall Culverts (Hydrology Model)</option>
            <option value="high_winds">High Winds & Ridge Exposure (Terrain)</option>
            <option value="severe_weather">Severe Weather & Flash Inundation</option>
            <option value="steep_slope">Steep Slopes (DEM Topography)</option>
          </select>
        </div>
      </div>

      {/* Conceptual Clarity: Hazard Categories vs Contributing Factors */}
      <div className="p-3.5 rounded-xl bg-sky-50/70 border border-sky-200 text-xs text-sky-900 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-2xs">
        <div className="flex items-start gap-2.5">
          <span className="text-base mt-0.5">ℹ️</span>
          <div>
            <p className="font-bold text-slate-900">
              Hazard Categories vs. Contributing Risk Factors
            </p>
            <p className="text-[11px] text-slate-600 leading-relaxed mt-0.5">
              <strong>Hazard Categories</strong> identify physical spatial vulnerability zones along the NH-6 corridor. <strong>Contributing Risk Factors</strong> represent the dynamic empirical variables (e.g. slope gradient, rainfall precipitation rate, road classification) evaluated by the deterministic baseline risk model.
            </p>
          </div>
        </div>
        <span className="text-[10px] font-mono font-semibold px-2 py-1 rounded bg-white border border-sky-200 text-sky-800 shrink-0">
          Baseline Engine
        </span>
      </div>

      {/* Main Grid: Hazard List & Interactive Map */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column (5 Cols): Monitored Hazard Zone Cards */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Corridor Hazard Inventory ({filteredZones.length})
            </h2>
            <span className="text-[10px] text-slate-400 font-medium">Click card to inspect</span>
          </div>

          <div className="space-y-3">
            {filteredZones.map((zone) => {
              const isSelected = zone.id === activeZone?.id;
              const levelCfg =
                zone.severity === "high" || zone.severity === "critical"
                  ? RISK_LEVEL_CONFIG.high
                  : zone.severity === "medium"
                  ? RISK_LEVEL_CONFIG.medium
                  : RISK_LEVEL_CONFIG.low;

              return (
                <div
                  key={zone.id}
                  onClick={() => setSelectedZoneId(zone.id)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer relative ${
                    isSelected
                      ? "border-sky-600 bg-sky-50/60 ring-2 ring-sky-500/40 shadow-xs"
                      : "border-slate-200 bg-white hover:border-slate-300 shadow-xs"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-slate-900">{zone.name}</span>
                        <span
                          className={`text-[9px] uppercase font-bold px-1.5 py-0.2 rounded border ${levelCfg.badgeBg.replace(/dark:[^\s]+/g, "")} ${levelCfg.badgeText.replace(/dark:[^\s]+/g, "")} ${levelCfg.badgeBorder.replace(/dark:[^\s]+/g, "")}`}
                        >
                          {zone.severity} Risk
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-1 font-mono">
                        {zone.corridor_km} • Coordinates: [{zone.coordinates[1].toFixed(3)},{" "}
                        {zone.coordinates[0].toFixed(3)}]
                      </p>
                    </div>

                    <div className="text-right">
                      <span
                        className="text-lg font-black font-mono leading-none"
                        style={{ color: levelCfg.colorHex }}
                      >
                        {zone.risk_score}
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono block">/100</span>
                    </div>
                  </div>

                  <p className="text-xs text-slate-600 mt-2 leading-relaxed">{zone.description}</p>

                  {/* Contributing Risk Factors Breakdown */}
                  {zone.contributing_factors && zone.contributing_factors.length > 0 && (
                    <div className="mt-2.5 pt-2 border-t border-slate-100/80 space-y-1">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                        Contributing Risk Factors:
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {zone.contributing_factors.map((cf, idx) => (
                          <span
                            key={idx}
                            className="text-[10px] px-2 py-0.5 rounded bg-slate-50 border border-slate-200 text-slate-700 font-medium"
                          >
                            <strong className="text-slate-800">{cf.factor}:</strong> {cf.value}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                    <span className="truncate max-w-[210px] font-mono text-[10px]">
                      {zone.data_source}
                    </span>
                    <div className="flex items-center gap-1.5">
                      {zone.data_fidelity && (
                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                          {zone.data_fidelity}
                        </span>
                      )}
                      <span className="font-semibold text-slate-700">{zone.active_status}</span>
                    </div>
                  </div>
                </div>
              );
            })}

            {filteredZones.length === 0 && (
              <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-xs text-slate-500">
                No hazard zones match the selected filters.
              </div>
            )}
          </div>

          {/* Research Data Integrity Notice */}
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 space-y-1.5">
            <span className="font-bold text-slate-800 flex items-center gap-1.5">
              <span>🔬</span> Data Provenance & Telemetry Notice:
            </span>
            <p className="text-[11px] leading-relaxed">
              Historical landslide points are aligned with the Geological Survey of India (GSI) National Landslide Susceptibility Mapping (NLSM) inventory for Assam and Meghalaya. Road culvert drainage, wind shear, and thunderstorm models represent calculated GIS baselines and illustrative engineering profiles along NH-6.
            </p>
            <p className="text-[11px] text-slate-500 italic leading-relaxed pt-1 border-t border-slate-200/60">
              Notice: Certified real-time Doppler radar observations are unavailable. Weather hazard parameters and precipitation trigger levels represent simulated baseline thresholds and seasonal agro-met feeds.
            </p>
          </div>
        </div>

        {/* Right Column (7 Cols): Interactive GIS Risk Map */}
        <div className="lg:col-span-7 space-y-4 lg:sticky lg:top-20">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <span>🗺️</span> Spatial Risk Layer Visualization
            </h2>
            <span className="text-[11px] text-slate-400 font-medium">
              Click hazard pin on map to inspect details
            </span>
          </div>

          <div className="h-[600px] lg:h-[720px] w-full rounded-xl overflow-hidden shadow-xs border border-slate-200">
            <MapView
              mode="risk-zones"
              routes={routes}
              coverageBbox={activeBbox}
              hazardSeverityFilter={selectedSeverity}
              hazardCategoryFilter={selectedCategory}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
