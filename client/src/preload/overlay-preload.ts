import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("overlay", {
  onAugmentOffer: (cb: (offer: unknown) => void) =>
    ipcRenderer.on("live:augment-offer", (_e, o) => cb(o)),
  onItemShop: (cb: (state: unknown) => void) =>
    ipcRenderer.on("live:item-shop", (_e, s) => cb(s)),
});
