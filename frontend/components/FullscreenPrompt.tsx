"use client";
import { Maximize2 } from "lucide-react";

/**
 * Fullscreen intro screen shown before starting a practice or exam session.
 * Enters fullscreen automatically — no "skip" option.
 */
export function FullscreenPrompt({ onStart }: { onStart: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "var(--bg)" }}>
      <div className="max-w-sm text-center space-y-4 p-6">
        <div className="w-12 h-12 rounded-full mx-auto flex items-center justify-center"
             style={{ background: "color-mix(in srgb, var(--primary) 12%, transparent)" }}>
          <Maximize2 size={24} style={{ color: "var(--primary)" }} />
        </div>
        <h2 className="text-base font-bold">Ready to begin</h2>
        <p className="text-xs text-muted leading-relaxed">
          This session requires fullscreen mode to ensure exam integrity.
          Browser tabs and distractions will be hidden.
        </p>
        <button
          onClick={() => {
            document.documentElement.requestFullscreen()
              .then(() => onStart())
              .catch(() => onStart());
          }}
          className="btn btn-primary w-full ds-focus"
        >
          <Maximize2 size={15} />
          Enter fullscreen and start
        </button>
        <p className="text-[10px] text-muted">
          You can toggle fullscreen at any time during the session.
        </p>
      </div>
    </div>
  );
}
