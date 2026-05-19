export default function MayhemHome() {
  return (
    <main className="container mx-auto max-w-3xl px-4 py-10">
      <header className="mb-4">
        <div className="text-xs text-amber-400">queueId 2400 · Featured Mode</div>
        <h1 className="mt-1 text-2xl font-bold tracking-tight">海克斯大亂鬥 Mayhem</h1>
      </header>

      <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-5">
        <h2 className="font-semibold text-amber-200">資料來源待 M2 客戶端上線</h2>
        <p className="mt-2 text-sm text-amber-100/80">
          Riot 永久封鎖 Mayhem (queueId=2400) 的 Match-V5 API,
          全球資料只能透過 .exe 客戶端讀本機 LCU 累積。
        </p>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-amber-100/90">
          <li>客戶端讀 LCU <code className="font-mono text-xs">/lol-match-history</code> 抓 queueId=2400 對戰</li>
          <li>首次啟動跳出上傳同意提示,預設勾選,可關</li>
          <li>後端 <code className="font-mono text-xs">/api/v1/ingest/mayhem</code> 接收聚合</li>
          <li>累積到一定樣本後本頁面才會顯示 augment 排行</li>
        </ul>
      </div>

      <div className="mt-6 rounded-lg border border-border bg-surface p-5">
        <h3 className="text-sm font-semibold">為什麼 Mayhem 沒有全球資料?</h3>
        <p className="mt-2 text-sm text-text-muted">
          Riot 開發者關係團隊在 GitHub Issue #1109 公開表明,Mayhem 與 Brawl 模式都不會開放
          Match-V5 API。所有第三方統計站(OP.GG、U.GG、metasrc)目前都沒有 Mayhem 資料 ——
          這不是技術問題,是 Riot 政策。
        </p>
      </div>
    </main>
  );
}
