"use client";

import React, { useState, useEffect } from "react";
import { HealthResponse, MockScenario } from "../lib/types";
import { useApp } from "../lib/context";
import { CORRIDOR_OPTIONS } from "../lib/constants";
import SystemHealthBadge from "./SystemHealthBadge";

interface HeaderProps {
  health?: HealthResponse | null;
  isHealthLoading?: boolean;
  onRefreshHealth?: () => void;
  isMockMode?: boolean;
  onToggleMockMode?: (val: boolean) => void;
  mockScenario?: MockScenario;
  onSelectMockScenario?: (scenario: MockScenario) => void;
  onOpenMobileSidebar?: () => void;
  activeAlertCount?: number;
  selectedCorridor?: string;
  onSelectCorridor?: (corridor: string) => void;
}

export { CORRIDOR_OPTIONS } from "../lib/constants";

export default function Header(props: HeaderProps) {
  const context = useApp();

  // Use props if explicitly passed, otherwise use context
  const health = props.health !== undefined ? props.health : context.health;
  const isHealthLoading =
    props.isHealthLoading !== undefined ? props.isHealthLoading : context.isHealthLoading;
  const onRefreshHealth = props.onRefreshHealth || context.refreshHealth;
  const isMockMode = props.isMockMode !== undefined ? props.isMockMode : context.isMockMode;
  const onToggleMockMode =
    props.onToggleMockMode || ((val: boolean) => context.setIsMockMode(val));
  const mockScenario =
    props.mockScenario !== undefined ? props.mockScenario : context.mockScenario;
  const onSelectMockScenario =
    props.onSelectMockScenario || ((sc: MockScenario) => context.setMockScenario(sc));
  const onOpenMobileSidebar =
    props.onOpenMobileSidebar || (() => context.setIsMobileSidebarOpen(true));
  const activeAlertCount =
    props.activeAlertCount !== undefined
      ? props.activeAlertCount
      : context.summary?.active_alerts_count || 3;
  const selectedCorridor =
    props.selectedCorridor !== undefined ? props.selectedCorridor : context.selectedCorridor;
  const onSelectCorridor =
    props.onSelectCorridor || ((c: string) => context.setSelectedCorridor(c));

  const [currentDateTime, setCurrentDateTime] = useState<string>("");
  const [showNotificationMenu, setShowNotificationMenu] = useState(false);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const datePart = now.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      });
      const timePart = now.toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      });
      setCurrentDateTime(`${datePart}, ${timePart} IST`);
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="w-full bg-white border-b border-slate-200/90 sticky top-0 z-40 shadow-xs">
      <div className="w-full px-4 sm:px-6 py-2.5 flex flex-wrap items-center justify-between gap-3">
        {/* Left Section: Mobile Menu + Regional Location Selector */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onOpenMobileSidebar}
            className="lg:hidden p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 cursor-pointer"
            aria-label="Open sidebar navigation"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>

          {/* Regional Corridor Selector */}
          <div className="flex items-center gap-2">
            <span className="text-slate-400 text-sm hidden sm:inline">📍</span>
            <div className="relative">
              <select
                value={selectedCorridor}
                onChange={(e) => onSelectCorridor(e.target.value)}
                className="text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-slate-200 bg-slate-50 text-slate-800 hover:border-slate-300 focus:outline-none focus:ring-1 focus:ring-sky-500 cursor-pointer pr-7 appearance-none"
              >
                {CORRIDOR_OPTIONS.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} {c.isSupported ? "★ (Active)" : "(Planned)"}
                  </option>
                ))}
              </select>
              <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] text-slate-500 pointer-events-none">
                ▼
              </span>
            </div>
            {CORRIDOR_OPTIONS.find((c) => c.id === selectedCorridor)?.isSupported ? (
              <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200/60 hidden md:inline">
                Active MVP Corridor
              </span>
            ) : (
              <span
                className="text-[10px] font-medium px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200/60 hidden md:inline"
                title="Road routing graph is only modeled for Guwahati–Shillong in this MVP"
              >
                Planned (Not in MVP)
              </span>
            )}
          </div>

          {/* Search bar */}
          <div className="relative hidden xl:block w-64">
            <input
              type="text"
              placeholder="Search corridors, checkpoints..."
              value={context.searchQuery}
              onChange={(e) => context.setSearchQuery(e.target.value)}
              className="w-full text-xs pl-8 pr-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50/70 text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-sky-500 focus:bg-white"
            />
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-slate-400">
              🔍
            </span>
          </div>
        </div>

        {/* Right Section: Time + Notifications + Mode Switch + System Health */}
        <div className="flex items-center flex-wrap gap-2.5 sm:gap-3">
          {/* Live IST Date/Time */}
          {currentDateTime && (
            <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-100/80 text-[11px] font-mono text-slate-600 border border-slate-200/60">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-500"></span>
              <span>{currentDateTime}</span>
            </div>
          )}

          {/* Notifications Center */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowNotificationMenu(!showNotificationMenu)}
              className="p-1.5 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 relative transition-colors cursor-pointer"
              aria-label="View notifications"
              title="Corridor hazard notifications"
            >
              <span className="text-sm">🔔</span>
              {activeAlertCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-rose-500 text-white text-[9px] font-bold flex items-center justify-center">
                  {activeAlertCount}
                </span>
              )}
            </button>

            {/* Notification Dropdown */}
            {showNotificationMenu && (
              <div className="absolute right-0 top-10 w-80 p-3 bg-white border border-slate-200 rounded-xl shadow-lg z-50 text-xs space-y-2">
                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <span className="font-bold text-slate-800">Operational Alerts</span>
                  <span className="text-[10px] font-medium text-slate-500">
                    Northeast Dispatch Grid
                  </span>
                </div>
                <div className="space-y-2 max-h-56 overflow-y-auto">
                  <div className="p-2 rounded-lg bg-amber-50 border border-amber-200/80 text-amber-900">
                    <div className="flex items-center justify-between font-semibold">
                      <span>Landslide Risk Advisory</span>
                      <span className="text-[10px] text-amber-600">10m ago</span>
                    </div>
                    <p className="text-[11px] text-amber-800 mt-0.5">
                      Monsoon warning active along NH-6 Byrnihat-Nongpoh stretch.
                    </p>
                  </div>
                  <div className="p-2 rounded-lg bg-sky-50 border border-sky-200/80 text-sky-900">
                    <div className="flex items-center justify-between font-semibold">
                      <span>Corridor Clearance</span>
                      <span className="text-[10px] text-sky-600">35m ago</span>
                    </div>
                    <p className="text-[11px] text-sky-800 mt-0.5">
                      GS Road Khanapara checkpoint fully operational for heavy vehicles.
                    </p>
                  </div>
                </div>
                <div className="pt-2 border-t border-slate-100 text-center">
                  <button
                    type="button"
                    onClick={() => setShowNotificationMenu(false)}
                    className="text-[11px] text-slate-500 hover:text-slate-800 font-medium cursor-pointer"
                  >
                    Close
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Mode Switch: Live API vs Mock Mode */}
          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200">
            <button
              type="button"
              onClick={() => onToggleMockMode(false)}
              className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all cursor-pointer ${
                !isMockMode
                  ? "bg-white text-slate-900 shadow-2xs font-bold"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              Live API
            </button>
            <button
              type="button"
              onClick={() => onToggleMockMode(true)}
              className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all cursor-pointer ${
                isMockMode
                  ? "bg-sky-600 text-white shadow-2xs font-bold"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              Mock Mode
            </button>
          </div>

          {/* Mock Scenario Selector (visible only when in Mock Mode) */}
          {isMockMode && (
            <div className="flex items-center gap-1.5 text-xs">
              <select
                value={mockScenario}
                onChange={(e) =>
                  onSelectMockScenario(e.target.value as MockScenario)
                }
                className="text-xs font-medium px-2 py-1 rounded-lg border border-slate-200 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-sky-500 shadow-2xs cursor-pointer"
              >
                <option value="success">Multi-Route Success (2 Candidates)</option>
                <option value="partial_weather">Partial Weather Fallback (Degraded)</option>
                <option value="no_route">404 No Connected Route</option>
                <option value="out_of_coverage">422 Out of Coverage Area</option>
                <option value="dependency_error">503 Dependency Unavailable</option>
              </select>
            </div>
          )}

          {/* System Health Badge */}
          <SystemHealthBadge
            health={health}
            isLoading={isHealthLoading}
            onRefresh={onRefreshHealth}
            isMockMode={isMockMode}
          />
        </div>
      </div>
    </header>
  );
}
