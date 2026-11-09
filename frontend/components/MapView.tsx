"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import * as maplibregl from "maplibre-gl";
import { Coordinates, Route, VehiclePosition } from "../lib/types";
import {
  DEFAULT_CORRIDOR_BBOX,
  DEFAULT_MAP_CENTER,
  getRiskColor,
  getRiskLevel,
  OSM_ATTRIBUTION,
  OSM_TILE_URL,
  RISK_LEVEL_CONFIG,
} from "../lib/constants";
import { MOCK_HAZARD_ZONES } from "../lib/mockData";

maplibregl.setWorkerUrl(
  "/vendor/maplibre-gl/maplibre-gl-worker.mjs"
);

interface MapViewProps {
  mode?: "overview" | "routes" | "risk-zones" | "fleet";
  routes?: Route[];
  recommendedRouteId?: string;
  selectedRouteId?: string;
  onSelectRoute?: (routeId: string) => void;
  origin?: Coordinates | null;
  destination?: Coordinates | null;
  onSelectOrigin?: (coords: Coordinates) => void;
  onSelectDestination?: (coords: Coordinates) => void;
  pickingMode?: "origin" | "destination" | null;
  coverageBbox?: [number, number, number, number];
  vehicles?: VehiclePosition[];
  onSelectVehicle?: (v: VehiclePosition) => void;
  selectedVehicleId?: string;
  hazardSeverityFilter?: string;
  hazardCategoryFilter?: string;
}

