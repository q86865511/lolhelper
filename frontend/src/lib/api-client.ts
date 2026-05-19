/**
 * API client shared by Server Components and Client Components.
 *
 * Server-side: hit backend directly via NEXT_PUBLIC_API_URL.
 * Client-side: hit /api/proxy/... so the browser never sees the raw backend host.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type ApiOptions = RequestInit & { next?: { revalidate?: number; tags?: string[] } };

function isServer(): boolean {
  return typeof window === "undefined";
}

export async function apiGet<T = unknown>(
  path: string,
  init: ApiOptions = {},
): Promise<T> {
  const url = isServer() ? `${API_URL}/api/v1${path}` : `/api/proxy${path}`;
  const res = await fetch(url, {
    method: "GET",
    headers: {
      Accept: "application/json",
      ...(init.headers ?? {}),
    },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}
