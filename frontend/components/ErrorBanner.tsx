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
      className="p-3.5 rounded-xl border border-rose-300 dark:border-rose-900/80 bg-rose-50 dark:bg-rose-950/40 text-rose-900 dark:text-rose-100 shadow-sm flex items-start justify-between gap-3"
    >
      <div className="flex items-start gap-2.5">
        <span className="text-lg leading-none mt-0.5">⚠️</span>
        <div className="text-xs space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-bold uppercase tracking-wide text-[11px] font-mono text-rose-700 dark:text-rose-300">
              [{code}]
            </span>
            <span className="font-semibold">{message}</span>
          </div>

          <p className="text-zinc-600 dark:text-zinc-400">{helperText}</p>

          {details && Object.keys(details).length > 0 && (
            <div className="mt-1 pt-1 border-t border-rose-200 dark:border-rose-900/40 font-mono text-[10px] text-zinc-500">
              <span>Details: </span>
              <span>{JSON.stringify(details)}</span>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {onRetry && (
          <button
            onClick={onRetry}
            className="text-xs font-semibold px-2.5 py-1 rounded-md bg-rose-600 hover:bg-rose-700 text-white transition-colors"
          >
            Retry
          </button>
        )}
        <button
          onClick={onDismiss}
          className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 px-1.5 py-0.5 rounded text-sm"
          aria-label="Dismiss error banner"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
