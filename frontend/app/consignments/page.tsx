"use client";

import React, { useState } from "react";
import { useApp } from "../../lib/context";
import { Consignment, LifecycleStatus } from "../../lib/types";
import { COMMODITY_OPTIONS } from "../../lib/constants";
import { updateConsignment } from "../../lib/api";

export default function ConsignmentsPage() {
  const {
    consignments,
    isConsignmentsLoading,
    refreshConsignments,
    registerConsignment,
    vehicles,
  } = useApp();

  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [commodityFilter, setCommodityFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedConsignment, setSelectedConsignment] = useState<Consignment | null>(null);

  // New Shipment Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newCommodity, setNewCommodity] = useState<string>("Medicine");
  const [newQuantity, setNewQuantity] = useState("");
  const [newOrigin, setNewOrigin] = useState("Guwahati Central Medical Depot");
  const [newDestination, setNewDestination] = useState("Shillong Civil Hospital");
  const [newVehicle, setNewVehicle] = useState("V001");
  const [newNotes, setNewNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const filteredConsignments = consignments.filter((c) => {
    if (statusFilter !== "all" && c.lifecycle_status !== statusFilter) return false;
    if (commodityFilter !== "all" && c.commodity_type !== commodityFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchId = c.shipment_id.toLowerCase().includes(q);
      const matchCargo = c.quantity.toLowerCase().includes(q);
      const matchOrigin = c.origin.toLowerCase().includes(q);
      const matchDest = c.destination.toLowerCase().includes(q);
      if (!matchId && !matchCargo && !matchOrigin && !matchDest) return false;
    }
    return true;
  });

  const getStatusBadge = (status: LifecycleStatus) => {
    switch (status) {
      case "Dispatched":
        return "bg-sky-50 text-sky-700 border-sky-200";
      case "In Transit":
        return "bg-blue-50 text-blue-700 border-blue-300";
      case "Delayed due to Risk":
        return "bg-rose-50 text-rose-700 border-rose-300";
      case "Delivered":
        return "bg-emerald-50 text-emerald-700 border-emerald-300";
      default:
        return "bg-slate-50 text-slate-700 border-slate-200";
    }
  };

  const handleUpdateStatus = async (shipmentId: string, newStatus: LifecycleStatus) => {
    try {
      await updateConsignment(shipmentId, { lifecycle_status: newStatus });
      await refreshConsignments();
      if (selectedConsignment && selectedConsignment.shipment_id === shipmentId) {
        setSelectedConsignment((prev) => (prev ? { ...prev, lifecycle_status: newStatus } : null));
      }
    } catch (e) {
      console.error("Failed to update consignment status", e);
    }
  };

  const handleCreateShipment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newQuantity.trim() || !newOrigin.trim() || !newDestination.trim()) {
      setSubmitError("Please fill out all required fields.");
      return;
    }
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      await registerConsignment({
        commodity_type: newCommodity,
        quantity: newQuantity,
        origin: newOrigin,
        destination: newDestination,
        assigned_vehicle_id: newVehicle || undefined,
        lifecycle_status: "Dispatched",
        notes: newNotes || undefined,
      });
      setIsCreateModalOpen(false);
      setNewQuantity("");
      setNewNotes("");
      await refreshConsignments();
    } catch (err: any) {
      setSubmitError(err?.message || "Failed to create consignment.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Primary Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200/80">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
             Essential Commodities & Consignment Lifecycle Tracking
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Monitor disaster relief cargo, pharmaceuticals, food rations, and hazardous fuel shipments along Northeast road corridors
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => refreshConsignments()}
            disabled={isConsignmentsLoading}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 cursor-pointer shadow-2xs"
          >
            {isConsignmentsLoading ? "Syncing..." : "↻ Refresh"}
          </button>
          <button
            type="button"
            onClick={() => setIsCreateModalOpen(true)}
            className="px-3.5 py-1.5 text-xs font-bold rounded-lg bg-sky-600 hover:bg-sky-500 text-white cursor-pointer shadow-xs flex items-center gap-1.5 transition-colors"
          >
            <span>+</span> Register Shipment
          </button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl border border-slate-200/90 bg-white shadow-xs">
          <span className="text-[11px] font-semibold text-slate-500 block">Total Active Shipments</span>
          <span className="text-xl font-extrabold text-slate-900 font-mono mt-0.5 block">
            {consignments.length}
          </span>
        </div>
        <div className="p-3.5 rounded-xl border border-blue-200/80 bg-blue-50/50 shadow-xs">
          <span className="text-[11px] font-semibold text-blue-700 block">In Transit</span>
          <span className="text-xl font-extrabold text-blue-900 font-mono mt-0.5 block">
            {consignments.filter((c) => c.lifecycle_status === "In Transit").length}
          </span>
        </div>
        <div className="p-3.5 rounded-xl border border-rose-200/80 bg-rose-50/50 shadow-xs">
          <span className="text-[11px] font-semibold text-rose-700 block">Delayed Due to Risk</span>
          <span className="text-xl font-extrabold text-rose-900 font-mono mt-0.5 block">
            {consignments.filter((c) => c.lifecycle_status === "Delayed due to Risk").length}
          </span>
        </div>
        <div className="p-3.5 rounded-xl border border-emerald-200/80 bg-emerald-50/50 shadow-xs">
          <span className="text-[11px] font-semibold text-emerald-700 block">Successfully Delivered</span>
          <span className="text-xl font-extrabold text-emerald-900 font-mono mt-0.5 block">
            {consignments.filter((c) => c.lifecycle_status === "Delivered").length}
          </span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white border border-slate-200/90 rounded-xl p-3.5 shadow-xs flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          {/* Status Filter */}
          <div className="flex items-center gap-1.5 text-xs">
            <span className="font-bold text-slate-500 text-[11px]">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs px-2.5 py-1 rounded-lg border border-slate-200 bg-slate-50 text-slate-700 focus:outline-none focus:ring-1 focus:ring-sky-500"
            >
              <option value="all">All Lifecycles</option>
              <option value="Dispatched">Dispatched</option>
              <option value="In Transit">In Transit</option>
              <option value="Delayed due to Risk">Delayed due to Risk</option>
              <option value="Delivered">Delivered</option>
            </select>
          </div>

          {/* Commodity Filter */}
          <div className="flex items-center gap-1.5 text-xs">
            <span className="font-bold text-slate-500 text-[11px]">Commodity:</span>
            <select
              value={commodityFilter}
              onChange={(e) => setCommodityFilter(e.target.value)}
              className="text-xs px-2.5 py-1 rounded-lg border border-slate-200 bg-slate-50 text-slate-700 focus:outline-none focus:ring-1 focus:ring-sky-500"
            >
              <option value="all">All Commodities</option>
              {COMMODITY_OPTIONS.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Search Input */}
        <div className="w-full md:w-64">
          <input
            type="text"
            placeholder="Search by ID, cargo, or town..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full text-xs px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50 text-slate-900 focus:outline-none focus:ring-1 focus:ring-sky-500"
          />
        </div>
      </div>

      {/* Main Consignment Data Table */}
      <div className="bg-white border border-slate-200/90 rounded-xl shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 text-slate-500 font-semibold border-b border-slate-100">
              <tr>
                <th className="py-3 px-4">Shipment ID</th>
                <th className="py-3 px-4">Commodity / Cargo</th>
                <th className="py-3 px-4">Quantity</th>
                <th className="py-3 px-4">Route Path (Origin → Destination)</th>
                <th className="py-3 px-4">Assigned Vehicle</th>
                <th className="py-3 px-4">Risk Exposure</th>
                <th className="py-3 px-4">Lifecycle Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredConsignments.map((item) => (
                <tr key={item.shipment_id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="py-3 px-4 font-mono font-bold text-slate-900">
                    {item.shipment_id}
                  </td>
                  <td className="py-3 px-4">
                    <span className="font-semibold text-slate-800 block">
                      {item.commodity_type}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-600 font-medium">
                    {item.quantity}
                  </td>
                  <td className="py-3 px-4 max-w-xs">
                    <span className="text-slate-800 font-medium block truncate">
                      {item.origin}
                    </span>
                    <span className="text-[10px] text-slate-400 block truncate">
                      ↓ to {item.destination}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    {item.assigned_vehicle_id ? (
                      <span className="font-mono font-semibold px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-800 text-[11px]">
                         {item.assigned_vehicle_id}
                      </span>
                    ) : (
                      <span className="text-slate-400 italic text-[11px]">Unassigned</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                        (item.risk_score || 0) > 66
                          ? "bg-rose-50 text-rose-700 border-rose-200"
                          : (item.risk_score || 0) > 33
                          ? "bg-amber-50 text-amber-700 border-amber-200"
                          : "bg-emerald-50 text-emerald-700 border-emerald-200"
                      }`}
                    >
                      {item.risk_score !== null && item.risk_score !== undefined
                        ? `Risk ${item.risk_score}/100`
                        : "Low Risk"}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${getStatusBadge(
                        item.lifecycle_status
                      )}`}
                    >
                      {item.lifecycle_status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      type="button"
                      onClick={() => setSelectedConsignment(item)}
                      className="px-2.5 py-1 text-[11px] font-semibold rounded bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors cursor-pointer"
                    >
                      Manage
                    </button>
                  </td>
                </tr>
              ))}

              {filteredConsignments.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    No consignments match the selected filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Details & Status Management Modal */}
      {selectedConsignment && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6 space-y-4 border border-slate-100">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                   Shipment: {selectedConsignment.shipment_id}
                </h3>
                <span className="text-xs text-slate-500 block">
                  Commodity: {selectedConsignment.commodity_type}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setSelectedConsignment(null)}
                className="text-slate-400 hover:text-slate-600 text-lg p-1 cursor-pointer"
              >
                
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3 rounded-xl border border-slate-100">
                <div>
                  <span className="text-slate-400 font-medium block text-[10px]">Cargo Quantity</span>
                  <span className="font-bold text-slate-800">{selectedConsignment.quantity}</span>
                </div>
                <div>
                  <span className="text-slate-400 font-medium block text-[10px]">Assigned Fleet</span>
                  <span className="font-bold text-slate-800">
                    {selectedConsignment.assigned_vehicle_id || "None"}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 font-medium block text-[10px]">Origin Point</span>
                  <span className="font-semibold text-slate-700">{selectedConsignment.origin}</span>
                </div>
                <div>
                  <span className="text-slate-400 font-medium block text-[10px]">Destination</span>
                  <span className="font-semibold text-slate-700">{selectedConsignment.destination}</span>
                </div>
              </div>

              {selectedConsignment.notes && (
                <div>
                  <span className="text-slate-400 font-medium block text-[10px]">Consignment Notes</span>
                  <p className="text-slate-700 leading-relaxed mt-0.5 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                    {selectedConsignment.notes}
                  </p>
                </div>
              )}

              {/* Lifecycle Progress Buttons */}
              <div className="pt-2">
                <span className="text-slate-500 font-bold block text-[11px] mb-2">
                  Update Delivery Milestone:
                </span>
                <div className="grid grid-cols-2 gap-2">
                  {(["Dispatched", "In Transit", "Delayed due to Risk", "Delivered"] as LifecycleStatus[]).map(
                    (st) => (
                      <button
                        key={st}
                        type="button"
                        onClick={() => handleUpdateStatus(selectedConsignment.shipment_id, st)}
                        className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
                          selectedConsignment.lifecycle_status === st
                            ? "bg-sky-600 text-white border-sky-600 shadow-2xs"
                            : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                        }`}
                      >
                        {st}
                      </button>
                    )
                  )}
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 text-right">
              <button
                type="button"
                onClick={() => setSelectedConsignment(null)}
                className="px-4 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold cursor-pointer"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Register Shipment Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6 space-y-4 border border-slate-100">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <span>+</span> Register New Essential Commodity Cargo
                </h3>
                <span className="text-xs text-slate-500 block">
                  Assign priority commodities to corridors and fleet vehicles
                </span>
              </div>
              <button
                type="button"
                onClick={() => setIsCreateModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-lg p-1 cursor-pointer"
              >
                
              </button>
            </div>

            <form onSubmit={handleCreateShipment} className="space-y-3 text-xs">
              {submitError && (
                <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs">
                  {submitError}
                </div>
              )}

              <div>
                <label className="text-slate-700 font-semibold block mb-1">Commodity Type</label>
                <select
                  value={newCommodity}
                  onChange={(e) => setNewCommodity(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-sky-500"
                >
                  {COMMODITY_OPTIONS.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label} ({c.priority} Priority)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-slate-700 font-semibold block mb-1">Cargo Quantity / Details</label>
                <input
                  type="text"
                  placeholder="e.g., 300 Vaccine Coolers, 500 Sacks of Rice"
                  value={newQuantity}
                  onChange={(e) => setNewQuantity(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-sky-500"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-700 font-semibold block mb-1">Origin Facility</label>
                  <input
                    type="text"
                    value={newOrigin}
                    onChange={(e) => setNewOrigin(e.target.value)}
                    className="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-sky-500"
                    required
                  />
                </div>
                <div>
                  <label className="text-slate-700 font-semibold block mb-1">Destination Target</label>
                  <input
                    type="text"
                    value={newDestination}
                    onChange={(e) => setNewDestination(e.target.value)}
                    className="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-sky-500"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-700 font-semibold block mb-1">Assign Fleet Vehicle</label>
                <select
                  value={newVehicle}
                  onChange={(e) => setNewVehicle(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-sky-500"
                >
                  <option value="">No Vehicle Assigned Yet</option>
                  {vehicles.map((v) => (
                    <option key={v.vehicle_id} value={v.vehicle_id}>
                      {v.vehicle_id} (Lat: {v.lat.toFixed(3)}, Lng: {v.lng.toFixed(3)})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-slate-700 font-semibold block mb-1">Operational Instructions</label>
                <textarea
                  rows={2}
                  placeholder="e.g., Cold-chain maintenance, avoid flooded culvert NH-6..."
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-3.5 py-1.5 rounded-lg border border-slate-200 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-bold cursor-pointer shadow-xs"
                >
                  {isSubmitting ? "Registering..." : "Create Consignment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
