const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  setInteractiveRegion: (region) => ipcRenderer.send('set-interactive-region', region),
  enableMousePenetrate: () => ipcRenderer.send('enable-mouse-penetrate'),
  disableMousePenetrate: () => ipcRenderer.send('disable-mouse-penetrate'),
  getScreenSize: () => ipcRenderer.invoke('get-screen-size'),
  getVideoContainerSize: () => ipcRenderer.invoke('get-video-container-size'),
  getHotZoneExpand: () => ipcRenderer.invoke('get-hot-zone-expand'),

  onToggleDanmaku: (callback) => ipcRenderer.on('toggle-danmaku', (event, paused) => callback(paused)),
  onChangeVideoSource: (callback) => ipcRenderer.on('change-video-source', () => callback()),
  onScreenSize: (callback) => ipcRenderer.on('screen-size', (event, size) => callback(size)),
  onVideoContainerSize: (callback) => ipcRenderer.on('video-container-size', (event, size) => callback(size)),
  onHotZoneExpand: (callback) => ipcRenderer.on('hot-zone-expand', (event, expand) => callback(expand)),

  removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel)
});
