"use client";

import { useState, type ReactNode } from "react";

/**
 * Light hover tooltip.
 *
 * Avoids portal overhead — places an absolutely-positioned panel relative to
 * the trigger. Good enough for short LoL-flavour descriptions.
 */
export function HoverTooltip({
  children,
  content,
  width = 280,
}: {
  children: ReactNode;
  content: ReactNode;
  width?: number;
}) {
  const [open, setOpen] = useState(false);
  if (!content) return <>{children}</>;
  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      {children}
      {open && (
        <span
          role="tooltip"
          className="pointer-events-none absolute left-0 top-full z-50 mt-1 whitespace-pre-line rounded-md border border-border-strong bg-bg/95 p-2.5 text-xs leading-relaxed text-text shadow-lg backdrop-blur"
          style={{ width }}
        >
          {content}
        </span>
      )}
    </span>
  );
}
