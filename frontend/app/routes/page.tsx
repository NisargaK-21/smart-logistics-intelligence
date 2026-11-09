"use client";

import React from "react";
import { useApp } from "../../lib/context";
import RouteForm from "../../components/RouteForm";
import RouteCard from "../../components/RouteCard";
import RouteDetails from "../../components/RouteDetails";
import RouteComparison from "../../components/RouteComparison";
import RiskDistribution from "../../components/RiskDistribution";
import MapView from "../../components/MapView";
import ErrorBanner from "../../components/ErrorBanner";
import { Coordinates } from "../../lib/types";

export default function RoutesPage() {
  const {
    origin,
    setOrigin,
    destination,
    setDestination,
    vehicleType,
    setVehicleType,
    departureTime,
    setDepartureTime,
    pickingMode,
    setPickingMode,
    activeBbox,
    routes,
    recommendedRouteId,
    selectedRouteId,
    setSelectedRouteId,
    activeRoute,
    riskSource,
    isPlanningLoading,
    planCurrentRoutes,
    error,
    setError,
  } = useApp();

  const handleSelectOrigin = (coords: Coordinates) => {
    setOrigin(coords);
    setPickingMode(null);
  };

  const handleSelectDestination = (coords: Coordinates) => {
    setDestination(coords);
    setPickingMode(null);
  };

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200/80">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <span>🛣️</span> Route Planning & Risk Optimization Workspace
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Evaluate road network topology, terrain gradient, and precipitation hazards to dispatch the safest route
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="font-semibold text-slate-500">Corridor Bounds:</span>
          <span className="font-mono bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200 text-[11px]">
            [{activeBbox.join(", ")}]
          </span>
        </div>
      </div>

      {/* Global Error Banner */}
      <ErrorBanner
        error={error as Error | null}
        onDismiss={() => setError(null)}
        onRetry={planCurrentRoutes}
      />

      {/* Two-Column Responsive Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column (5 Cols): Form & Candidate Analysis */}
        <div className="lg:col-span-5 space-y-6">
          {/* Route Planning Parameters Form */}
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
            onSubmit={planCurrentRoutes}
            isLoading={isPlanningLoading}
          />

          {/* Candidate Route Results Cards */}
          {routes.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                  <span>🛣️</span> Candidate Routes ({routes.length})
                </h3>
                <span className="text-[11px] text-slate-500 font-medium">
                  Click route card to highlight
                </span>
              </div>

              <div className="space-y-3">
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

          {/* Route Comparison Matrix */}
          {routes.length > 1 && (
            <RouteComparison
              routes={routes}
              recommendedRouteId={recommendedRouteId}
              selectedRouteId={selectedRouteId}
              onSelectRoute={setSelectedRouteId}
            />
          )}

          {/* Risk Level Distribution */}
          {activeRoute && <RiskDistribution route={activeRoute} />}

          {/* Selected Route Explainability & Risk Details */}
          {activeRoute && (
            <RouteDetails
              route={activeRoute}
              riskSource={riskSource}
              isRecommended={activeRoute.route_id === recommendedRouteId}
            />
          )}
        </div>

        {/* Right Column (7 Cols): Interactive GIS Map */}
        <div className="lg:col-span-7 space-y-4 lg:sticky lg:top-20">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <span>🗺️</span> Interactive Corridor Routing Canvas
            </h2>
            <span className="text-[11px] text-slate-400 font-medium">
              Click &quot;Pick on Map&quot; to set waypoints visually
            </span>
          </div>

          <div className="h-[600px] lg:h-[720px] w-full rounded-xl overflow-hidden shadow-xs border border-slate-200">
            <MapView
              mode="routes"
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
      </div>
    </div>
  );
}
