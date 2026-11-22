"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useApp } from "../lib/context";

export default function Sidebar() {
  const pathname = usePathname();
  const { isMobileSidebarOpen, setIsMobileSidebarOpen, summary } = useApp();
  const activeAlertCount = summary?.active_alerts_count ?? 0;

  const navItems = [
    { href: "/", label: "Dashboard", icon: "" },
    { href: "/routes", label: "Routes", icon: "️" },
    {
      href: "/risk-zones",
      label: "Risk Zones",
      icon: "️",
      badge: activeAlertCount > 0 ? activeAlertCount : undefined,
      badgeColor: "bg-amber-100 text-amber-800",
    },
    { href: "/fleet", label: "Fleet", icon: "" },
    { href: "/consignments", label: "Consignments", icon: "" },
    { href: "/analytics", label: "Analytics", icon: "" },
    { href: "/reports", label: "Reports", icon: "" },
    { href: "/settings", label: "Settings", icon: "️" },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileSidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-[#182822]/40 backdrop-blur-xs lg:hidden transition-opacity cursor-pointer"
          onClick={() => setIsMobileSidebarOpen(false)}
        />
      )}

      {/* Sidebar Container: Deep Forest Theme (#182822) */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-[#182822] text-[#F9F6F0] border-r border-[#243B33] flex flex-col justify-between transition-transform duration-200 ease-in-out lg:translate-x-0 lg:static lg:z-auto ${
          isMobileSidebarOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full"
        }`}
      >
        {/* Top Section */}
        <div>
          <div className="p-5 border-b border-[#243B33] flex items-center justify-between">
            <Link
              href="/"
              onClick={() => setIsMobileSidebarOpen(false)}
              className="flex items-center gap-3 cursor-pointer group"
            >
              <div className="w-10 h-10 rounded-xl bg-[#243B33] border border-[#344F45] group-hover:bg-[#2F4A40] transition-colors flex items-center justify-center text-[#F9F6F0] shadow-xs">
                <svg
                  className="w-5 h-5 text-[#EFE9DE]"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="1.8"
                    d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
                  />
                </svg>
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <span className="font-serif font-semibold text-[#F9F6F0] text-lg tracking-tight">
                    NER-ResQ
                  </span>
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-sm bg-[#2A4239] text-[#D8C7B5] tracking-widest uppercase">
                    Core
                  </span>
                </div>
                <p className="text-[11px] font-normal text-[#96A79F] leading-tight">
                  Smart Logistics Intelligence
                </p>
              </div>
            </Link>

            {/* Mobile close button */}
            <button
              type="button"
              onClick={() => setIsMobileSidebarOpen(false)}
              className="lg:hidden p-1.5 rounded-lg text-[#96A79F] hover:text-[#F9F6F0] hover:bg-[#243B33] cursor-pointer"
              aria-label="Close menu"
            >
              
            </button>
          </div>

          {/* Regional Tagline */}
          <div className="px-5 py-2.5 bg-[#14221D] border-b border-[#243B33] text-[11px] text-[#AAB8B0] flex items-center gap-2">
            
            <span className="truncate tracking-wide">Northeast Corridor Active</span>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-1">
            {navItems.map((item) => {
              const isActive =
                item.href === "/"
                  ? pathname === "/"
                  : pathname === item.href || pathname.startsWith(`${item.href}/`);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setIsMobileSidebarOpen(false)}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-medium cursor-pointer transition-all ${
                    isActive
                      ? "bg-[#243B33] text-[#F9F6F0] font-semibold shadow-xs border-l-2 border-[#D4A392]"
                      : "text-[#B9C6BF] hover:text-[#FFFFFF] hover:bg-[#1E332B]"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-sm opacity-90">{item.icon}</span>
                    <span className="tracking-wide">{item.label}</span>
                  </div>

                  {item.badge !== undefined && (
                    <span
                      className="text-[10px] px-1.5 py-0.5 rounded-full font-bold bg-[#B87A68] text-white"
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Bottom Regional Node Footer */}
        <div className="p-4 border-t border-[#243B33] m-3 rounded-xl bg-[#14221D] border border-[#243B33]/80">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold text-[#83968D] uppercase tracking-wider">
              Control Hub
            </span>
            <span className="text-[10px] font-semibold text-[#52B788] flex items-center gap-1">
              
              Live Grid
            </span>
          </div>
          <p className="text-xs font-bold text-[#F9F6F0]">Guwahati Ops Center</p>
          <p className="text-[11px] text-[#96A79F] mt-0.5 font-mono">
            NH-6 • GS Road Corridor
          </p>
          <div className="mt-3 pt-2.5 border-t border-[#243B33] flex items-center justify-between text-[10px] text-[#83968D]">
            <span>NER-ResQ Platform</span>
            <span className="font-mono text-[#D8C7B5]">v1.2</span>
          </div>
        </div>
      </aside>
    </>
  );
}
