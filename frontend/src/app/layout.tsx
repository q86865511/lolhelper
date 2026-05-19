import type { Metadata } from "next";
import { Nav } from "@/components/nav";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    template: "%s | LOL Helper",
    default: "LOL Helper — 競技場 & 海克斯大亂鬥 統計",
  },
  description: "League of Legends 競技場 (Arena) 與 海克斯大亂鬥 (Mayhem) 即時 augment 與裝備勝率統計。",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-TW">
      <body className="min-h-screen antialiased">
        <Nav />
        {children}
        <footer className="border-t border-border py-8 mt-16">
          <div className="container mx-auto max-w-6xl px-4 text-xs text-text-dim">
            <p>
              This product isn&apos;t endorsed by Riot Games and doesn&apos;t reflect the
              views or opinions of Riot Games or anyone officially involved in producing or
              managing League of Legends.
            </p>
            <p className="mt-1">
              League of Legends and Riot Games are trademarks or registered trademarks of
              Riot Games, Inc.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
