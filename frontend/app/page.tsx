"use client";

import React, { useState, useEffect, useCallback } from "react";
import Header from "../components/Header";
import MapView from "../components/MapView";
import RouteForm from "../components/RouteForm";
import RouteCard from "../components/RouteCard";
import RouteDetails from "../components/RouteDetails";
import DashboardMetrics from "../components/DashboardMetrics";
import ErrorBanner from "../components/ErrorBanner";
import {
  Coordinates,
  CoverageResponse,
  DashboardSummary,
  HealthResponse,
  MockScenario,
  RiskSource,
  Route,
  VehicleType,
} from "../lib/types";
import { getCoverage, getDashboardSummary, getHealth, planRoutes } from "../lib/api";
import { DEFAULT_CORRIDOR_BBOX } from "../lib/constants";

export default function DashboardPage() {
  // Mode & Health state
  const [isMockMode, setIsMockMode] = useState(false);
  const [mockScenario, setMockScenario] = useState<MockScenario>("success");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isHealthLoading, setIsHealthLoading] = useState(false);
  const [coverage, setCoverage] = useState<CoverageResponse | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);

  // Route Planning query state
  // Default verified coordinates from backend tests: Guwahati corridor
  const [origin, setOrigin] = useState<Coordinates | null>({
    lat: 26.1445,
    lng: 91.7362,
  });
  const [destination, setDestination] = useState<Coordinates | null>({
    lat: 26.1801,
    lng: 91.7001,
  });
  const [vehicleType, setVehicleType] = useState<VehicleType>("truck");
  const [departureTime, setDepartureTime] = useState<string>("");
  const [pickingMode, setPickingMode] = useState<"origin" | "destination" | null>(null);

  // Results state
  const [routes, setRoutes] = useState<Route[]>([]);
  const [recommendedRouteId, setRecommendedRouteId] = useState<string>("");
  const [selectedRouteId, setSelectedRouteId] = useState<string>("");
  const [riskSource, setRiskSource] = useState<RiskSource>("baseline");
  const [isPlanningLoading, setIsPlanningLoading] = useState(false);
  const [error, setError] = useState<unknown | null>(null);

  // Fetch telemetry and system health
  const loadSystemStatus = useCallback(async (mock: boolean) => {
    setIsHealthLoading(true);
    setIsSummaryLoading(true);
    try {
      const [hRes, cRes, sRes] = await Promise.allSettled([
        getHealth({ mock }),
        getCoverage({ mock }),
        getDashboardSummary({ mock }),
      ]);

      if (hRes.status === "fulfilled") {
        setHealth(hRes.value);
      } else {
        // If live backend is down, show impaired status
        setHealth({
          status: "impaired",
          modules: { gis: "unavailable", risk: "unavailable", weather: "unavailable" },
        });
      }

      if (cRes.status === "fulfilled") {
        setCoverage(cRes.value);
      }

      if (sRes.status === "fulfilled") {
        setSummary(sRes.value);
      }
    } finally {
      setIsHealthLoading(false);
      setIsSummaryLoading(false);
    }
  }, []);

  // Initial fetch on mount or mode toggle
  useEffect(() => {
    let isSubscribed = true;

    async function fetchInitialStatus() {
      const [hRes, cRes, sRes] = await Promise.allSettled([
        getHealth({ mock: isMockMode }),
        getCoverage({ mock: isMockMode }),
        getDashboardSummary({ mock: isMockMode }),
      ]);

      if (!isSubscribed) return;

      if (hRes.status === "fulfilled") {
        setHealth(hRes.value);
      } else {
        setHealth({
          status: "impaired",
          modules: { gis: "unavailable", risk: "unavailable", weather: "unavailable" },
        });
      }

      if (cRes.status === "fulfilled") {
        setCoverage(cRes.value);
      }

      if (sRes.status === "fulfilled") {
        setSummary(sRes.value);
      }

      setIsHealthLoading(false);
      setIsSummaryLoading(false);
    }

    void fetchInitialStatus();

    return () => {
      isSubscribed = false;
    };
  }, [isMockMode]);

  // Execute route plan
  const handlePlanRoutes = async () => {
    if (!origin || !destination) return;

    setIsPlanningLoading(true);
    setError(null);

    try {
      const res = await planRoutes(
        {
          origin,
          destination,
          vehicle_type: vehicleType,
          departure_time: departureTime ? new Date(departureTime).toISOString() : undefined,
        },
        {
          mock: isMockMode,
          scenario: mockScenario,
        }
      );

      setRoutes(res.routes || []);
      setRecommendedRouteId(res.recommended_route_id);
      setSelectedRouteId(res.recommended_route_id);
      setRiskSource(res.risk_source);
      setPickingMode(null);
    } catch (err) {
      setError(err);
      setRoutes([]);
    } finally {
      setIsPlanningLoading(false);
    }
  };

  // Map click coordinate handlers
  const handleSelectOrigin = (coords: Coordinates) => {
    setOrigin(coords);
    setPickingMode(null);
  };

  const handleSelectDestination = (coords: Coordinates) => {
    setDestination(coords);
    setPickingMode(null);
  };

  const activeRoute =
    routes.find((r) => r.route_id === selectedRouteId) ||
    routes.find((r) => r.route_id === recommendedRouteId) ||
    routes[0];

  const activeBbox = coverage?.bbox || DEFAULT_CORRIDOR_BBOX;

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black text-zinc-900 dark:text-zinc-100 flex flex-col font-sans">
      {/* Top Header */}
      <Header
        health={health}
        isHealthLoading={isHealthLoading}
        onRefreshHealth={() => loadSystemStatus(isMockMode)}
        isMockMode={isMockMode}
        onToggleMockMode={(val) => {
          setIsMockMode(val);
          setError(null);
        }}
        mockScenario={mockScenario}
        onSelectMockScenario={(sc) => {
          setMockScenario(sc);
          setError(null);
        }}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-4 flex flex-col">
        {/* Regional Telemetry Metrics Row */}
        <DashboardMetrics summary={summary} isLoading={isSummaryLoading} />

        {/* Global Error Banner */}
        <ErrorBanner
          error={error as Error | null}
          onDismiss={() => setError(null)}
          onRetry={handlePlanRoutes}
        />

        {/* Two-Column Responsive Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 flex-1 items-start">
          {/* Left Column: Controls & Results (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            {/* Route Planning Form */}
            <RouteForm
              origin={origin}
              destination={destination}
              onOriginChange={setOrigin}
              onDestinationChange={setDestination}
              vehicleType={vehicleType}
              onVehicleTypeChange={setVehicleType}
              departureTime={departureTime}
              onDepartureTimeChange={setDepartureTime}
              pickingMode={pickingMode}
              onTogglePickingMode={setPickingMode}
              coverageBbox={activeBbox}
              onSubmit={handlePlanRoutes}
              isLoading={isPlanningLoading}
            />

            {/* Candidate Route Results Cards */}
            {routes.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-1.5">
                    <span>🛣️</span> Candidate Routes ({routes.length})
                  </h3>
                  <span className="text-[11px] text-zinc-500">
                    Click route to highlight
                  </span>
                </div>

                <div className="space-y-2.5">
                  {routes.map((route) => (
                    <RouteCard
                      key={route.route_id}
                      route={route}
                      isRecommended={route.route_id === recommendedRouteId}
                      isSelected={route.route_id === (selectedRouteId || recommendedRouteId)}
                      onSelect={() => setSelectedRouteId(route.route_id)}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Selected Route Explainability & Risk Details */}
            {activeRoute && (
              <RouteDetails
                route={activeRoute}
                riskSource={riskSource}
                isRecommended={activeRoute.route_id === recommendedRouteId}
              />
            )}
          </div>

          {/* Right Column: Interactive Map (7 cols) */}
          <div className="lg:col-span-7 h-[580px] lg:h-[720px] lg:sticky lg:top-20">
            <MapView
              routes={routes}
              recommendedRouteId={recommendedRouteId}
              selectedRouteId={selectedRouteId}
              onSelectRoute={setSelectedRouteId}
              origin={origin}
              destination={destination}
              onSelectOrigin={handleSelectOrigin}
              onSelectDestination={handleSelectDestination}
              pickingMode={pickingMode}
              coverageBbox={activeBbox}
            />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full border-t border-zinc-200 dark:border-zinc-800 py-4 px-6 text-center text-xs text-zinc-500 dark:text-zinc-400 bg-white dark:bg-zinc-900">
        <p>
          NER-ResQ Smart Logistics & Accessibility Intelligence Platform • Person 4 Frontend Implementation • OpenStreetMap Data &copy; contributors
        </p>
      </footer>
    </div>
  );
}
