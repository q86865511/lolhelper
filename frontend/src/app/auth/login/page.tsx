import { LoginButton } from "./login-button";

export const dynamic = "force-dynamic";

export default function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  return (
    <main className="container mx-auto max-w-md px-4 py-16">
      <div className="rounded-lg border border-border bg-surface p-8">
        <h1 className="text-2xl font-bold tracking-tight">登入</h1>
        <p className="mt-2 text-sm text-text-muted">
          用 Google 帳號登入,M2 將支援將您的 .exe 上傳資料綁定到個人帳號。
        </p>

        <ErrorBanner promise={searchParams} />

        <div className="mt-6">
          <LoginButton />
        </div>

        <div className="mt-6 text-xs text-text-dim">
          目前帳號用途:同意 Mayhem 對戰資料上傳(預設可關)、未來個人戰績頁。
          不會公開您的 Email 或姓名。
        </div>
      </div>
    </main>
  );
}

async function ErrorBanner({
  promise,
}: {
  promise: Promise<{ error?: string }>;
}) {
  const { error } = await promise;
  if (!error) return null;
  return (
    <div className="mt-4 rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
      登入失敗:{error}
    </div>
  );
}
