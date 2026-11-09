"use client";

import React, { useState } from "react";

// Historical Incident Distribution by Month along Northeast NH-6 Corridor
const HISTORICAL_INCIDENTS = [
  { month: "Jan", landslides: 2, floods: 0 },
  { month: "Feb", landslides: 3, floods: 0 },
  { month: "Mar", landslides: 5, floods: 1 },
  { month: "Apr", landslides: 12, floods: 4 },
  { month: "May", landslides: 28, floods: 14 },
  { month: "Jun", landslides: 54, floods: 38 },
  { month: "Jul", landslides: 68, floods: 45 },
  { month: "Aug", landslides: 61, floods: 42 },
  { month: "Sep", landslides: 41, floods: 22 },
  { month: "Oct", landslides: 18, floods: 6 },
  { month: "Nov", landslides: 6, floods: 1 },
  { month: "Dec", landslides: 2, floods: 0 },
];

// Elevation & Slope Profile along Guwahati (55m) to Shillong (1,496m) Corridor
const ELEVATION_PROFILE = [
  { km: "0", name: "Guwahati Hub", elev: 55, slope: 1.2 },
  { km: "15", name: "Khanapara", elev: 85, slope: 2.4 },
  { km: "30", name: "Byrnihat", elev: 160, slope: 5.8 },
  { km: "48", name: "Nongpoh", elev: 580, slope: 9.4 },
  { km: "68", name: "Umsning", elev: 890, slope: 12.1 },
  { km: "85", name: "Umiam Lake", elev: 1020, slope: 8.2 },
  { km: "104", name: "Shillong Peak", elev: 1496, slope: 6.5 },
];

