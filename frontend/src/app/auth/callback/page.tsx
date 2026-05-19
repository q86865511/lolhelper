import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import { fetchCurrentUser } from "@/lib/auth";

export const dynamic = "force-dynamic";

/**
 * Backend redirects here after Google sign-in completes. By the time the user
 * reaches this page, the auth cookies are already set. We confirm by hitting
 * /auth/me, then forward to the home page.
 */
export default async function AuthCallback() {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore.toString();
  const user = await fetchCurrentUser(cookieHeader);
  if (!user) {
    redirect("/auth/login?error=session_not_established");
  }
  redirect("/");
}
