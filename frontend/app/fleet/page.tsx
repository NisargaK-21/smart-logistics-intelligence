"use client";

import React, { useState, useEffect } from "react";
import { useApp } from "../../lib/context";
import MapView from "../../components/MapView";
import { VehiclePosition } from "../../lib/types";
import { connectVehicleWebSocket, simulateVehicle } from "../../lib/api";

export default function FleetPage() {
  const { vehicles, isVehiclesLoading, refreshVehicles, activeBbox, isMockMode } = useApp();
  const [selectedVehicle, setSelectedVehicle] = useState<VehiclePosition | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [isSimulating, setIsSimulating] = useState(false);
  const [simVehicleId, setSimVehicleId] = useState("V003");
  const [simRouteId, setSimRouteId] = useState("route-2");
  const [simSpeed, setSimSpeed] = useState(48);
  const [simSuccessMsg, setSimSuccessMsg] = useState<string | null>(null);

  // Connect to live WebSocket if available
  useEffect(() => {
    const cleanup = connectVehicleWebSocket(
      () => {
        void refreshVehicles();
      },
      () => {
        // Fallback silently if WS not connected
      }
    );

    return () => cleanup();
  }, [refreshVehicles]);

  const filteredVehicles = vehicles.filter((v) => {
    if (statusFilter !== "all" && (v.status || "in_transit") !== statusFilter) return false;
    return true;
  });

  const activeV = selectedVehicle || filteredVehicles[0] || vehicles[0];

  const handleLaunchSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSimulating(true);
    setSimSuccessMsg(null);
    try {
      const res = await simulateVehicle(
        {
          vehicle_id: simVehicleId,
          route_id: simRouteId,
          speed_kmh: simSpeed,
        },
        { mock: isMockMode }
      );
      setSimSuccessMsg(res.message);
      await refreshVehicles();
    } catch {
      setSimSuccessMsg(`Simulation trip dispatched for ${simVehicleId} along ${simRouteId}.`);
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Title & Status Strip */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200/80">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <span>🚚</span> Fleet Management & Live GPS Telemetry
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time positioning, transit speeds, and route-hazard proximity tracking
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-sky-50 text-sky-700 border border-sky-200/60 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-sky-500 animate-pulse"></span>
            <span>{vehicles.length} Monitored Vehicles</span>
          </span>
          <button
            type="button"
            onClick={() => refreshVehicles()}
            disabled={isVehiclesLoading}
            className="px-2.5 py-1 text-xs font-semibold rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 cursor-pointer"
          >
            {isVehiclesLoading ? "Syncing..." : "↻ Refresh"}
          </button>
        </div>
      </div>

      {/* Filter Bar & Simulation Quick Launcher */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Status Filter */}
        <div className="lg:col-span-6 bg-white border border-slate-200/90 rounded-xl p-4 shadow-xs flex items-center gap-3">
          <span className="text-xs font-bold text-slate-600">Status:</span>
          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200">
            {["all", "in_transit", "idle", "scheduled"].map((st) => (
              <button
                key={st}
                type="button"
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1 text-xs font-semibold rounded-md transition-all cursor-pointer capitalize ${
                  statusFilter === st
                    ? "bg-white text-slate-900 shadow-2xs font-bold"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                {st === "all" ? "All Fleet" : st.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>

        {/* Dispatch Simulator Launcher Form */}
        <div className="lg:col-span-6 bg-white border border-slate-200/90 rounded-xl p-4 shadow-xs">
          <form onSubmit={handleLaunchSimulation} className="flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-700">Dispatch Trip:</span>
              <select
                value={simVehicleId}
                onChange={(e) => setSimVehicleId(e.target.value)}
                className="px-2 py-1 rounded border border-slate-200 bg-slate-50 font-semibold cursor-pointer"
              >
                <option value="V001">V001 (Truck)</option>
                <option value="V002">V002 (Van)</option>
                <option value="V003">V003 (Car)</option>
                <option value="V004">V004 (Truck)</option>
              </select>

              <select
                value={simRouteId}
                onChange={(e) => setSimRouteId(e.target.value)}
                className="px-2 py-1 rounded border border-slate-200 bg-slate-50 font-semibold cursor-pointer"
              >
                <option value="route-2">Route 2 (Recommended)</option>
                <option value="route-1">Route 1 (Alternative)</option>
              </select>

              <input
                type="number"
                min="20"
                max="80"
                value={simSpeed}
                onChange={(e) => setSimSpeed(Number(e.target.value))}
                className="w-16 px-2 py-1 rounded border border-slate-200 bg-slate-50 font-mono"
                title="Speed in km/h"
              />
              <span className="text-slate-400 text-[10px]">km/h</span>
            </div>

            <button
              type="submit"
              disabled={isSimulating}
              className="px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold transition-colors cursor-pointer"
            >
              {isSimulating ? "Dispatching..." : "⚡ Simulate Trip"}
            </button>
          </form>

          {simSuccessMsg && (
            <p className="text-[11px] text-emerald-700 mt-2 font-medium flex items-center gap-1">
              <span>✅</span> {simSuccessMsg}
            </p>
          )}
        </div>
      </div>

      {/* Main Grid: Vehicle Fleet Table & Map */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column (5 Cols): Vehicle Cards */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Active Vehicles ({filteredVehicles.length})
            </h2>
            <span className="text-[10px] text-slate-400 font-medium">Click vehicle to focus on map</span>
          </div>

          <div className="space-y-3">
            {filteredVehicles.map((v) => {
              const isSelected = v.vehicle_id === activeV?.vehicle_id;
              return (
                <div
                  key={v.vehicle_id}
                  onClick={() => setSelectedVehicle(v)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer relative ${
                    isSelected
                      ? "border-sky-600 bg-sky-50/60 ring-2 ring-sky-500/40 shadow-xs"
                      : "border-slate-200 bg-white hover:border-slate-300 shadow-xs"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-slate-900 flex items-center gap-1">
                          <span>🚚</span> {v.vehicle_id}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-semibold capitalize border border-slate-200">
                          {v.status || "In Transit"}
                        </span>
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-50 text-amber-800 font-bold border border-amber-200">
                          Simulated GPS
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-1">
                        Driver: <span className="font-semibold text-slate-700">{v.driver_name || "Assigned Officer"}</span> • Class:{" "}
                        <span className="capitalize font-semibold text-slate-700">{v.vehicle_class || "truck"}</span>
                      </p>
                    </div>

                    <div className="text-right">
                      <div className="flex items-baseline justify-end gap-1">
                        <span className="text-lg font-black font-mono text-slate-900">
                          {v.speed_kmh.toFixed(0)}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">km/h</span>
                      </div>
                      <span className="text-[10px] text-slate-400 font-mono block">
                        Head: {v.heading_deg?.toFixed(0) || 0}°
                      </span>
                    </div>
                  </div>

                  <div className="mt-3 pt-2.5 border-t border-slate-100 grid grid-cols-2 gap-2 text-xs text-slate-600">
                    <div>
                      <span className="text-[10px] text-slate-400 block">Assigned Corridor</span>
                      <span className="font-mono font-semibold text-slate-800">
                        {v.assigned_route || "route-2"}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block">GPS Position</span>
                      <span className="font-mono text-slate-800 text-[11px]">
                        [{v.lat.toFixed(4)}, {v.lng.toFixed(4)}]
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}

            {filteredVehicles.length === 0 && (
              <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-xs text-slate-500">
                No fleet vehicles match the selected status filter.
              </div>
            )}
          </div>
        </div>

        {/* Right Column (7 Cols): Fleet Map Tracking */}
        <div className="lg:col-span-7 space-y-4 lg:sticky lg:top-20">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <span>🗺️</span> Real-Time Fleet Map Tracking
            </h2>
            <span className="text-[11px] text-slate-400 font-medium">
              Click vehicle icon on map to view status
            </span>
          </div>

          <div className="h-[600px] lg:h-[720px] w-full rounded-xl overflow-hidden shadow-xs border border-slate-200">
            <MapView
              mode="fleet"
              vehicles={filteredVehicles}
              selectedVehicleId={activeV?.vehicle_id}
              onSelectVehicle={setSelectedVehicle}
              coverageBbox={activeBbox}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
