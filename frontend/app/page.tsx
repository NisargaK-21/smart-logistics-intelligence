"use client";

import React from "react";
import Link from "next/link";
import { useApp } from "../lib/context";
import DashboardMetrics from "../components/DashboardMetrics";
import ErrorBanner from "../components/ErrorBanner";
import MapView from "../components/MapView";
import RiskDistribution from "../components/RiskDistribution";
import WeatherTerrainOverview from "../components/WeatherTerrainOverview";
import RecentAlerts from "../components/RecentAlerts";

export default function DashboardPage() {
  const {
    summary,
    isSummaryLoading,
    error,
    setError,
    routes,
    recommendedRouteId,
    selectedRouteId,
    setSelectedRouteId,
    origin,
    destination,
    activeBbox,
    activeRoute,
    health,
    isMockMode,
    vehicles,
    planCurrentRoutes,
    isPlanningLoading,
  } = useApp();

  return (
    <div className="space-y-6">
      {/* Page Title & Operational Status Strip */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200/80">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <span>📊</span> Operational Intelligence Overview
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time disaster resilience & logistics telemetry for the Northeast Region of India
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/routes"
            className="px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 active:bg-sky-700 text-white text-xs font-semibold shadow-xs flex items-center gap-1.5 cursor-pointer transition-colors"
          >
            <span>⚡</span>
            <span>Plan New Route</span>
          </Link>
          <Link
            href="/risk-zones"
            className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-2xs flex items-center gap-1.5 cursor-pointer transition-colors"
          >
            <span>⚠️</span>
            <span>Risk Zones</span>
          </Link>
        </div>
      </div>

      {/* Global Error Banner if any */}
      <ErrorBanner
        error={error as Error | null}
        onDismiss={() => setError(null)}
        onRetry={planCurrentRoutes}
      />

      {/* Module 3: KPI Metrics Cards */}
      <DashboardMetrics summary={summary} isLoading={isSummaryLoading} />

      {/* Main Balanced Dashboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Section (7 Cols): Interactive Map Overview */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <span>🗺️</span> GIS Operational Map (Guwahati–Shillong NH-6)
            </h2>
            <span className="text-[11px] text-slate-400 font-mono">
              Live & Monitored Layers
            </span>
          </div>

          <div className="h-[520px] w-full rounded-xl overflow-hidden shadow-xs border border-slate-200">
            <MapView
              mode="overview"
              routes={routes}
              recommendedRouteId={recommendedRouteId}
              selectedRouteId={selectedRouteId}
              onSelectRoute={setSelectedRouteId}
              origin={origin}
              destination={destination}
              coverageBbox={activeBbox}
              vehicles={vehicles}
            />
          </div>
        </div>

        {/* Right Section (5 Cols): Corridor Telemetry & Route Quick Status */}
        <div className="lg:col-span-5 space-y-6">
          {/* Quick Route Status Card */}
          <div className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs space-y-3">
            <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                  <span>🛣️</span> Monitored Corridor Routes
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Active GIS road candidates evaluated for hazard exposure
                </p>
              </div>
              <Link
                href="/routes"
                className="text-xs text-sky-600 hover:text-sky-700 font-bold cursor-pointer"
              >
                Full Workspace →
              </Link>
            </div>

            {routes.length > 0 ? (
              <div className="space-y-2.5">
                <div className="p-3 rounded-lg bg-sky-50/70 border border-sky-200 text-xs text-sky-900">
                  <div className="flex items-center justify-between font-bold">
                    <span>Recommended Route ({recommendedRouteId.toUpperCase()})</span>
                    <span className="font-mono text-sky-700 font-black">
                      Score: {activeRoute?.risk_score}/100
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600 mt-1">
                    Distance: {activeRoute?.distance_km.toFixed(1)} km • Duration:{" "}
                    {Math.round(activeRoute?.estimated_duration_minutes || 0)} min • Quality:{" "}
                    <span className="capitalize font-semibold text-slate-800">
                      {activeRoute?.data_quality}
                    </span>
                  </p>
                </div>

                {activeRoute && <RiskDistribution route={activeRoute} />}
              </div>
            ) : (
              <div className="py-8 text-center text-xs text-slate-500 space-y-2">
                <span className="text-2xl block">📍</span>
                <p className="font-medium text-slate-700">No active route planned in this session</p>
                <p className="text-[11px] text-slate-400">
                  Calculate safer transit routes taking slope, rainfall, and historical landslide factors into account.
                </p>
                <div className="pt-2">
                  <button
                    type="button"
                    onClick={planCurrentRoutes}
                    disabled={isPlanningLoading}
                    className="px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold text-xs transition-colors cursor-pointer"
                  >
                    {isPlanningLoading ? "Calculating..." : "Evaluate Default Corridor Route"}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Weather & Topography Overview */}
          <WeatherTerrainOverview health={health} isMockMode={isMockMode} />
        </div>
      </div>

      {/* Bottom Row: Recent Alerts & Live Field Activity Stream */}
      <div className="pt-2">
        <RecentAlerts summary={summary} />
      </div>
    </div>
  );
}
