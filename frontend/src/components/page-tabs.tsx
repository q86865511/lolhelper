import Link from "next/link";
import type { Route } from "next";

export type TabItem = { href: string; label: string; active?: boolean };

export function PageTabs({ items }: { items: TabItem[] }) {
  return (
    <div className="border-b border-border">
      <nav className="flex gap-1">
        {items.map((item) => (
          <Link
            key={item.href}
            href={item.href as Route}
            className={`relative px-4 py-2.5 text-sm transition ${
              item.active
                ? "text-text"
                : "text-text-muted hover:text-text"
            }`}
          >
            {item.label}
            {item.active && (
              <span className="absolute inset-x-3 -bottom-px h-0.5 bg-accent-strong" />
            )}
          </Link>
        ))}
      </nav>
    </div>
  );
}
