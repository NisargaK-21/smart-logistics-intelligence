"use client";

import React from "react";
import { ApiError } from "../lib/api";
import { ERROR_MESSAGES } from "../lib/constants";

interface ErrorBannerProps {
  error: ApiError | Error | string | null;
  onDismiss: () => void;
  onRetry?: () => void;
}

export default function ErrorBanner({
  error,
  onDismiss,
  onRetry,
}: ErrorBannerProps) {
  if (!error) return null;

  let code = "ERROR";
  let message = "";
  let details: Record<string, unknown> | undefined;

  if (error instanceof ApiError) {
    code = error.code;
    message = error.message;
    details = error.details;
  } else if (error instanceof Error) {
    message = error.message;
  } else {
    message = String(error);
  }

  const helperText = ERROR_MESSAGES[code] || "An unexpected error occurred.";

  return (
    <div
      role="alert"
      className="p-4 rounded-xl border border-rose-200 bg-rose-50/80 text-rose-950 shadow-xs flex items-start justify-between gap-3 transition-all"
    >
      <div className="flex items-start gap-3">
        <span className="text-xl leading-none mt-0.5">⚠️</span>
        <div className="text-xs space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-bold uppercase tracking-wide text-[11px] font-mono text-rose-700 bg-rose-100/80 px-2 py-0.5 rounded border border-rose-200">
              [{code}]
            </span>
            <span className="font-bold text-rose-900">{message}</span>
          </div>

          <p className="text-slate-600 leading-relaxed">{helperText}</p>

          {details && Object.keys(details).length > 0 && (
            <div className="mt-1.5 pt-1.5 border-t border-rose-200/60 font-mono text-[10px] text-slate-500">
              <span className="font-semibold text-slate-700">Details: </span>
              <span>{JSON.stringify(details)}</span>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {onRetry && (
          <button
            onClick={onRetry}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white transition-colors cursor-pointer shadow-2xs"
          >
            Retry
          </button>
        )}
        <button
          onClick={onDismiss}
          className="text-slate-400 hover:text-slate-700 p-1.5 rounded-lg text-sm cursor-pointer"
          aria-label="Dismiss error banner"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
