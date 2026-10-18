const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("attentionDesktop", {
  isDesktopApp: true,

  getAgentStatus: () => ipcRenderer.invoke("agent:status"),

  startAgent: () => ipcRenderer.invoke("agent:start"),

  stopAgent: () => ipcRenderer.invoke("agent:stop"),

  loginAgent: (creds) => ipcRenderer.invoke("agent:login", creds),

  logoutAgent: () => ipcRenderer.invoke("agent:logout"),
});
