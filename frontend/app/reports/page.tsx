"use client";

import React, { useState } from "react";
import { useApp } from "../../lib/context";
import FieldReportModal from "../../components/FieldReportModal";
import { FieldReport } from "../../lib/types";

export default function ReportsPage() {
  const { fieldReports, isReportsLoading, refreshReports, submitReport } = useApp();
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedReport, setSelectedReport] = useState<FieldReport | null>(null);

  const filteredReports = fieldReports.filter((r) => {
    if (categoryFilter !== "all" && r.category.toLowerCase() !== categoryFilter.toLowerCase())
      return false;
    if (severityFilter !== "all" && r.severity.toLowerCase() !== severityFilter.toLowerCase())
      return false;
    if (
      search &&
      !r.description.toLowerCase().includes(search.toLowerCase()) &&
      !(r.location_name || "").toLowerCase().includes(search.toLowerCase()) &&
      !r.report_id.toLowerCase().includes(search.toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  const exportToCSV = () => {
    if (filteredReports.length === 0) return;

    const headers = [
      "Report ID",
      "Category",
      "Severity",
      "Latitude",
      "Longitude",
      "Location Name",
      "Description",
      "Reporter",
      "Timestamp",
      "Status",
    ];

    const rows = filteredReports.map((r) => [
      r.report_id,
      r.category,
      r.severity,
      r.location.lat,
      r.location.lng,
      `"${(r.location_name || "").replace(/"/g, '""')}"`,
      `"${r.description.replace(/"/g, '""')}"`,
      `"${(r.reporter_name || "Field Officer").replace(/"/g, '""')}"`,
      r.created_at,
      r.status || "verified",
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `ner_resq_field_reports_${new Date().toISOString().split("T")[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getSeverityPill = (sev: string) => {
    switch (sev.toLowerCase()) {
      case "critical":
        return "bg-rose-100 text-rose-800 border-rose-200";
      case "high":
        return "bg-amber-100 text-amber-800 border-amber-200";
      case "medium":
        return "bg-sky-100 text-sky-800 border-sky-200";
      default:
        return "bg-emerald-100 text-emerald-800 border-emerald-200";
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Title & Action Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200/80">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <span>📝</span> Field Incident & Ground Verification Reports
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Log, verify, and export geo-tagged obstacle reports submitted by corridor field officials
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={exportToCSV}
            className="px-3.5 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-2xs flex items-center gap-1.5 cursor-pointer transition-colors"
          >
            <span>📥</span>
            <span>Export CSV</span>
          </button>
          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            className="px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 active:bg-sky-700 text-white text-xs font-semibold shadow-xs flex items-center gap-1.5 cursor-pointer transition-colors"
          >
            <span>➕</span>
            <span>New Field Report</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white border border-slate-200/90 rounded-xl p-4 shadow-xs flex flex-wrap items-center justify-between gap-4">
        {/* Search Input */}
        <div className="relative w-full sm:w-72">
          <input
            type="text"
            placeholder="Search location, keyword, ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full text-xs pl-8 pr-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50/70 text-slate-900 focus:outline-none focus:ring-1 focus:ring-sky-500 focus:bg-white"
          />
          <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-slate-400">
            🔍
          </span>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-600">Category:</span>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="text-xs font-medium px-2.5 py-1.5 rounded-lg border border-slate-200 bg-slate-50 text-slate-800 focus:outline-none focus:ring-1 focus:ring-sky-500 cursor-pointer"
            >
              <option value="all">All Categories</option>
              <option value="landslide">Landslide</option>
              <option value="waterlogging">Waterlogging</option>
              <option value="road_blockage">Road Blockage</option>
              <option value="accident">Accident</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-600">Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="text-xs font-medium px-2.5 py-1.5 rounded-lg border border-slate-200 bg-slate-50 text-slate-800 focus:outline-none focus:ring-1 focus:ring-sky-500 cursor-pointer"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          <button
            type="button"
            onClick={() => refreshReports()}
            disabled={isReportsLoading}
            className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 cursor-pointer"
          >
            {isReportsLoading ? "Syncing..." : "↻ Refresh"}
          </button>
        </div>
      </div>

      {/* Reports Table & Details Modal */}
      <div className="bg-white border border-slate-200/90 rounded-xl shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-bold">
                <th className="py-3 px-4">Report ID</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Location / Landmark</th>
                <th className="py-3 px-4">Description</th>
                <th className="py-3 px-4">Reporter</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredReports.map((report) => (
                <tr
                  key={report.report_id}
                  className="hover:bg-slate-50/70 transition-colors"
                >
                  <td className="py-3 px-4 font-mono font-bold text-slate-900">
                    {report.report_id}
                  </td>
                  <td className="py-3 px-4 capitalize text-slate-700 font-semibold">
                    {report.category.replace("_", " ")}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${getSeverityPill(
                        report.severity
                      )}`}
                    >
                      {report.severity}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className="font-semibold text-slate-800 block">
                      {report.location_name || "NH-6 Monitored Sector"}
                    </span>
                    <span className="text-[10px] font-mono text-slate-400">
                      [{report.location.lat.toFixed(4)}, {report.location.lng.toFixed(4)}]
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-600 max-w-xs truncate">
                    {report.description}
                  </td>
                  <td className="py-3 px-4 text-slate-700 font-medium">
                    {report.reporter_name || "Field Officer"}
                  </td>
                  <td className="py-3 px-4">
                    <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 capitalize">
                      {report.status || "Verified"}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      type="button"
                      onClick={() => setSelectedReport(report)}
                      className="px-2.5 py-1 text-[11px] font-semibold rounded bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors cursor-pointer"
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              ))}

              {filteredReports.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    No field incident reports match the search criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail Dialog */}
      {selectedReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full p-6 space-y-4 text-xs animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <span className="font-bold text-base text-slate-900">
                  Incident Detail: {selectedReport.report_id}
                </span>
                <span
                  className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${getSeverityPill(
                    selectedReport.severity
                  )}`}
                >
                  {selectedReport.severity}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setSelectedReport(null)}
                className="text-slate-400 hover:text-slate-700 p-1 rounded cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2">
              <div>
                <span className="text-slate-400 font-medium block text-[10px]">Location</span>
                <span className="font-bold text-slate-800 text-sm">
                  {selectedReport.location_name || "NH-6 Monitored Sector"}
                </span>
                <span className="font-mono text-slate-500 text-[11px] block">
                  [{selectedReport.location.lat}, {selectedReport.location.lng}]
                </span>
              </div>

              <div>
                <span className="text-slate-400 font-medium block text-[10px]">Description</span>
                <p className="text-slate-700 leading-relaxed mt-0.5">
                  {selectedReport.description}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4 pt-2 border-t border-slate-100">
                <div>
                  <span className="text-slate-400 font-medium block text-[10px]">Reporter</span>
                  <span className="font-semibold text-slate-800">
                    {selectedReport.reporter_name || "Field Officer"}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 font-medium block text-[10px]">Recorded Time</span>
                  <span className="font-mono text-slate-700">{selectedReport.created_at}</span>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 text-right">
              <button
                type="button"
                onClick={() => setSelectedReport(null)}
                className="px-4 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Submission Modal */}
      <FieldReportModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={async (newRep) => {
          await submitReport(newRep);
        }}
      />
    </div>
  );
}
