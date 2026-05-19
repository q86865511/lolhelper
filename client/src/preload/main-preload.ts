import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("lolhelper", {
  onLcuState: (cb: (state: unknown) => void) =>
    ipcRenderer.on("lcu:state", (_e, s) => cb(s)),
  onGameflowPhase: (cb: (phase: string) => void) =>
    ipcRenderer.on("lcu:gameflow-phase", (_e, p: string) => cb(p)),
  toggleOverlay: () => ipcRenderer.send("window:toggle-overlay"),
});
