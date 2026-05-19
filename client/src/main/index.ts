/**
 * Electron main process entry.
 *
 * Responsibilities:
 *  - Create main window (dashboard) + overlay window (transparent always-on-top)
 *  - Wire up LCU watcher + Live Client poller -> IPC broadcasts
 *  - Wire up Mayhem uploader -> backend
 *  - Auto-update via electron-updater
 *
 * M2 milestone: implement LCU watcher.
 * M3 milestone: implement overlay panels + recommendation calls.
 */

import { app, BrowserWindow } from "electron";
import { resolve } from "node:path";

let mainWindow: BrowserWindow | null = null;
let overlayWindow: BrowserWindow | null = null;

function createMainWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 720,
    title: "LOL Helper",
    show: false,
    webPreferences: {
      preload: resolve(__dirname, "../preload/main.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.once("ready-to-show", () => mainWindow?.show());

  if (process.env.ELECTRON_RENDERER_URL) {
    void mainWindow.loadURL(
      `${process.env.ELECTRON_RENDERER_URL}/src/renderer/main.html`,
    );
  } else {
    void mainWindow.loadFile(resolve(__dirname, "../renderer/main.html"));
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

function createOverlayWindow(): void {
  overlayWindow = new BrowserWindow({
    width: 320,
    height: 480,
    x: 100,
    y: 100,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    show: false,
    focusable: false, // start non-interactive; toggle on hotkey
    webPreferences: {
      preload: resolve(__dirname, "../preload/overlay.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  // Keep above fullscreen games on Windows
  overlayWindow.setAlwaysOnTop(true, "screen-saver");

  if (process.env.ELECTRON_RENDERER_URL) {
    void overlayWindow.loadURL(
      `${process.env.ELECTRON_RENDERER_URL}/src/overlay/overlay.html`,
    );
  } else {
    void overlayWindow.loadFile(resolve(__dirname, "../renderer/overlay.html"));
  }
}

app.whenReady().then(() => {
  createMainWindow();
  createOverlayWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
      createOverlayWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
