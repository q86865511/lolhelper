export default function DownloadPage() {
  return (
    <main className="container mx-auto max-w-3xl px-4 py-10">
      <header className="mb-4">
        <div className="text-xs text-text-dim">客戶端</div>
        <h1 className="mt-1 text-2xl font-bold tracking-tight">下載 .exe</h1>
      </header>

      <div className="rounded-lg border border-border bg-surface p-5">
        <p className="text-sm text-text-muted">
          .exe 客戶端會在 M2 推出。功能:
        </p>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-text">
          <li>偵測 LoL 客戶端,自動同步 augment 選擇</li>
          <li>遊戲中右下角 always-on-top 推薦 overlay(熱鍵 Alt+Q 切換)</li>
          <li>本機 Mayhem 戰績自動上傳(可關閉)</li>
          <li>Windows 自動更新</li>
        </ul>
      </div>

      <div className="mt-6 rounded-lg border border-border bg-surface p-5 text-xs text-text-dim">
        <p>
          發佈方式預定:GitHub Releases 提供 NSIS 安裝程式,
          整合 electron-updater 自動下載新版。
        </p>
      </div>
    </main>
  );
}
