"use client";

import Link from "next/link";
import Image from "next/image";
import { useState, useRef, useEffect } from "react";
import { logout, type CurrentUser } from "@/lib/auth";

export function NavUserMenu({ user }: { user: CurrentUser | null }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  if (!user) {
    return (
      <Link
        href="/auth/login"
        className="rounded-md border border-border bg-surface px-3 py-1 text-text-muted transition hover:border-border-strong hover:text-text"
      >
        登入
      </Link>
    );
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-md border border-border bg-surface px-2 py-1 transition hover:border-border-strong"
      >
        {user.avatar_url ? (
          <Image
            src={user.avatar_url}
            alt={user.display_name ?? user.email}
            width={20}
            height={20}
            className="rounded-full"
            unoptimized
          />
        ) : (
          <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-accent-strong text-[10px] text-bg">
            {(user.display_name ?? user.email).slice(0, 1).toUpperCase()}
          </span>
        )}
        <span className="text-text">{user.display_name ?? user.email}</span>
        <span className="text-text-dim">▾</span>
      </button>
      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 w-48 rounded-md border border-border bg-bg p-1 shadow-lg">
          <div className="px-3 py-2 text-[11px] text-text-dim">{user.email}</div>
          <hr className="border-border" />
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              void logout();
            }}
            className="block w-full rounded px-3 py-1.5 text-left text-sm text-text-muted hover:bg-surface hover:text-text"
          >
            登出
          </button>
        </div>
      )}
    </div>
  );
}
