"use client";

import React from "react";
import { HealthResponse, MockScenario } from "../lib/types";
import SystemHealthBadge from "./SystemHealthBadge";

interface HeaderProps {
  health: HealthResponse | null;
  isHealthLoading: boolean;
  onRefreshHealth: () => void;
  isMockMode: boolean;
  onToggleMockMode: (val: boolean) => void;
  mockScenario: MockScenario;
  onSelectMockScenario: (scenario: MockScenario) => void;
}

export default function Header({
  health,
  isHealthLoading,
  onRefreshHealth,
  isMockMode,
  onToggleMockMode,
  mockScenario,
  onSelectMockScenario,
}: HeaderProps) {
  return (
    <header className="w-full bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800 sticky top-0 z-40 backdrop-blur-md bg-white/90 dark:bg-zinc-900/90 shadow-2xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-4">
        {/* Brand and Project Info */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-600 to-emerald-500 flex items-center justify-center text-white font-black text-lg shadow-sm">
            N
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-zinc-900 dark:text-zinc-100 tracking-tight">
                NER-ResQ
              </h1>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700">
                v1.0 MVP
              </span>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Smart Logistics & Accessibility Intelligence • Northeast Region
            </p>
          </div>
        </div>

        {/* Controls: Health Badge + Mock Switch */}
        <div className="flex items-center flex-wrap gap-3">
          {/* Mock Mode Switch */}
          <div className="flex items-center gap-2 bg-zinc-100 dark:bg-zinc-800/80 p-1 rounded-xl border border-zinc-200 dark:border-zinc-700">
            <button
              type="button"
              onClick={() => onToggleMockMode(false)}
              className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-colors ${
                !isMockMode
                  ? "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-2xs"
                  : "text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
              }`}
            >
              Live API
            </button>
            <button
              type="button"
              onClick={() => onToggleMockMode(true)}
              className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-colors ${
                isMockMode
                  ? "bg-sky-600 text-white shadow-2xs"
                  : "text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
              }`}
            >
              Mock Mode
            </button>
          </div>

          {/* Mock Scenario Selector (visible only when in Mock Mode) */}
          {isMockMode && (
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-zinc-400 hidden sm:inline">Scenario:</span>
              <select
                value={mockScenario}
                onChange={(e) =>
                  onSelectMockScenario(e.target.value as MockScenario)
                }
                className="text-xs font-medium px-2 py-1 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 focus:outline-none focus:ring-1 focus:ring-sky-500 shadow-2xs"
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
