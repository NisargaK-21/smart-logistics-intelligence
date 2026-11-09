"use client";

import React from "react";
import Sidebar from "./Sidebar";
import Header from "./Header";

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      <div className="flex-1 flex w-full">
        {/* Module 1: Persistent Sidebar Navigation */}
        <Sidebar />

        {/* Main Application Area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Module 2: Persistent Top Header */}
          <Header />

          {/* Dynamic Page Content */}
          <main className="flex-1 max-w-[1600px] w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6 flex flex-col">
            {children}
          </main>

          {/* Global Footer */}
          <footer className="w-full border-t border-slate-200/90 py-4 px-6 text-center text-xs text-slate-500 bg-white">
            <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
              <p className="font-medium">
                NER-ResQ — Smart Logistics Intelligence Platform • Northeast Region Corridor Operations
              </p>
              <p className="text-[11px] text-slate-400">
                MapLibre GL Engine • OpenStreetMap Data &copy; contributors
              </p>
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
}
