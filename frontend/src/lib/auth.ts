/** Client-side auth helpers. Cookies are HttpOnly so we never see the JWT directly. */

import { apiGet } from "@/lib/api-client";

export type CurrentUser = {
  id: number;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  consent_upload: boolean;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Server-side: fetch /auth/me with cookie forwarded so SSR knows who the user is. */
export async function fetchCurrentUser(cookieHeader?: string): Promise<CurrentUser | null> {
  try {
    const url = `${API_URL}/api/v1/auth/me`;
    const res = await fetch(url, {
      method: "GET",
      headers: cookieHeader ? { cookie: cookieHeader, accept: "application/json" } : { accept: "application/json" },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as CurrentUser;
  } catch {
    return null;
  }
}

/** Client-side: kick off Google OAuth. Hits backend for the authorize URL then redirects. */
export async function startGoogleLogin(): Promise<void> {
  // Use proxy route in browser so cookie set by backend lands on the same origin
  const res = await apiGet<{ url: string }>("/auth/google/url");
  window.location.href = res.url;
}

/** Client-side: hit /auth/logout to revoke and clear cookies. */
export async function logout(): Promise<void> {
  await fetch("/api/proxy/auth/logout", {
    method: "POST",
    credentials: "include",
  });
  window.location.href = "/";
}
