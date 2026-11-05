"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import * as maplibregl from "maplibre-gl";
import { Coordinates, Route } from "../lib/types";
import {
  DEFAULT_CORRIDOR_BBOX,
  DEFAULT_MAP_CENTER,
  getRiskColor,
  getRiskLevel,
  OSM_ATTRIBUTION,
  OSM_TILE_URL,
  RISK_LEVEL_CONFIG,
} from "../lib/constants";

interface MapViewProps {
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
}

export default function MapView({
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
}: MapViewProps) {
  const mapContainer = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const originMarkerRef = useRef<maplibregl.Marker | null>(null);
  const destMarkerRef = useRef<maplibregl.Marker | null>(null);
  const hoverPopupRef = useRef<maplibregl.Popup | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [isLegendOpen, setIsLegendOpen] = useState(true);

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
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), "top-right");

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

  // Handle map click for coordinate picking
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

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
    };
  }, [pickingMode, onSelectOrigin, onSelectDestination]);

  // Update Origin and Destination Markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Origin Marker
    if (origin) {
      if (!originMarkerRef.current) {
        const el = document.createElement("div");
        el.className = "flex items-center justify-center";
        el.innerHTML = `
          <div style="background-color: #10b981; border: 2px solid white; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3);" 
               class="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold ring-2 ring-emerald-500">
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

    // Destination Marker
    if (destination) {
      if (!destMarkerRef.current) {
        const el = document.createElement("div");
        el.className = "flex items-center justify-center";
        el.innerHTML = `
          <div style="background-color: #ef4444; border: 2px solid white; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3);" 
               class="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold ring-2 ring-rose-500">
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
            "#0284c7", // Bright cyan/blue highlight for recommended route
            "#334155",
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
            0.45,
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
                <div class="font-bold flex items-center gap-1.5">
                  <span>Route: ${props.route_id}</span>
                  ${props.is_recommended ? '<span class="text-sky-500 font-semibold text-[10px]">★ Recommended</span>' : ""}
                </div>
                <div class="text-zinc-600 dark:text-zinc-400">Segment: <span class="font-mono">${props.segment_id}</span></div>
                <div class="flex items-center gap-2 pt-1 border-t border-zinc-200 dark:border-zinc-800">
                  <span class="inline-block w-2.5 h-2.5 rounded-full" style="background-color: ${props.risk_color};"></span>
                  <span class="font-semibold text-zinc-900 dark:text-zinc-100">${levelConfig.label}</span>
                  <span class="text-zinc-500">(Score: ${props.risk_score}/100)</span>
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

  // Viewport action: Fit all routes
  const handleFitRoutes = useCallback(() => {
    const map = mapRef.current;
    if (!map || routes.length === 0) return;

    const bounds = new maplibregl.LngLatBounds();
    routes.forEach((route) => {
      route.geometry.coordinates.forEach((c) => bounds.extend(c));
    });
    map.fitBounds(bounds, { padding: 50, duration: 800 });
  }, [routes]);

  // Viewport action: Reset to full coverage corridor
  const handleResetCoverage = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    const [minLng, minLat, maxLng, maxLat] = coverageBbox;
    map.fitBounds([minLng, minLat, maxLng, maxLat], { padding: 40, duration: 800 });
  }, [coverageBbox]);

  return (
    <div className="relative w-full h-full min-h-[420px] rounded-xl overflow-hidden border border-zinc-200 dark:border-zinc-800 bg-zinc-100 dark:bg-zinc-900 shadow-sm flex flex-col">
      {/* Map Target Container */}
      <div ref={mapContainer} className="w-full h-full flex-1" />

      {/* Picking Mode Banner */}
      {pickingMode && (
        <div className="absolute top-3 left-3 right-14 sm:right-auto z-10 bg-sky-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium shadow-md flex items-center gap-2 animate-pulse">
          <span className="w-2 h-2 rounded-full bg-white"></span>
          <span>Click anywhere on the road corridor to set {pickingMode === "origin" ? "Origin" : "Destination"}</span>
        </div>
      )}

      {/* Map Control Buttons */}
      <div className="absolute bottom-6 left-3 z-10 flex flex-col gap-2">
        <button
          onClick={handleFitRoutes}
          disabled={routes.length === 0}
          title="Fit view to planned routes"
          className="bg-white/95 dark:bg-zinc-800/95 text-zinc-700 dark:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-700 disabled:opacity-40 disabled:cursor-not-allowed border border-zinc-200 dark:border-zinc-700 text-xs font-semibold px-2.5 py-1.5 rounded-lg shadow-sm backdrop-blur flex items-center gap-1.5 transition-colors"
        >
          <span>🎯</span> Fit Route
        </button>
        <button
          onClick={handleResetCoverage}
          title="Reset view to Guwahati-Shillong corridor"
          className="bg-white/95 dark:bg-zinc-800/95 text-zinc-700 dark:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-700 border border-zinc-200 dark:border-zinc-700 text-xs font-semibold px-2.5 py-1.5 rounded-lg shadow-sm backdrop-blur flex items-center gap-1.5 transition-colors"
        >
          <span>🗺️</span> Reset Corridor
        </button>
      </div>

      {/* Risk Color Legend */}
      <div className="absolute bottom-6 right-3 z-10">
        {isLegendOpen ? (
          <div className="bg-white/95 dark:bg-zinc-800/95 border border-zinc-200 dark:border-zinc-700 p-2.5 rounded-xl shadow-lg backdrop-blur text-xs w-48 transition-all">
            <div className="flex items-center justify-between font-semibold pb-1.5 mb-1.5 border-b border-zinc-200 dark:border-zinc-700 text-zinc-800 dark:text-zinc-200">
              <span>Segment Risk Legend</span>
              <button
                onClick={() => setIsLegendOpen(false)}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 px-1"
                aria-label="Collapse legend"
              >
                ✕
              </button>
            </div>
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-emerald-500"></span>
                  <span className="text-zinc-700 dark:text-zinc-300">Low</span>
                </div>
                <span className="text-[11px] font-mono text-zinc-500">0 – 33</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-amber-500"></span>
                  <span className="text-zinc-700 dark:text-zinc-300">Medium</span>
                </div>
                <span className="text-[11px] font-mono text-zinc-500">34 – 66</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-rose-500"></span>
                  <span className="text-zinc-700 dark:text-zinc-300">High</span>
                </div>
                <span className="text-[11px] font-mono text-zinc-500">67 – 100</span>
              </div>
              <div className="pt-1.5 mt-1 border-t border-zinc-200 dark:border-zinc-700 flex items-center gap-2">
                <span className="w-4 h-1.5 bg-sky-600 rounded"></span>
                <span className="text-[11px] text-zinc-600 dark:text-zinc-400">Recommended Route</span>
              </div>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setIsLegendOpen(true)}
            className="bg-white/95 dark:bg-zinc-800/95 text-zinc-700 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-700 text-xs font-semibold px-2.5 py-1.5 rounded-lg shadow-md backdrop-blur"
          >
            📊 Show Legend
          </button>
        )}
      </div>
    </div>
  );
}