export default function MapView({
  mode = "overview",
  routes = [],
  recommendedRouteId,
  selectedRouteId,
  onSelectRoute,
  origin,
  destination,
  onSelectOrigin,
  onSelectDestination,
  pickingMode = null,
  coverageBbox = DEFAULT_CORRIDOR_BBOX,
  vehicles = [],
  onSelectVehicle,
  selectedVehicleId,
  hazardSeverityFilter = "all",
  hazardCategoryFilter = "all",
}: MapViewProps) {
  const mapContainer = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const originMarkerRef = useRef<maplibregl.Marker | null>(null);
  const destMarkerRef = useRef<maplibregl.Marker | null>(null);
  const hazardMarkersRef = useRef<maplibregl.Marker[]>([]);
  const vehicleMarkersRef = useRef<maplibregl.Marker[]>([]);
  const hoverPopupRef = useRef<maplibregl.Popup | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [isLegendOpen, setIsLegendOpen] = useState(true);
  const [showHazards, setShowHazards] = useState(true);
  const [tileError, setTileError] = useState(false);

  // Initialize MapLibre GL
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const [minLng, minLat, maxLng, maxLat] = coverageBbox;
    const initialBounds: [number, number, number, number] = [
      minLng - 0.05,
      minLat - 0.05,
      maxLng + 0.05,
      maxLat + 0.05,
    ];

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          "osm-tiles": {
            type: "raster",
            tiles: [OSM_TILE_URL],
            tileSize: 256,
            attribution: OSM_ATTRIBUTION,
            maxzoom: 19,
          },
        },
        layers: [
          {
            id: "osm-layer",
            type: "raster",
            source: "osm-tiles",
            minzoom: 0,
            maxzoom: 19,
          },
        ],
      },
      center: DEFAULT_MAP_CENTER,
      zoom: 11,
      maxBounds: [
        [minLng - 0.3, minLat - 0.3],
        [maxLng + 0.3, maxLat + 0.3],
      ],
      attributionControl: false,
    });

    // Dedicated attribution control placed at bottom-left to avoid crowding legend at bottom-right
    map.addControl(
      new maplibregl.AttributionControl({ compact: false }),
      "bottom-left"
    );

    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), "top-right");

    // Graceful tile-loading error handling:
    // Intercept raster tile 403/429/network errors so transient tile server limits do not produce unhandled AJAXErrors
    map.on("error", (e) => {
      const eventWithSource = e as unknown as { sourceId?: string; error?: { status?: number; message?: string } };
      const err = eventWithSource.error;
      const isOsmTileFetchError =
        eventWithSource.sourceId === "osm-tiles" &&
        (err?.status === 403 ||
          err?.status === 429 ||
          err?.status === 0 ||
          (err?.message ? /ajaxerror|fetch/i.test(err.message) : false));

      if (isOsmTileFetchError) {
        setTileError(true);
        return;
      }

      // Do NOT hide genuine application errors (GeoJSON parsing, style expressions, layer binding):
      if (typeof console !== "undefined" && console.error) {
        console.error("[MapLibre Application Error]", e.error || e);
      }
    });

    map.on("load", () => {
      setMapLoaded(true);
      map.fitBounds(initialBounds, { padding: 40, duration: 800 });
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [coverageBbox]);

  // Handle map click and cursor for coordinate picking
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const canvas = map.getCanvas();
    if (pickingMode === "origin" || pickingMode === "destination") {
      canvas.style.cursor = "crosshair";
    } else {
      canvas.style.cursor = "";
    }

    const handleClick = (e: maplibregl.MapMouseEvent) => {
      const coords: Coordinates = {
        lat: Number(e.lngLat.lat.toFixed(5)),
        lng: Number(e.lngLat.lng.toFixed(5)),
      };

      if (pickingMode === "origin" && onSelectOrigin) {
        onSelectOrigin(coords);
      } else if (pickingMode === "destination" && onSelectDestination) {
        onSelectDestination(coords);
      }
    };

    map.on("click", handleClick);
    return () => {
      map.off("click", handleClick);
      if (canvas) canvas.style.cursor = "";
    };
  }, [pickingMode, onSelectOrigin, onSelectDestination]);

  // Update Origin and Destination Markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Origin Marker (A)
    if (origin) {
      if (!originMarkerRef.current) {
        const el = document.createElement("div");
        el.className = "flex items-center justify-center cursor-pointer";
        el.innerHTML = `
          <div style="background-color: #10b981; border: 2.5px solid white; box-shadow: 0 4px 10px rgba(0,0,0,0.25);" 
               class="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-black shadow-md cursor-pointer">
            A
          </div>`;
        originMarkerRef.current = new maplibregl.Marker({ element: el })
          .setLngLat([origin.lng, origin.lat])
          .addTo(map);
      } else {
        originMarkerRef.current.setLngLat([origin.lng, origin.lat]);
      }
    } else if (originMarkerRef.current) {
      originMarkerRef.current.remove();
      originMarkerRef.current = null;
    }

    // Destination Marker (B)
    if (destination) {
      if (!destMarkerRef.current) {
        const el = document.createElement("div");
        el.className = "flex items-center justify-center cursor-pointer";
        el.innerHTML = `
          <div style="background-color: #ef4444; border: 2.5px solid white; box-shadow: 0 4px 10px rgba(0,0,0,0.25);" 
               class="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-black shadow-md cursor-pointer">
            B
          </div>`;
        destMarkerRef.current = new maplibregl.Marker({ element: el })
          .setLngLat([destination.lng, destination.lat])
          .addTo(map);
      } else {
        destMarkerRef.current.setLngLat([destination.lng, destination.lat]);
      }
    } else if (destMarkerRef.current) {
      destMarkerRef.current.remove();
      destMarkerRef.current = null;
    }
  }, [origin, destination]);

  // Render Hazard Indicators
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    // Clear old hazard markers
    hazardMarkersRef.current.forEach((m) => m.remove());
    hazardMarkersRef.current = [];

    if (!showHazards && mode !== "risk-zones") return;

    const filtered = MOCK_HAZARD_ZONES.filter((hzd) => {
      if (hazardSeverityFilter !== "all" && hzd.severity !== hazardSeverityFilter) return false;
      if (hazardCategoryFilter !== "all" && hzd.category !== hazardCategoryFilter) return false;
      return true;
    });

    filtered.forEach((hzd) => {
      const el = document.createElement("div");
      el.className = "cursor-pointer group relative";
      const markerColor =
        hzd.severity === "high" || hzd.severity === "critical"
          ? "#ef4444"
          : hzd.severity === "medium"
          ? "#f59e0b"
          : "#10b981";

      const catIcon =
        hzd.category === "heavy_rainfall" || hzd.category === "flood" || hzd.category === "flash_flood"
          ? "🌧️"
          : hzd.category === "high_winds"
          ? "💨"
          : hzd.category === "severe_weather"
          ? "⛈️"
          : hzd.category === "steep_slope" || hzd.category === "slope"
          ? "⛰️"
          : "🪨";

      el.innerHTML = `
        <div style="background-color: ${markerColor}; border: 2px solid white; box-shadow: 0 4px 10px rgba(0,0,0,0.25);" 
             class="w-7 h-7 rounded-full flex items-center justify-center text-white text-[11px] font-bold shadow-md cursor-pointer animate-pulse">
          ${catIcon}
        </div>
      `;

      const factorsHtml = hzd.contributing_factors
        ? `<div class="pt-1.5 border-t border-slate-100 space-y-0.5 text-[10px]">
            <span class="font-bold text-slate-700">Contributing Risk Factors:</span>
            ${hzd.contributing_factors.map((f) => `<div class="text-slate-500">• ${f.factor}: <strong class="text-slate-700">${f.value}</strong></div>`).join("")}
          </div>`
        : "";

      const fidelityBadge = hzd.data_fidelity
        ? `<div class="text-[9px] font-mono text-slate-400 mt-1">Fidelity: ${hzd.data_fidelity}</div>`
        : "";

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat(hzd.coordinates)
        .setPopup(
          new maplibregl.Popup({ offset: 12 }).setHTML(`
            <div class="text-xs space-y-1.5 p-1 max-w-[240px]">
              <div class="font-bold text-slate-900">${hzd.name}</div>
              <div class="text-slate-600 font-mono text-[11px]">${hzd.corridor_km}</div>
              <p class="text-slate-600 text-[11px] leading-relaxed">${hzd.description}</p>
              ${factorsHtml}
              <div class="flex items-center justify-between pt-1 border-t border-slate-100 text-[10px]">
                <span class="font-bold uppercase" style="color: ${markerColor};">${hzd.severity} Risk (${hzd.risk_score}/100)</span>
                <span class="text-slate-400 font-medium">${hzd.active_status}</span>
              </div>
              ${fidelityBadge}
            </div>
          `)
        )
        .addTo(map);

      hazardMarkersRef.current.push(marker);
    });
  }, [mapLoaded, showHazards, mode, hazardSeverityFilter, hazardCategoryFilter]);

  // Render Fleet Vehicle Markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    vehicleMarkersRef.current.forEach((m) => m.remove());
    vehicleMarkersRef.current = [];

    if (mode !== "fleet" && mode !== "overview") return;

    vehicles.forEach((v) => {
      const isSelected = v.vehicle_id === selectedVehicleId;
      const el = document.createElement("div");
      el.className = "cursor-pointer group relative";
      el.innerHTML = `
        <div style="background-color: ${isSelected ? "#0284c7" : "#1e293b"}; border: 2.5px solid white; box-shadow: 0 4px 12px rgba(0,0,0,0.3);" 
             class="px-2 py-1 rounded-full text-white text-[10px] font-bold flex items-center gap-1 shadow-md cursor-pointer transition-transform hover:scale-110">
          <span>🚚</span>
          <span>${v.vehicle_id}</span>
        </div>
      `;

      el.addEventListener("click", () => {
        if (onSelectVehicle) onSelectVehicle(v);
      });

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([v.lng, v.lat])
        .setPopup(
          new maplibregl.Popup({ offset: 12 }).setHTML(`
            <div class="text-xs space-y-1 p-1">
              <div class="font-bold text-slate-900 flex items-center justify-between">
                <span>Vehicle ${v.vehicle_id}</span>
                <span class="text-[10px] px-1.5 py-0.2 rounded bg-sky-100 text-sky-800 font-bold capitalize">${v.status || "In Transit"}</span>
              </div>
              <div class="text-slate-600 text-[11px]">Speed: <span class="font-mono font-bold">${v.speed_kmh} km/h</span> • Class: <span class="capitalize">${v.vehicle_class || "truck"}</span></div>
              <div class="text-slate-500 font-mono text-[10px]">Coords: [${v.lat.toFixed(4)}, ${v.lng.toFixed(4)}]</div>
            </div>
          `)
        )
        .addTo(map);

      vehicleMarkersRef.current.push(marker);
    });
  }, [mapLoaded, vehicles, mode, selectedVehicleId, onSelectVehicle]);

  // Update Route and Segment layers
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    const sourceId = "routes-segments-source";
    const casingLayerId = "routes-casing-layer";
    const segmentsLayerId = "routes-segments-layer";

    // Build GeoJSON features for all route segments
    type SegmentFeature = {
      type: "Feature";
      geometry: {
        type: "LineString";
        coordinates: [number, number][];
      };
      properties: {
        route_id: string;
        segment_id: string;
        risk_score: number;
        risk_color: string;
        risk_level: string;
        is_recommended: boolean;
        is_selected: boolean;
      };
    };

    const features: SegmentFeature[] = [];

    routes.forEach((route) => {
      const isRecommended = route.route_id === recommendedRouteId;
      const isSelected = route.route_id === (selectedRouteId || recommendedRouteId);

      route.segments.forEach((seg) => {
        features.push({
          type: "Feature",
          geometry: {
            type: "LineString",
            coordinates: seg.coordinates,
          },
          properties: {
            route_id: route.route_id,
            segment_id: seg.segment_id,
            risk_score: seg.risk_score,
            risk_color: getRiskColor(seg.risk_score),
            risk_level: getRiskLevel(seg.risk_score),
            is_recommended: isRecommended,
            is_selected: isSelected,
          },
        });
      });
    });

    const geojsonData: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features,
    };

    // Update or add data source
    const existingSource = map.getSource(sourceId) as maplibregl.GeoJSONSource | undefined;
    if (existingSource) {
      existingSource.setData(geojsonData);
    } else {
      map.addSource(sourceId, {
        type: "geojson",
        data: geojsonData,
      });

      // Layer 1: Route Casing / Glow for recommended or selected routes
      map.addLayer({
        id: casingLayerId,
        type: "line",
        source: sourceId,
        layout: {
          "line-cap": "round",
          "line-join": "round",
        },
        paint: {
          "line-color": [
            "case",
            ["get", "is_recommended"],
            "#0284c7",
            "#64748b",
          ],
          "line-width": [
            "case",
            ["get", "is_selected"],
            9,
            ["get", "is_recommended"],
            7,
            3,
          ],
          "line-opacity": [
            "case",
            ["get", "is_selected"],
            0.85,
            0.3,
          ],
        },
      });

      // Layer 2: Segment polylines colored by risk score
      map.addLayer({
        id: segmentsLayerId,
        type: "line",
        source: sourceId,
        layout: {
          "line-cap": "round",
          "line-join": "round",
        },
        paint: {
          "line-color": ["get", "risk_color"],
          "line-width": [
            "case",
            ["get", "is_selected"],
            6,
            4,
          ],
          "line-opacity": [
            "case",
            ["get", "is_selected"],
            1.0,
            0.5,
          ],
        },
      });

      // Hover and Click interactions on segments
      map.on("mouseenter", segmentsLayerId, (e) => {
        map.getCanvas().style.cursor = "pointer";
        if (!e.features || e.features.length === 0) return;

        const feature = e.features[0];
        const props = feature.properties as SegmentFeature["properties"];
        const coords = e.lngLat;

        if (!hoverPopupRef.current) {
          hoverPopupRef.current = new maplibregl.Popup({
            closeButton: false,
            closeOnClick: false,
            offset: 12,
          });
        }

        const popup = hoverPopupRef.current;
        if (popup) {
          const levelConfig = RISK_LEVEL_CONFIG[props.risk_level as "low" | "medium" | "high"];
          popup
            .setLngLat(coords)
            .setHTML(
              `<div class="text-xs space-y-1">
                <div class="font-bold flex items-center justify-between gap-2">
                  <span class="text-slate-900">Route: ${props.route_id.toUpperCase()}</span>
                  ${props.is_recommended ? '<span class="text-sky-600 font-bold text-[10px] bg-sky-50 px-1.5 py-0.5 rounded">★ Recommended</span>' : ""}
                </div>
                <div class="text-slate-500 font-mono text-[11px]">Segment ID: ${props.segment_id}</div>
                <div class="flex items-center gap-2 pt-1.5 border-t border-slate-100">
                  <span class="inline-block w-2.5 h-2.5 rounded-full" style="background-color: ${props.risk_color};"></span>
                  <span class="font-bold text-slate-800">${levelConfig.label}</span>
                  <span class="font-mono text-slate-500 font-semibold">(${props.risk_score}/100)</span>
                </div>
              </div>`
            )
            .addTo(map);
        }
      });

      map.on("mouseleave", segmentsLayerId, () => {
        map.getCanvas().style.cursor = "";
        if (hoverPopupRef.current) {
          hoverPopupRef.current.remove();
        }
      });

      map.on("click", segmentsLayerId, (e) => {
        if (!e.features || e.features.length === 0) return;
        const feature = e.features[0];
        const props = feature.properties as SegmentFeature["properties"];
        if (onSelectRoute) {
          onSelectRoute(props.route_id);
        }
      });
    }

    // Auto-fit to active route if available
    if (routes.length > 0) {
      const activeRoute =
        routes.find((r) => r.route_id === (selectedRouteId || recommendedRouteId)) || routes[0];

      if (activeRoute && activeRoute.geometry.coordinates.length > 0) {
        const bounds = new maplibregl.LngLatBounds();
        activeRoute.geometry.coordinates.forEach((coord) => {
          bounds.extend(coord);
        });
        map.fitBounds(bounds, { padding: 60, duration: 1000 });
      }
    }
  }, [routes, recommendedRouteId, selectedRouteId, mapLoaded, onSelectRoute]);

  // Viewport action: Fit all routes or vehicles
  const handleFitRoutes = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;

    if (routes.length > 0) {
      const bounds = new maplibregl.LngLatBounds();
      routes.forEach((route) => {
        route.geometry.coordinates.forEach((c) => bounds.extend(c));
      });
      map.fitBounds(bounds, { padding: 50, duration: 800 });
    } else if (vehicles.length > 0) {
      const bounds = new maplibregl.LngLatBounds();
      vehicles.forEach((v) => bounds.extend([v.lng, v.lat]));
      map.fitBounds(bounds, { padding: 50, duration: 800 });
    }
  }, [routes, vehicles]);

  // Viewport action: Reset to full coverage corridor
  const handleResetCoverage = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    const [minLng, minLat, maxLng, maxLat] = coverageBbox;
    map.fitBounds([minLng, minLat, maxLng, maxLat], { padding: 40, duration: 800 });
  }, [coverageBbox]);

  const handleRetryTiles = useCallback(() => {
    setTileError(false);
    const map = mapRef.current;
    if (!map) return;
    const source = map.getSource("osm-tiles") as maplibregl.RasterTileSource | undefined;
    if (source && typeof source.setTiles === "function") {
      // Actively reset and refetch tiles from canonical endpoint
      source.setTiles([OSM_TILE_URL]);
    } else {
      map.triggerRepaint();
    }
  }, []);

  return (
    <div className="relative w-full h-full min-h-[460px] rounded-xl overflow-hidden border border-slate-200/90 bg-slate-100 shadow-xs flex flex-col">
      {/* Map Target Container */}
      <div ref={mapContainer} className="w-full h-full flex-1" />

      {/* Graceful Tile Error Notification */}
      {tileError && (
        <div className="absolute top-3 left-3 z-20 max-w-sm p-3 rounded-xl bg-amber-50/95 border border-amber-300 text-amber-900 shadow-md backdrop-blur-xs text-xs space-y-1.5 animate-in fade-in">
          <div className="flex items-center gap-1.5 font-bold">
            <span>⚠️</span>
            <span>Base Map Tiles Degraded (Offline / Rate-Limited)</span>
          </div>
          <p className="text-[11px] text-amber-800 leading-relaxed">
            OpenStreetMap tile servers are temporarily unreachable. Vector route paths, segment risk scoring, fleet tracking, and coordinate picking remain fully functional.
          </p>
          <div className="pt-1 flex items-center justify-between">
            <button
              type="button"
              onClick={handleRetryTiles}
              className="px-2.5 py-1 text-[10px] font-bold rounded bg-amber-200/80 hover:bg-amber-200 text-amber-900 border border-amber-400 cursor-pointer transition-colors"
            >
              ↻ Retry Base Tiles
            </button>
            <span className="text-[10px] text-amber-700 font-mono">Vector Layers Active</span>
          </div>
        </div>
      )}

      {/* Picking Mode Banner */}
      {pickingMode && (
        <div className="absolute top-3 right-14 sm:right-auto sm:left-3 z-10 bg-sky-600 text-white px-3.5 py-2 rounded-lg text-xs font-semibold shadow-md flex items-center gap-2 animate-pulse border border-sky-400">
          <span className="w-2.5 h-2.5 rounded-full bg-white"></span>
          <span>Click anywhere on the road corridor to set {pickingMode === "origin" ? "Origin (A)" : "Destination (B)"}</span>
        </div>
      )}

      {/* Floating Action Controls - positioned above attribution */}
      <div className="absolute bottom-10 left-3 z-10 flex flex-col gap-2">
        <button
          onClick={handleFitRoutes}
          disabled={routes.length === 0 && vehicles.length === 0}
          title="Fit view to planned routes or fleet"
          className="bg-white/95 text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed border border-slate-200 text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm backdrop-blur-xs flex items-center gap-1.5 transition-all cursor-pointer"
        >
          <span>🎯</span> Fit View
        </button>
        <button
          onClick={handleResetCoverage}
          title="Reset view to Guwahati-Shillong corridor"
          className="bg-white/95 text-slate-700 hover:bg-slate-50 border border-slate-200 text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm backdrop-blur-xs flex items-center gap-1.5 transition-all cursor-pointer"
        >
          <span>🗺️</span> Reset Corridor
        </button>
        <button
          onClick={() => setShowHazards(!showHazards)}
          title="Toggle corridor hazard markers"
          className={`border text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm backdrop-blur-xs flex items-center gap-1.5 transition-all cursor-pointer ${
            showHazards
              ? "bg-amber-50 text-amber-800 border-amber-300"
              : "bg-white/95 text-slate-700 border-slate-200 hover:bg-slate-50"
          }`}
        >
          <span>⚠️</span> Hazards {showHazards ? "On" : "Off"}
        </button>
      </div>

      {/* Segment Risk Legend */}
      <div className="absolute bottom-6 right-3 z-10">
        {isLegendOpen ? (
          <div className="bg-white/95 border border-slate-200 p-3 rounded-xl shadow-lg backdrop-blur-xs text-xs w-52 transition-all">
            <div className="flex items-center justify-between font-bold pb-2 mb-2 border-b border-slate-100 text-slate-800">
              <span className="flex items-center gap-1.5">
                <span>📊</span> Segment Risk Scale
              </span>
              <button
                onClick={() => setIsLegendOpen(false)}
                className="text-slate-400 hover:text-slate-600 px-1 font-bold cursor-pointer"
                aria-label="Collapse legend"
              >
                ✕
              </button>
            </div>
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-2xs"></span>
                  <span className="text-slate-700 font-medium">Low Risk</span>
                </div>
                <span className="text-[11px] font-mono text-slate-500 font-semibold">0 – 33</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shadow-2xs"></span>
                  <span className="text-slate-700 font-medium">Medium Risk</span>
                </div>
                <span className="text-[11px] font-mono text-slate-500 font-semibold">34 – 66</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-2xs"></span>
                  <span className="text-slate-700 font-medium">High Risk</span>
                </div>
                <span className="text-[11px] font-mono text-slate-500 font-semibold">67 – 100</span>
              </div>
              <div className="pt-2 mt-1.5 border-t border-slate-100 flex items-center gap-2">
                <span className="w-4 h-1.5 bg-sky-600 rounded"></span>
                <span className="text-[11px] text-slate-600 font-medium">Recommended Route</span>
              </div>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setIsLegendOpen(true)}
            className="bg-white/95 text-slate-700 hover:bg-slate-50 border border-slate-200 text-xs font-semibold px-3 py-1.5 rounded-lg shadow-md backdrop-blur-xs cursor-pointer"
          >
            📊 Show Legend
          </button>
        )}
      </div>
    </div>
  );
}
