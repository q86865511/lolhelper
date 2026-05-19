/**
 * Watch the LoL client lockfile and emit when LCU comes online/offline.
 *
 * Lockfile location (Windows default):
 *   C:\Riot Games\League of Legends\lockfile
 *
 * Format: ProcessName:PID:Port:Password:Protocol  (e.g. "LeagueClient:12345:54321:abcd...:https")
 *
 * M2 milestone: full implementation + WebSocket subscribe.
 */

import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { EventEmitter } from "node:events";

export interface LCUCredentials {
  pid: number;
  port: number;
  password: string;
  protocol: "http" | "https";
  baseUrl: string;
  authHeader: string; // Basic ...
}

export class LockfileWatcher extends EventEmitter {
  private path: string;
  private current: LCUCredentials | null = null;
  private interval: NodeJS.Timeout | null = null;

  constructor(installPath = "C:\\Riot Games\\League of Legends") {
    super();
    this.path = resolve(installPath, "lockfile");
  }

  start(): void {
    if (this.interval) return;
    this.interval = setInterval(() => void this.check(), 2000);
    void this.check();
  }

  stop(): void {
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }
  }

  private async check(): Promise<void> {
    try {
      const raw = await readFile(this.path, "utf-8");
      const creds = parseLockfile(raw);
      if (!this.current || this.current.port !== creds.port) {
        this.current = creds;
        this.emit("connected", creds);
      }
    } catch (e: unknown) {
      const err = e as { code?: string };
      if (err.code === "ENOENT") {
        if (this.current) {
          this.current = null;
          this.emit("disconnected");
        }
      }
      // other errors ignored — we'll retry next tick
    }
  }
}

export function parseLockfile(raw: string): LCUCredentials {
  const [, pid, port, password, protocol] = raw.trim().split(":");
  if (!pid || !port || !password || !protocol) {
    throw new Error(`malformed lockfile: ${raw}`);
  }
  const baseUrl = `${protocol}://127.0.0.1:${port}`;
  const authHeader =
    "Basic " + Buffer.from(`riot:${password}`).toString("base64");
  return {
    pid: Number(pid),
    port: Number(port),
    password,
    protocol: protocol as "http" | "https",
    baseUrl,
    authHeader,
  };
}
