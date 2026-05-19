import Link from "next/link";
import { cookies } from "next/headers";
import { fetchCurrentUser } from "@/lib/auth";
import { NavUserMenu } from "@/components/nav-user-menu";

const navItems: Array<{ href: string; label: string }> = [
  { href: "/arena/champions", label: "競技場" },
  { href: "/mayhem", label: "海克斯大亂鬥" },
  { href: "/download", label: "下載 .exe" },
];

export async function Nav() {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore.toString();
  const user = await fetchCurrentUser(cookieHeader);

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-bg/85 backdrop-blur">
      <div className="container mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-2 font-bold tracking-tight">
            <span className="inline-flex h-7 w-7 items-center justify-center rounded bg-accent-strong text-bg">
              L
            </span>
            <span>LOL Helper</span>
          </Link>
          <nav className="hidden gap-1 md:flex">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded px-3 py-1.5 text-sm text-text-muted transition hover:bg-surface hover:text-text"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-3 text-xs text-text-dim">
          <span className="hidden rounded border border-border px-2 py-1 md:inline">Patch 16.9</span>
          <NavUserMenu user={user} />
        </div>
      </div>
    </header>
  );
}