export function HistoricalIncidentChart() {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const maxVal = 70;
  const height = 180;
  const width = 500;
  const barWidth = 14;
  const gap = (width - barWidth * 2 * HISTORICAL_INCIDENTS.length) / (HISTORICAL_INCIDENTS.length + 1);

  return (
    <div className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs space-y-3">
      <div className="flex items-center justify-between pb-2 border-b border-slate-100">
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
            <span>📈</span> Historical Disaster Disruptions (Northeast Corridor)
          </h3>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Monthly distribution derived from GSI Landslide & CWC Flood Archives
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1.5 font-medium text-slate-600">
            <span className="w-2.5 h-2.5 rounded bg-amber-500 inline-block"></span>
            Landslides
          </span>
          <span className="flex items-center gap-1.5 font-medium text-slate-600">
            <span className="w-2.5 h-2.5 rounded bg-sky-500 inline-block"></span>
            Monsoon Floods
          </span>
        </div>
      </div>

      {/* SVG Bar Chart */}
      <div className="relative pt-2">
        <svg viewBox={`0 0 ${width} ${height + 30}`} className="w-full h-48 overflow-visible">
          {/* Horizontal Grid lines */}
          {[0, 20, 40, 60].map((val) => {
            const y = height - (val / maxVal) * height;
            return (
              <g key={val}>
                <line x1="0" y1={y} x2={width} y2={y} stroke="#e2e8f0" strokeDasharray="3 3" />
                <text x="2" y={y - 3} fill="#94a3b8" fontSize="9" fontFamily="monospace">
                  {val}
                </text>
              </g>
            );
          })}

          {/* Bars */}
          {HISTORICAL_INCIDENTS.map((d, i) => {
            const x = gap + i * (barWidth * 2 + gap);
            const landHeight = (d.landslides / maxVal) * height;
            const floodHeight = (d.floods / maxVal) * height;
            const landY = height - landHeight;
            const floodY = height - floodHeight;
            const isHovered = hoveredIndex === i;

            return (
              <g
                key={d.month}
                onMouseEnter={() => setHoveredIndex(i)}
                onMouseLeave={() => setHoveredIndex(null)}
                className="cursor-pointer"
              >
                {/* Landslide bar */}
                <rect
                  x={x}
                  y={landY}
                  width={barWidth}
                  height={landHeight}
                  fill="#f59e0b"
                  rx="2"
                  opacity={isHovered ? 1 : 0.85}
                  className="transition-opacity"
                />
                {/* Flood bar */}
                <rect
                  x={x + barWidth + 2}
                  y={floodY}
                  width={barWidth}
                  height={floodHeight}
                  fill="#0284c7"
                  rx="2"
                  opacity={isHovered ? 1 : 0.85}
                  className="transition-opacity"
                />
                {/* X axis Label */}
                <text
                  x={x + barWidth}
                  y={height + 16}
                  fill={isHovered ? "#0f172a" : "#64748b"}
                  fontSize="10"
                  textAnchor="middle"
                  fontWeight={isHovered ? "bold" : "normal"}
                >
                  {d.month}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Hover Tooltip display */}
        {hoveredIndex !== null && (
          <div className="p-2 rounded bg-slate-900 text-white text-[11px] shadow-lg absolute top-2 right-2 space-y-0.5">
            <div className="font-bold border-b border-slate-700 pb-0.5">
              {HISTORICAL_INCIDENTS[hoveredIndex].month}: Total Disruptions
            </div>
            <div className="flex justify-between gap-4 text-amber-300">
              <span>Landslides:</span>
              <span className="font-mono font-bold">
                {HISTORICAL_INCIDENTS[hoveredIndex].landslides}
              </span>
            </div>
            <div className="flex justify-between gap-4 text-sky-300">
              <span>Floods:</span>
              <span className="font-mono font-bold">
                {HISTORICAL_INCIDENTS[hoveredIndex].floods}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function ElevationProfileChart() {
  const [hoveredKm, setHoveredKm] = useState<number | null>(null);

  const maxElev = 1600;
  const height = 180;
  const width = 500;
  const points = ELEVATION_PROFILE.map((p, i) => {
    const x = (i / (ELEVATION_PROFILE.length - 1)) * (width - 40) + 20;
    const y = height - (p.elev / maxElev) * height;
    return { x, y, ...p };
  });

  const pathD = points.reduce((acc, p, i) => {
    return i === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`;
  }, "");

  const areaD = `${pathD} L ${points[points.length - 1].x} ${height} L ${points[0].x} ${height} Z`;

  return (
    <div className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs space-y-3">
      <div className="flex items-center justify-between pb-2 border-b border-slate-100">
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
            <span>⛰️</span> Terrain Elevation & Slope Gradient Profile
          </h3>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Guwahati Basin (55m) → Shillong Plateau (1,496m) Digital Elevation Model
          </p>
        </div>
        <span className="text-[10px] font-mono font-bold px-2 py-0.5 bg-slate-100 rounded text-slate-600">
          Max Slope: 12.1°
        </span>
      </div>

      <div className="relative pt-2">
        <svg viewBox={`0 0 ${width} ${height + 30}`} className="w-full h-48 overflow-visible">
          {/* Horizontal altitude lines */}
          {[200, 600, 1000, 1400].map((elev) => {
            const y = height - (elev / maxElev) * height;
            return (
              <g key={elev}>
                <line x1="20" y1={y} x2={width - 20} y2={y} stroke="#e2e8f0" strokeDasharray="3 3" />
                <text x="2" y={y + 3} fill="#94a3b8" fontSize="9" fontFamily="monospace">
                  {elev}m
                </text>
              </g>
            );
          })}

          {/* Shaded Area */}
          <path d={areaD} fill="url(#elevGradient)" opacity="0.4" />

          {/* Gradients */}
          <defs>
            <linearGradient id="elevGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0284c7" />
              <stop offset="100%" stopColor="#e0f2fe" />
            </linearGradient>
          </defs>

          {/* Elevation Line */}
          <path d={pathD} fill="none" stroke="#0284c7" strokeWidth="2.5" />

          {/* Waypoint circles */}
          {points.map((p, i) => (
            <g
              key={p.km}
              onMouseEnter={() => setHoveredKm(i)}
              onMouseLeave={() => setHoveredKm(null)}
              className="cursor-pointer"
            >
              <circle
                cx={p.x}
                cy={p.y}
                r={hoveredKm === i ? 6 : 4}
                fill="#ffffff"
                stroke="#0284c7"
                strokeWidth="2.5"
                className="transition-all"
              />
              <text x={p.x} y={height + 16} fill="#64748b" fontSize="9" textAnchor="middle">
                {p.km}km
              </text>
            </g>
          ))}
        </svg>

        {hoveredKm !== null && (
          <div className="p-2 rounded bg-slate-900 text-white text-[11px] shadow-lg absolute top-2 right-2 space-y-0.5">
            <div className="font-bold border-b border-slate-700 pb-0.5">
              {ELEVATION_PROFILE[hoveredKm].name} (KM {ELEVATION_PROFILE[hoveredKm].km})
            </div>
            <div className="text-sky-300">
              Altitude: <span className="font-mono font-bold">{ELEVATION_PROFILE[hoveredKm].elev} m</span>
            </div>
            <div className="text-rose-300">
              Slope Gradient:{" "}
              <span className="font-mono font-bold">{ELEVATION_PROFILE[hoveredKm].slope}°</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
