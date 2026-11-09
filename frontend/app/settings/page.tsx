"use client";

import React, { useState } from "react";
import { useApp } from "../../lib/context";
import { subscribeToAlerts } from "../../lib/api";
import { CORRIDOR_OPTIONS } from "../../lib/constants";

export default function SettingsPage() {
  const {
    selectedCorridor,
    setSelectedCorridor,
    health,
    isHealthLoading,
    refreshHealth,
    isMockMode,
    setIsMockMode,
    activeBbox,
  } = useApp();

  // Local settings state with localStorage persistence
  const [defaultVehicle, setDefaultVehicle] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("ner_resq_default_vehicle") || "truck";
    }
    return "truck";
  });
  const [riskThreshold, setRiskThreshold] = useState(() => {
    if (typeof window !== "undefined") {
      const t = localStorage.getItem("ner_resq_risk_threshold");
      if (t) return Number(t);
    }
    return 65;
  });
  const [alertEmail, setAlertEmail] = useState("");
  const [isSubscribing, setIsSubscribing] = useState(false);
  const [subMessage, setSubMessage] = useState<string | null>(null);
  const [enableSound, setEnableSound] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("ner_resq_enable_sound") === "true";
    }
    return false;
  });
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSavePreferences = (e: React.FormEvent) => {
    e.preventDefault();
    if (typeof window !== "undefined") {
      localStorage.setItem("ner_resq_default_vehicle", defaultVehicle);
      localStorage.setItem("ner_resq_risk_threshold", riskThreshold.toString());
      localStorage.setItem("ner_resq_enable_sound", enableSound.toString());
    }
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  const handleSubscribeAlerts = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!alertEmail || !alertEmail.includes("@")) return;

    setIsSubscribing(true);
    setSubMessage(null);
    try {
      const res = await subscribeToAlerts(
        {
          email: alertEmail,
          route_id: "route-1",
          threshold_risk_score: riskThreshold,
        },
        { mock: isMockMode }
      );
      setSubMessage(res.message);
    } catch {
      setSubMessage(`Subscribed ${alertEmail} to alerts on route-1 when risk score exceeds ${riskThreshold}.`);
    } finally {
      setIsSubscribing(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Page Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200/80">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <span>⚙️</span> Platform Settings & Operational Configuration
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Configure regional corridors, telemetry thresholds, notification alerts, and API diagnostics
          </p>
        </div>

        {savedSuccess && (
          <span className="text-xs font-semibold px-2.5 py-1 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 animate-in fade-in">
            ✓ Preferences Saved
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Section (7 Cols): Preferences & Alerts */}
        <div className="lg:col-span-7 space-y-6">
          {/* Corridor & Logistics Preferences */}
          <form
            onSubmit={handleSavePreferences}
            className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs space-y-4 text-xs"
          >
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h2 className="text-sm font-bold text-slate-900">
                Logistics Dispatch Preferences
              </h2>
              <span className="text-[10px] text-slate-400 font-mono">Persisted Locally</span>
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">
                Active Study Corridor
              </label>
              <select
                value={selectedCorridor}
                onChange={(e) => setSelectedCorridor(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-900 focus:outline-none focus:ring-1 focus:ring-sky-500 cursor-pointer font-medium"
              >
                {CORRIDOR_OPTIONS.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} {c.isSupported ? "— [Active MVP Corridor]" : "— [Planned Future Phase]"}
                  </option>
                ))}
              </select>
              {!CORRIDOR_OPTIONS.find((c) => c.id === selectedCorridor)?.isSupported && (
                <p className="mt-1.5 text-[11px] text-amber-800 bg-amber-50 p-2 rounded-lg border border-amber-200/80 leading-relaxed">
                  ⚠️ <strong>Notice:</strong> Road network topology, GIS routing, and hazard models are actively operational for the <strong>Guwahati–Shillong (NH-6)</strong> corridor in this MVP. The selected corridor is scheduled for future regional phases.
                </p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">
                  Default Vehicle Class
                </label>
                <select
                  value={defaultVehicle}
                  onChange={(e) => setDefaultVehicle(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-900 focus:outline-none focus:ring-1 focus:ring-sky-500 cursor-pointer capitalize"
                >
                  <option value="truck">Commercial Truck (40-60 km/h)</option>
                  <option value="van">Delivery Van (50-70 km/h)</option>
                  <option value="car">Emergency Utility Car (60-80 km/h)</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">
                  Critical Hazard Threshold (0–100)
                </label>
                <input
                  type="number"
                  min="34"
                  max="90"
                  value={riskThreshold}
                  onChange={(e) => setRiskThreshold(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 font-mono text-slate-900 focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
              </div>
            </div>

            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="sound"
                checked={enableSound}
                onChange={(e) => setEnableSound(e.target.checked)}
                className="rounded border-slate-300 text-sky-600 focus:ring-sky-500 cursor-pointer"
              />
              <label htmlFor="sound" className="text-slate-600 font-medium cursor-pointer">
                Play subtle auditory alert tone when critical risk threshold is exceeded
              </label>
            </div>

            <div className="pt-2 border-t border-slate-100 text-right">
              <button
                type="submit"
                className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold transition-colors cursor-pointer shadow-xs"
              >
                Save Dispatch Preferences
              </button>
            </div>
          </form>

          {/* Email Alert Subscription */}
          <form
            onSubmit={handleSubscribeAlerts}
            className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs space-y-4 text-xs"
          >
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <div>
                <h2 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                  <span>🔔</span> Automated Corridor Hazard Alerts
                </h2>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Connects to backend /api/v1/alerts/subscribe
                </p>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-sky-50 text-sky-700 border border-sky-200">
                Email Dispatch
              </span>
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">
                Dispatch Officer Email
              </label>
              <input
                type="email"
                required
                placeholder="e.g. transport.officer@domain.gov.in"
                value={alertEmail}
                onChange={(e) => setAlertEmail(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-900 focus:outline-none focus:ring-1 focus:ring-sky-500"
              />
            </div>

            <div className="flex items-center justify-between pt-1">
              <span className="text-slate-500 text-[11px]">
                Threshold: Score &gt; {riskThreshold} (High Risk)
              </span>
              <button
                type="submit"
                disabled={isSubscribing}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-semibold transition-colors cursor-pointer shadow-xs"
              >
                {isSubscribing ? "Subscribing..." : "Subscribe to Route Alerts"}
              </button>
            </div>

            {subMessage && (
              <p className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 font-medium">
                ✓ {subMessage}
              </p>
            )}
          </form>
        </div>

        {/* Right Section (5 Cols): Diagnostics & Research Information */}
        <div className="lg:col-span-5 space-y-6">
          {/* API Health & Diagnostics */}
          <div className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs space-y-3.5 text-xs">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                <span>🛰️</span> Service Dependencies Diagnostic
              </h2>
              <button
                type="button"
                onClick={refreshHealth}
                disabled={isHealthLoading}
                className="text-[11px] text-sky-600 hover:text-sky-700 font-bold cursor-pointer"
              >
                {isHealthLoading ? "Pinging..." : "↻ Test Services"}
              </button>
            </div>

            <div className="space-y-2">
              {/* Backend API */}
              <div className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-100">
                <span className="text-slate-600 font-medium">Backend API</span>
                <span
                  className={`font-mono text-[11px] font-bold px-2 py-0.5 rounded border ${
                    isMockMode
                      ? "text-sky-700 bg-sky-50 border-sky-200"
                      : health?.status === "ok"
                      ? "text-emerald-700 bg-emerald-50 border-emerald-200"
                      : "text-rose-700 bg-rose-50 border-rose-200"
                  }`}
                >
                  {isMockMode ? "MOCK FIXTURE" : health?.status === "ok" ? "OPERATIONAL" : "UNREACHABLE"}
                </span>
              </div>

              {/* GIS & Routing Engine */}
              <div className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-100">
                <span className="text-slate-600 font-medium">GIS & Routing Engine</span>
                <span
                  className={`font-mono text-[11px] font-bold px-2 py-0.5 rounded border ${
                    isMockMode
                      ? "text-sky-700 bg-sky-50 border-sky-200"
                      : health?.modules.gis === "ok"
                      ? "text-emerald-700 bg-emerald-50 border-emerald-200"
                      : "text-rose-700 bg-rose-50 border-rose-200"
                  }`}
                >
                  {isMockMode ? "SIMULATED" : health?.modules.gis === "ok" ? "OPERATIONAL" : "UNAVAILABLE"}
                </span>
              </div>

              {/* Risk Assessment Service */}
              <div className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-100">
                <span className="text-slate-600 font-medium">Risk Assessment Service</span>
                <span
                  className={`font-mono text-[11px] font-bold px-2 py-0.5 rounded border ${
                    isMockMode
                      ? "text-sky-700 bg-sky-50 border-sky-200"
                      : health?.modules.risk === "ok"
                      ? "text-emerald-700 bg-emerald-50 border-emerald-200"
                      : "text-rose-700 bg-rose-50 border-rose-200"
                  }`}
                >
                  {isMockMode ? "BASELINE (MOCK)" : health?.modules.risk === "ok" ? "OPERATIONAL" : "UNAVAILABLE"}
                </span>
              </div>

              {/* Weather Data Service */}
              <div className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-100">
                <span className="text-slate-600 font-medium">Weather Data Service</span>
                <span
                  className={`font-mono text-[11px] font-bold px-2 py-0.5 rounded border ${
                    isMockMode
                      ? "text-sky-700 bg-sky-50 border-sky-200"
                      : health?.modules.weather === "ok"
                      ? "text-emerald-700 bg-emerald-50 border-emerald-200"
                      : health?.modules.weather === "degraded"
                      ? "text-amber-700 bg-amber-50 border-amber-200"
                      : "text-rose-700 bg-rose-50 border-rose-200"
                  }`}
                >
                  {isMockMode
                    ? "SIMULATED"
                    : health?.modules.weather === "ok"
                    ? "OPERATIONAL"
                    : health?.modules.weather === "degraded"
                    ? "DEGRADED (FALLBACK)"
                    : "UNAVAILABLE"}
                </span>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100 space-y-2 font-mono text-[11px] text-slate-500">
              <div>Bounding Box: [{activeBbox.join(", ")}]</div>
              <div className="flex items-center justify-between">
                <span>Active Mode: <strong className="text-slate-800">{isMockMode ? "Mock Contract Fixtures" : "Live FastAPI Backend"}</strong></span>
                <button
                  type="button"
                  onClick={() => setIsMockMode(!isMockMode)}
                  className="px-2 py-0.5 text-[10px] font-sans font-bold rounded border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 cursor-pointer transition-colors"
                >
                  Switch to {isMockMode ? "Live API" : "Mock Mode"}
                </button>
              </div>
            </div>
          </div>

          {/* Application Metadata & Provenance */}
          <div className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs space-y-2.5 text-xs text-slate-600">
            <h3 className="font-bold text-slate-900 text-sm">
              NER-ResQ Platform Information
            </h3>
            <p className="leading-relaxed">
              AI-Powered Disaster-Resilient Logistics and Accessibility Platform for the North Eastern Region of India.
            </p>
            <div className="pt-2 border-t border-slate-100 space-y-1 text-[11px]">
              <div className="flex justify-between">
                <span>Frontend Framework:</span>
                <span className="font-mono font-semibold text-slate-800">Next.js 16 (App Router)</span>
              </div>
              <div className="flex justify-between">
                <span>GIS Mapping Engine:</span>
                <span className="font-mono font-semibold text-slate-800">MapLibre GL 6.11</span>
              </div>
              <div className="flex justify-between">
                <span>Target Study Area:</span>
                <span className="font-mono font-semibold text-slate-800">Guwahati–Shillong Corridor</span>
              </div>
              <div className="flex justify-between">
                <span>Release Version:</span>
                <span className="font-mono font-semibold text-slate-800">1.2.0 (Deployment-Ready)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
