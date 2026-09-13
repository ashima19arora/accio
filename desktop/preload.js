const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('accioDesktop', {
  dragStart: (offset) => ipcRenderer.send('orb-drag-start', offset),
  dragMove: (coords) => ipcRenderer.send('orb-drag-move', coords),
  dragEnd: () => ipcRenderer.send('orb-drag-end'),
  orbClick: () => ipcRenderer.send('orb-click'),
  showContextMenu: () => ipcRenderer.send('orb-show-context-menu'),
  toggleVisibility: () => ipcRenderer.send('orb-toggle-visibility'),
  resetPosition: () => ipcRenderer.send('orb-reset-position'),
  quit: () => ipcRenderer.send('orb-quit'),
  executeAudio: (audioArrayBuffer) => ipcRenderer.invoke('orb-execute-audio', audioArrayBuffer),
  micStateChanged: (state) => ipcRenderer.send('orb-mic-state', state),
  onStateChange: (callback) => {
    ipcRenderer.on('orb-state', (_event, state) => callback(state));
  },
  onThemeChange: (callback) => {
    ipcRenderer.on('orb-theme-change', (_event, theme) => callback(theme));
  },
  onVoiceState: (callback) => {
    ipcRenderer.on('orb-voice-state', (_event, data) => callback(data));
  },
});
