"use client";

import React, { useEffect, useState } from "react";
import { getCurrentWeather } from "../lib/api";
import { Coordinates, CurrentWeather } from "../lib/types";

interface WeatherTerrainOverviewProps {
  coordinates: Coordinates | null;
}

function describeWeather(code: number): string {
  if (code === 0) return "Clear";
  if (code <= 3) return "Cloudy";
  if (code === 45 || code === 48) return "Fog";
  if (code >= 51 && code <= 57) return "Drizzle";
  if (code >= 61 && code <= 67) return "Rain";
  if (code >= 71 && code <= 77) return "Snow";
  if (code >= 80 && code <= 82) return "Rain showers";
  if (code >= 85 && code <= 86) return "Snow showers";
  if (code >= 95) return "Thunderstorm";
  return "Current conditions";
}

export default function WeatherTerrainOverview({
  coordinates,
}: WeatherTerrainOverviewProps) {
  const [weatherState, setWeatherState] = useState<{
    key: string;
    weather?: CurrentWeather;
    error?: string;
  } | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshToken, setRefreshToken] = useState(0);
  const latitude = coordinates?.lat ?? null;
  const longitude = coordinates?.lng ?? null;
  const coordinateKey = latitude === null || longitude === null
    ? ""
    : `${latitude},${longitude}`;
  const weather = weatherState?.key === coordinateKey
    ? weatherState.weather ?? null
    : null;
  const error = weatherState?.key === coordinateKey
    ? weatherState.error ?? ""
    : "";
  const isLoading = Boolean(coordinateKey) && !weather && !error;

  useEffect(() => {
    if (latitude === null || longitude === null) return;
    const controller = new AbortController();
    const key = `${latitude},${longitude}`;
    const loadWeather = async () => {
      try {
        const currentWeather = await getCurrentWeather(latitude, longitude, {
          signal: controller.signal,
        });
        if (!controller.signal.aborted) {
          setWeatherState({ key, weather: currentWeather });
        }
      } catch (loadError) {
        if (!controller.signal.aborted) {
          setWeatherState({
            key,
            error: loadError instanceof Error
              ? loadError.message
              : "Could not load current weather.",
          });
        }
      } finally {
        if (!controller.signal.aborted) setIsRefreshing(false);
      }
    };
    void loadWeather();
    return () => controller.abort();
  }, [latitude, longitude, refreshToken]);

  return (
    <div className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs space-y-3.5">
      <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <span>🌦️</span> Current Weather
          </h3>
          <p className="text-[11px] text-slate-500 mt-0.5">
            {weather
              ? `${weather.latitude.toFixed(3)}, ${weather.longitude.toFixed(3)}`
              : "At your selected starting point"}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setIsRefreshing(true);
            setRefreshToken((value) => value + 1);
          }}
          disabled={isLoading || isRefreshing || !coordinates}
          className="text-[11px] font-semibold text-sky-700 hover:text-sky-900 disabled:opacity-50"
        >
          {isLoading || isRefreshing ? "Updating..." : "Refresh"}
        </button>
      </div>

      {weather ? (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            <WeatherMetric label="Temperature" value={`${weather.temperature_c.toFixed(1)}°C`} />
            <WeatherMetric label="Condition" value={describeWeather(weather.weather_code)} />
            <WeatherMetric label="Precipitation" value={`${weather.precipitation_mm.toFixed(1)} mm`} />
            <WeatherMetric label="Wind" value={`${weather.wind_speed_kmh.toFixed(1)} km/h`} />
          </div>
          <p className="text-[10px] text-slate-500">
            {weather.source} forecast • Model time {weather.time}
            {weather.elevation_m !== null
              ? ` • Elevation ${Math.round(weather.elevation_m)} m`
              : ""}
          </p>
        </>
      ) : (
        <p className={`text-xs ${error ? "text-rose-700" : "text-slate-500"}`}>
          {error || (isLoading ? "Loading current conditions..." : "Choose a starting point to load weather.")}
        </p>
      )}
    </div>
  );
}

function WeatherMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80">
      <span className="text-[10px] text-slate-500 block font-medium">{label}</span>
      <span className="text-base font-bold font-mono text-slate-900 block mt-0.5">
        {value}
      </span>
    </div>
  );
}
