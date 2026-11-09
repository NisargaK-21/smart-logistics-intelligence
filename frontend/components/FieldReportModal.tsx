"use client";

import React, { useState } from "react";
import { FieldReportCreate } from "../lib/types";

interface FieldReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (report: FieldReportCreate) => Promise<void>;
}

export default function FieldReportModal({
  isOpen,
  onClose,
  onSubmit,
}: FieldReportModalProps) {
  const [category, setCategory] = useState("landslide");
  const [severity, setSeverity] = useState("high");
  const [lat, setLat] = useState("25.9000");
  const [lng, setLng] = useState("91.7600");
  const [locationName, setLocationName] = useState("NH-6 Umsning Bypass");
  const [reporterName, setReporterName] = useState("Field Officer");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const latNum = parseFloat(lat);
    const lngNum = parseFloat(lng);

    if (isNaN(latNum) || isNaN(lngNum)) {
      setError("Please provide valid coordinates.");
      return;
    }

    if (description.trim().length < 5) {
      setError("Please provide a detailed incident description (at least 5 characters).");
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit({
        category,
        severity,
        location: { lat: latNum, lng: lngNum },
        location_name: locationName,
        description,
        reporter_name: reporterName,
      });
      onClose();
    } catch {
      setError("Failed to submit report. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">📝</span>
            <h2 className="text-base font-bold text-slate-900">
              Submit Ground Incident Report
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 p-1.5 rounded-lg text-sm cursor-pointer"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs">
          {error && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 font-medium">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="font-semibold text-slate-700 block mb-1">
                Hazard Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-800 focus:outline-none focus:ring-1 focus:ring-sky-500 cursor-pointer"
              >
                <option value="landslide">Landslide / Mudslide</option>
                <option value="waterlogging">Flash Flood / Waterlogging</option>
                <option value="road_blockage">Road Blockage / Debris</option>
                <option value="accident">Traffic Incident / Breakdown</option>
              </select>
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">
                Severity Level
              </label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-800 focus:outline-none focus:ring-1 focus:ring-sky-500 cursor-pointer"
              >
                <option value="critical">Critical (Road Impassable)</option>
                <option value="high">High (Severe Disruption)</option>
                <option value="medium">Medium (Passable with Caution)</option>
                <option value="low">Low (Minor Advisory)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="font-semibold text-slate-700 block mb-1">
              Location Description / Landmark
            </label>
            <input
              type="text"
              value={locationName}
              onChange={(e) => setLocationName(e.target.value)}
              placeholder="e.g. NH-6 KM 48 near Byrnihat Bridge"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-900 focus:outline-none focus:ring-1 focus:ring-sky-500"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="font-semibold text-slate-700 block mb-1">
                Latitude (e.g. 25.9000)
              </label>
              <input
                type="number"
                step="any"
                value={lat}
                onChange={(e) => setLat(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 font-mono text-slate-900 focus:outline-none focus:ring-1 focus:ring-sky-500"
                required
              />
            </div>
            <div>
              <label className="font-semibold text-slate-700 block mb-1">
                Longitude (e.g. 91.7600)
              </label>
              <input
                type="number"
                step="any"
                value={lng}
                onChange={(e) => setLng(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 font-mono text-slate-900 focus:outline-none focus:ring-1 focus:ring-sky-500"
                required
              />
            </div>
          </div>

          <div>
            <label className="font-semibold text-slate-700 block mb-1">
              Reporter Name / Department
            </label>
            <input
              type="text"
              value={reporterName}
              onChange={(e) => setReporterName(e.target.value)}
              placeholder="e.g. Officer Sharma (Highway Patrol)"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-900 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
          </div>

          <div>
            <label className="font-semibold text-slate-700 block mb-1">
              Field Incident Observations
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe road conditions, width restrictions, water depth, or clearing progress..."
              className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-900 focus:outline-none focus:ring-1 focus:ring-sky-500"
              required
            />
          </div>

          <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50 font-semibold cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold shadow-xs transition-colors cursor-pointer"
            >
              {isSubmitting ? "Submitting..." : "Submit Verified Report"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
