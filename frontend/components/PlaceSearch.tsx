"use client";

import React, { useEffect, useRef, useState } from "react";
import { Coordinates, PlaceResult } from "../lib/types";
import { searchPlaces } from "../lib/api";

interface PlaceSearchProps {
  label: string;
  location: Coordinates | null;
  allowCurrentLocation?: boolean;
  onSelect: (coordinates: Coordinates) => void;
}

function locationKey(location: Coordinates | null): string {
  return location ? `${location.lat},${location.lng}` : "";
}

export default function PlaceSearch({
  label,
  location,
  allowCurrentLocation = false,
  onSelect,
}: PlaceSearchProps) {
  const [query, setQuery] = useState("");
  const [selectedQuery, setSelectedQuery] = useState("");
  const [results, setResults] = useState<PlaceResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isGettingLocation, setIsGettingLocation] = useState(false);
  const [didSearch, setDidSearch] = useState(false);
  const [error, setError] = useState("");
  const lastSelectedLocation = useRef("");
  const previousLocation = useRef(locationKey(location));

  useEffect(() => {
    const key = locationKey(location);
    if (key !== previousLocation.current) {
      if (key !== lastSelectedLocation.current) {
        setQuery("");
        setSelectedQuery("");
        setResults([]);
        setIsSearching(false);
        setDidSearch(false);
      }
      previousLocation.current = key;
      lastSelectedLocation.current = "";
    }
  }, [location]);

  useEffect(() => {
    const normalizedQuery = query.trim();
    if (normalizedQuery.length < 3 || normalizedQuery === selectedQuery) {
      return;
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(async () => {
      setIsSearching(true);
      setError("");
      try {
        setResults(await searchPlaces(normalizedQuery, { signal: controller.signal }));
        setDidSearch(true);
      } catch (searchError) {
        if (!controller.signal.aborted) {
          setResults([]);
          setDidSearch(true);
          setError(
            searchError instanceof Error
              ? searchError.message
              : "Place search failed. Please try again."
          );
        }
      } finally {
        if (!controller.signal.aborted) setIsSearching(false);
      }
    }, 1000);

    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [query, selectedQuery]);

  const choosePlace = (place: PlaceResult) => {
    lastSelectedLocation.current = locationKey(place);
    setQuery(place.display_name);
    setSelectedQuery(place.display_name);
    setResults([]);
    setDidSearch(false);
    setError("");
    onSelect({ lat: place.lat, lng: place.lng });
  };

  const useCurrentLocation = () => {
    if (!navigator.geolocation) {
      setError("Location access is not supported by this browser.");
      return;
    }
    setIsGettingLocation(true);
    setError("");
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        const current = { lat: coords.latitude, lng: coords.longitude };
        lastSelectedLocation.current = locationKey(current);
        setQuery("Current location");
        setSelectedQuery("Current location");
        setResults([]);
        setIsSearching(false);
        setIsGettingLocation(false);
        onSelect(current);
      },
      (locationError) => {
        setError(locationError.message || "Could not access your current location.");
        setIsGettingLocation(false);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 }
    );
  };

  return (
    <div className="space-y-1.5">
      <label className="text-[10px] text-slate-500 font-medium block">
        Search {label} in Northeast India
      </label>
      <div className="relative flex gap-1.5">
        <input
          type="search"
          role="combobox"
          aria-label={`Search ${label}`}
          aria-expanded={results.length > 0}
          aria-controls={`place-results-${label.toLowerCase().replace(/\s+/g, "-")}`}
          aria-autocomplete="list"
          placeholder={`Search a place or address`}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setSelectedQuery("");
            setResults([]);
            setIsSearching(false);
            setDidSearch(false);
            setError("");
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter" && results[0]) {
              event.preventDefault();
              choosePlace(results[0]);
            }
          }}
          className="min-w-0 flex-1 text-xs px-3 py-2 rounded-lg border border-slate-200 bg-slate-50/70 text-slate-900 focus:outline-none focus:ring-1 focus:ring-sky-500 focus:bg-white"
        />
        {allowCurrentLocation && (
          <button
            type="button"
            onClick={useCurrentLocation}
            disabled={isGettingLocation}
            className="shrink-0 rounded-lg border border-slate-200 px-2.5 text-[11px] font-semibold text-slate-700 hover:bg-sky-50 disabled:opacity-60"
          >
            {isGettingLocation ? "Locating..." : "Use my location"}
          </button>
        )}
        {results.length > 0 && (
          <ul
            id={`place-results-${label.toLowerCase().replace(/\s+/g, "-")}`}
            role="listbox"
            className="absolute left-0 right-0 top-full z-30 mt-1 max-h-56 overflow-auto rounded-lg border border-slate-200 bg-white shadow-lg"
          >
            {results.map((place) => (
              <li key={`${place.lat},${place.lng},${place.display_name}`} role="option" aria-selected="false">
                <button
                  type="button"
                  onClick={() => choosePlace(place)}
                  className="w-full px-3 py-2 text-left text-xs text-slate-700 hover:bg-sky-50"
                >
                  {place.display_name}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      {(isSearching || error) && (
        <p className={`text-[10px] ${error ? "text-rose-600" : "text-slate-500"}`}>
          {error || "Searching OpenStreetMap places..."}
        </p>
      )}
      {didSearch && query.trim().length >= 3 && !isSearching && !error && results.length === 0 && !selectedQuery && (
        <p className="text-[10px] text-slate-500">No matching places found.</p>
      )}
    </div>
  );
}
