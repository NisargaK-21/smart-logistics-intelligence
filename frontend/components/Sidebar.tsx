"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useApp } from "../lib/context";

export default function Sidebar() {
  const pathname = usePathname();
  const { isMobileSidebarOpen, setIsMobileSidebarOpen, summary } = useApp();
  const activeAlertCount = summary?.active_alerts_count || 3;

  const navItems = [
    { href: "/", label: "Dashboard", icon: "📊" },
    { href: "/routes", label: "Routes", icon: "🛣️" },
    {
      href: "/risk-zones",
      label: "Risk Zones",
      icon: "⚠️",
      badge: activeAlertCount > 0 ? activeAlertCount : undefined,
      badgeColor: "bg-amber-100 text-amber-800",
    },
    { href: "/fleet", label: "Fleet", icon: "🚚" },
    { href: "/analytics", label: "Analytics", icon: "📈" },
    { href: "/reports", label: "Reports", icon: "📝" },
    { href: "/settings", label: "Settings", icon: "⚙️" },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileSidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/30 backdrop-blur-xs lg:hidden transition-opacity cursor-pointer"
          onClick={() => setIsMobileSidebarOpen(false)}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-slate-200/90 flex flex-col justify-between transition-transform duration-200 ease-in-out lg:translate-x-0 lg:static lg:z-auto ${
          isMobileSidebarOpen ? "translate-x-0 shadow-xl" : "-translate-x-full"
        }`}
      >
        {/* Top Section */}
        <div>
          <div className="p-5 border-b border-slate-100 flex items-center justify-between">
            <Link
              href="/"
              onClick={() => setIsMobileSidebarOpen(false)}
              className="flex items-center gap-3 cursor-pointer group"
            >
              <div className="w-10 h-10 rounded-xl bg-sky-600 group-hover:bg-sky-500 transition-colors flex items-center justify-center text-white shadow-xs">
                <svg
                  className="w-5 h-5 text-white"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2.2"
                    d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
                  />
                </svg>
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <span className="font-extrabold text-slate-900 text-base tracking-tight">
                    NER-ResQ
                  </span>
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-sm bg-sky-100 text-sky-700 tracking-wider">
                    SaaS
                  </span>
                </div>
                <p className="text-[11px] font-medium text-slate-500 leading-tight">
                  Smart Logistics Intelligence
                </p>
              </div>
            </Link>

            {/* Mobile close button */}
            <button
              type="button"
              onClick={() => setIsMobileSidebarOpen(false)}
              className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 cursor-pointer"
              aria-label="Close menu"
            >
              ✕
            </button>
          </div>

          {/* Regional Tagline */}
          <div className="px-5 py-2.5 bg-slate-50/80 border-b border-slate-100 text-[11px] text-slate-600 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0"></span>
            <span className="truncate">Northeast Corridor Active</span>
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
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium cursor-pointer transition-all ${
                    isActive
                      ? "bg-sky-50 text-sky-700 font-semibold shadow-2xs border-l-3 border-sky-600"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <span className="text-sm">{item.icon}</span>
                    <span>{item.label}</span>
                  </div>

                  {item.badge !== undefined && (
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${
                        item.badgeColor || "bg-slate-100 text-slate-700"
                      }`}
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
        <div className="p-4 border-t border-slate-100 m-3 rounded-xl bg-slate-50/70 border">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              Control Hub
            </span>
            <span className="text-[10px] font-semibold text-emerald-600 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block"></span>
              Live Grid
            </span>
          </div>
          <p className="text-xs font-bold text-slate-800">Guwahati Ops Center</p>
          <p className="text-[11px] text-slate-500 mt-0.5 font-mono">
            NH-6 • GS Road Corridor
          </p>
          <div className="mt-3 pt-2.5 border-t border-slate-200/60 flex items-center justify-between text-[10px] text-slate-500">
            <span>NER-ResQ Platform</span>
            <span className="font-mono">v1.2</span>
          </div>
        </div>
      </aside>
    </>
  );
}
