"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { HealthResponse, MockScenario } from "../lib/types";
import { useApp } from "../lib/context";
import { CORRIDOR_OPTIONS } from "../lib/constants";
import SystemHealthBadge from "./SystemHealthBadge";

interface HeaderProps {
  health?: HealthResponse | null;
  isHealthLoading?: boolean;
  onRefreshHealth?: () => void;
  isMockMode?: boolean;
  onToggleMockMode?: (val: boolean) => void;
  mockScenario?: MockScenario;
  onSelectMockScenario?: (scenario: MockScenario) => void;
  activeAlertCount?: number;
  selectedCorridor?: string;
  onSelectCorridor?: (corridor: string) => void;
}

export { CORRIDOR_OPTIONS } from "../lib/constants";

export default function Header(props: HeaderProps) {
  const pathname = usePathname();
  const context = useApp();

  const health = props.health !== undefined ? props.health : context.health;
  const isHealthLoading =
    props.isHealthLoading !== undefined ? props.isHealthLoading : context.isHealthLoading;
  const onRefreshHealth = props.onRefreshHealth || context.refreshHealth;
  const isMockMode = props.isMockMode !== undefined ? props.isMockMode : context.isMockMode;
  const onToggleMockMode =
    props.onToggleMockMode || ((val: boolean) => context.setIsMockMode(val));
  const mockScenario =
    props.mockScenario !== undefined ? props.mockScenario : context.mockScenario;
  const onSelectMockScenario =
    props.onSelectMockScenario || ((sc: MockScenario) => context.setMockScenario(sc));
  const activeAlertCount =
    props.activeAlertCount !== undefined
      ? props.activeAlertCount
      : context.summary?.active_alerts_count ?? 0;
  const selectedCorridor =
    props.selectedCorridor !== undefined ? props.selectedCorridor : context.selectedCorridor;
  const onSelectCorridor =
    props.onSelectCorridor || ((c: string) => context.setSelectedCorridor(c));

  const [currentDateTime, setCurrentDateTime] = useState<string>("");
  const [showNotificationMenu, setShowNotificationMenu] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const datePart = now.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      });
      const timePart = now.toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      });
      setCurrentDateTime(`${datePart}, ${timePart} IST`);
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const navLinks = [
    { href: "/", label: "Dashboard" },
    { href: "/routes", label: "Routes" },
    {
      href: "/risk-zones",
      label: "Risk Zones",
      badge: activeAlertCount > 0 ? activeAlertCount : undefined,
    },
    { href: "/fleet", label: "Fleet" },
    { href: "/consignments", label: "Consignments" },
    { href: "/analytics", label: "Analytics" },
    { href: "/reports", label: "Reports" },
    // { href: "/settings", label: "Settings" }, // Abstracted per design requirements
  ];

  return (
    <header className="w-full bg-[#182822] text-[#F9F6F0] sticky top-0 z-50 shadow-md border-b border-[#243B33] backdrop-blur-md">
      {/* Top Banner Bar: Brand, Status, Controls */}
      <div className="w-full px-4 sm:px-6 lg:px-8 border-b border-[#243B33]/80">
        <div className="max-w-[1600px] mx-auto py-3 flex items-center justify-between gap-4">
          {/* Brand Logo & Title */}
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-3 group">
              <div className="w-9 h-9 rounded-lg bg-[#243B33] border border-[#344F45] group-hover:bg-[#2D473E] transition-colors flex items-center justify-center text-[#F9F6F0] shadow-xs">
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
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <span className="font-serif font-semibold text-[#F9F6F0] text-xl tracking-tight leading-none">
                    NER-ResQ
                  </span>
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-[#2A4239] text-[#D8C7B5] tracking-widest uppercase">
                    Core
                  </span>
                </div>
                <span className="text-[10px] text-[#96A79F] tracking-wide mt-0.5 hidden sm:inline">
                  Smart Logistics Intelligence
                </span>
              </div>
            </Link>

            {/* Active Corridor Selector: Abstracted per request */}
            {/*
            <div className="hidden md:flex items-center gap-2 pl-4 border-l border-[#243B33]">
              <div className="relative">
                <select
                  value={selectedCorridor}
                  onChange={(e) => onSelectCorridor(e.target.value)}
                  className="text-xs font-semibold px-2.5 py-1 rounded-md bg-[#243B33] border border-[#344F45] text-[#EFE9DE] hover:border-[#4B6B5F] focus:outline-none focus:ring-1 focus:ring-[#D4A392] cursor-pointer pr-6 appearance-none"
                >
                  {CORRIDOR_OPTIONS.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} {c.isSupported ? "(Active)" : "(Planned)"}
                    </option>
                  ))}
                </select>
                <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[9px] text-[#AAB8B0] pointer-events-none">
                  ▼
                </span>
              </div>
            </div>
            */}
          </div>

          {/* Right Operational Controls */}
          <div className="flex items-center gap-3">
            {/* Live IST Timestamp */}
            {currentDateTime && (
              <span className="hidden xl:inline text-[11px] font-mono text-[#AAB8B0] bg-[#14221D] px-2.5 py-1 rounded border border-[#243B33]">
                {currentDateTime}
              </span>
            )}

            {/* Mode Switch: Abstracted / Commented out per request */}
            {/*
            <div className="flex items-center bg-[#14221D] p-0.5 rounded-lg border border-[#243B33]">
              <button
                type="button"
                onClick={() => onToggleMockMode(false)}
                className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all cursor-pointer ${
                  !isMockMode
                    ? "bg-[#243B33] text-[#F9F6F0] shadow-xs font-bold"
                    : "text-[#83968D] hover:text-[#EFE9DE]"
                }`}
              >
                Live API
              </button>
              <button
                type="button"
                onClick={() => onToggleMockMode(true)}
                className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all cursor-pointer ${
                  isMockMode
                    ? "bg-[#D4A392] text-[#182822] shadow-xs font-bold"
                    : "text-[#83968D] hover:text-[#EFE9DE]"
                }`}
              >
                Mock
              </button>
            </div>
            */}

            {/* Notifications Menu Trigger */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setShowNotificationMenu(!showNotificationMenu)}
                className="p-1.5 rounded-lg bg-[#243B33] border border-[#344F45] text-[#D8C7B5] hover:text-white relative cursor-pointer"
                title="Operational alerts"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="1.8"
                    d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                  />
                </svg>
                {activeAlertCount > 0 && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-[#B87A68] text-white text-[9px] font-bold flex items-center justify-center">
                    {activeAlertCount}
                  </span>
                )}
              </button>

              {/* Notification Dropdown */}
              {showNotificationMenu && (
                <div className="absolute right-0 top-10 w-80 p-3 bg-[#FAF8F5] text-[#1E2E28] border border-[#E8E1D5] rounded-xl shadow-xl z-50 text-xs space-y-2">
                  <div className="flex items-center justify-between pb-2 border-b border-[#E8E1D5]">
                    <span className="font-bold text-[#182822]">Operational Alerts</span>
                    <span className="text-[10px] text-[#8C9891]">Northeast Dispatch</span>
                  </div>
                  <div className="space-y-2 max-h-56 overflow-y-auto">
                    {context.alerts.length === 0 ? (
                      <p className="py-4 text-center text-[#8C9891]">No active alerts.</p>
                    ) : (
                      context.alerts.map((alert) => (
                        <div
                          key={alert.alert_id}
                          className="p-2 rounded-lg bg-white border border-[#E8E1D5]"
                        >
                          <div className="flex items-center justify-between font-semibold text-[#182822]">
                            <span>{alert.title}</span>
                            <span className="text-[10px] uppercase text-[#8C9891]">
                              {alert.severity}
                            </span>
                          </div>
                          <p className="text-[11px] text-[#5D6B64] mt-0.5">{alert.message}</p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* System Health Diagnostic Badge: Abstracted / Commented out per request */}
            {/*
            <SystemHealthBadge
              health={health}
              isLoading={isHealthLoading}
              onRefresh={onRefreshHealth}
              isMockMode={isMockMode}
            />
            */}

            {/* Mobile Hamburger Button */}
            <button
              type="button"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="lg:hidden p-1.5 rounded-lg bg-[#243B33] border border-[#344F45] text-[#EFE9DE] cursor-pointer"
              aria-label="Toggle navigation menu"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Primary Navigation Bar (Horizontal Tab Strip) */}
      <div className="w-full px-4 sm:px-6 lg:px-8 bg-[#14221D]">
        <div className="max-w-[1600px] mx-auto flex items-center justify-between">
          <nav className="hidden lg:flex items-center gap-1 py-1.5">
            {navLinks.map((link) => {
              const isActive =
                link.href === "/"
                  ? pathname === "/"
                  : pathname === link.href || pathname.startsWith(`${link.href}/`);

              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`px-4 py-2 rounded-md text-xs tracking-wider transition-all flex items-center gap-2 cursor-pointer ${
                    isActive
                      ? "bg-[#243B33] text-[#F9F6F0] font-semibold border-b-2 border-[#D4A392]"
                      : "text-[#AAB8B0] hover:text-[#FFFFFF] hover:bg-[#1E332B]"
                  }`}
                >
                  <span>{link.label}</span>
                  {link.badge !== undefined && (
                    <span className="text-[9px] px-1.5 py-0.2 rounded-full font-bold bg-[#B87A68] text-white">
                      {link.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Status Capsule Indicator */}
          <div className="hidden lg:flex items-center gap-2 text-[11px] text-[#AAB8B0] py-2">
            <span className="w-2 h-2 rounded-full bg-[#52B788] animate-pulse"></span>
            <span className="font-mono text-[#D8C7B5]">NH-6 Monitored Corridor • Live Grid</span>
          </div>
        </div>

        {/* Mobile Navigation Drawer */}
        {isMobileMenuOpen && (
          <div className="lg:hidden py-3 border-t border-[#243B33] space-y-3">
            <nav className="space-y-1">
              {navLinks.map((link) => {
                const isActive =
                  link.href === "/"
                    ? pathname === "/"
                    : pathname === link.href || pathname.startsWith(`${link.href}/`);

                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setIsMobileMenuOpen(false)}
                    className={`flex items-center justify-between px-3 py-2.5 rounded-md text-xs font-medium cursor-pointer ${
                      isActive
                        ? "bg-[#243B33] text-[#F9F6F0] font-bold"
                        : "text-[#AAB8B0] hover:bg-[#1E332B] hover:text-white"
                    }`}
                  >
                    <span>{link.label}</span>
                    {link.badge !== undefined && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded-full font-bold bg-[#B87A68] text-white">
                        {link.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}
