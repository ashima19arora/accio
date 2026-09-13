const { app, BrowserWindow, screen, ipcMain, Tray, Menu, nativeImage, globalShortcut } = require('electron');
const path = require('path');
const http = require('http');
const { spawn } = require('child_process');

let mainWindow = null;
let tray = null;
let dragOffset = null;
let lastToggleTimestamp = 0;
let currentTheme = 'aurora';
let voiceStateServer = null;
let pythonVoiceProcess = null;
const TOGGLE_COOLDOWN_MS = 400; // Prevent bounce / rapid multiple triggers

const WINDOW_WIDTH = 260;
const WINDOW_HEIGHT = 130;

function createOverlayWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.workAreaSize;

  // Station cleanly at middle-right edge with balanced margin
  const defaultX = width - WINDOW_WIDTH - 20;
  const defaultY = Math.max(60, Math.round(height * 0.40));

  mainWindow = new BrowserWindow({
    width: WINDOW_WIDTH,
    height: WINDOW_HEIGHT,
    x: defaultX,
    y: defaultY,
    type: 'toolbar',
    frame: false,
    transparent: true,
    backgroundColor: '#00000000',
    alwaysOnTop: true,
    resizable: false,
    hasShadow: false,
    skipTaskbar: true,
    focusable: true,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Keep floating above all applications, browsers, and desktop windows
  mainWindow.setAlwaysOnTop(true, 'screen-saver');
  if (process.platform === 'darwin') {
    mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  }

  mainWindow.loadFile(path.join(__dirname, 'index.html'));

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
    mainWindow.setAlwaysOnTop(true, 'screen-saver');
    console.log(`[Accio Desktop] Floating Orb is online and visible at (${defaultX}, ${defaultY})`);
  });

  // Support in-window keyboard shortcut for Ctrl+R reload only (Ctrl+Shift+Z is handled by globalShortcut)
  mainWindow.webContents.on('before-input-event', (event, input) => {
    if ((input.control || input.meta) && !input.shift && input.key.toLowerCase() === 'r') {
      mainWindow.setSize(WINDOW_WIDTH, WINDOW_HEIGHT);
      mainWindow.reload();
      event.preventDefault();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  setupIPC();
  createTray();
}

function startVoiceStateServer() {
  if (voiceStateServer) return;
  try {
    voiceStateServer = http.createServer((req, res) => {
      res.setHeader('Access-Control-Allow-Origin', '*');
      if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
      }
      try {
        const parsedUrl = new URL(req.url, 'http://127.0.0.1:48123');
        if (parsedUrl.pathname === '/state') {
          const state = parsedUrl.searchParams.get('state') || 'idle';
          const text = parsedUrl.searchParams.get('text') || '';
          const message = parsedUrl.searchParams.get('message') || '';
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('orb-voice-state', { state, text, message });
          }
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ ok: true, state, text, message }));
          return;
        }
      } catch (_) {}
      res.writeHead(404);
      res.end();
    });

    voiceStateServer.listen(48123, '127.0.0.1', () => {
      console.log('[Accio Desktop] Voice state bridge listening on http://127.0.0.1:48123');
    });

    voiceStateServer.on('error', (err) => {
      console.warn('[Accio Desktop] Voice state port notice:', err.message);
    });
  } catch (err) {
    console.warn('[Accio Desktop] Could not start voice bridge:', err);
  }
}

function forwardAudioToPythonBridge(buffer) {
  return new Promise((resolve) => {
    if (!buffer) {
      resolve({ success: false, message: 'Empty audio buffer' });
      return;
    }
    const postData = Buffer.isBuffer(buffer) ? buffer : Buffer.from(buffer);
    const req = http.request(
      {
        hostname: '127.0.0.1',
        port: 48124,
        path: '/execute_audio',
        method: 'POST',
        headers: {
          'Content-Type': 'audio/wav',
          'Content-Length': postData.length,
        },
        timeout: 25000,
      },
      (res) => {
        let data = '';
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => {
          try {
            const parsed = JSON.parse(data);
            resolve(parsed);
          } catch (_) {
            resolve({ success: false, message: 'Invalid response from speech bridge' });
          }
        });
      }
    );

    req.on('error', (err) => {
      console.warn('[Accio Desktop] Speech bridge connection error:', err.message);
      resolve({ success: false, error: err.message, offline: true });
    });

    req.on('timeout', () => {
      req.destroy();
      resolve({ success: false, error: 'Speech bridge request timed out' });
    });

    req.write(postData);
    req.end();
  });
}

function ensurePythonVoiceBridge() {
  setTimeout(() => {
    const checkReq = http.get('http://127.0.0.1:48124/health', (res) => {
      if (res.statusCode === 200) {
        console.log('[Accio Desktop] Python Voice Bridge verified ONLINE on port 48124.');
      }
    });

    checkReq.on('error', () => {
      if (!pythonVoiceProcess) {
        console.log('[Accio Desktop] Spawning background Accio Voice Assistant daemon...');
        const projectRoot = path.join(__dirname, '..');
        try {
          pythonVoiceProcess = spawn('python', ['-u', 'assistant.py'], {
            cwd: projectRoot,
            stdio: 'pipe',
            windowsHide: true,
          });

          pythonVoiceProcess.stdout.on('data', () => {});
          pythonVoiceProcess.stderr.on('data', (d) => {
            const msg = d.toString().trim();
            if (msg && !msg.includes('UserWarning') && !msg.includes('DeprecationWarning')) {
              console.warn(`[Voice Daemon] ${msg}`);
            }
          });

          pythonVoiceProcess.on('exit', (code) => {
            console.log(`[Accio Desktop] Voice Assistant daemon exited with code ${code}`);
            pythonVoiceProcess = null;
          });
        } catch (err) {
          console.warn('[Accio Desktop] Failed to spawn voice assistant:', err.message);
        }
      }
    });
  }, 400);
}

function showOrb() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.setAlwaysOnTop(true, 'screen-saver');
  mainWindow.webContents.send('orb-state', { state: 'visible', timestamp: Date.now() });
  console.log('[Accio Desktop] Orb is now VISIBLE');
}

function hideOrb() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  mainWindow.hide();
  mainWindow.webContents.send('orb-state', { state: 'hidden', timestamp: Date.now() });
  console.log('[Accio Desktop] Orb is now HIDDEN');
}

function toggleOrbVisibility() {
  if (!mainWindow || mainWindow.isDestroyed()) return;

  const now = Date.now();
  if (now - lastToggleTimestamp < TOGGLE_COOLDOWN_MS) {
    // Cooldown in effect - ignore rapid duplicate bounce
    return;
  }
  lastToggleTimestamp = now;

  if (mainWindow.isVisible()) {
    hideOrb();
  } else {
    showOrb();
  }
}

function setTheme(theme) {
  currentTheme = theme;
  console.log(`[Accio Desktop] Switched theme to: ${theme}`);
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('orb-theme-change', theme);
  }
}

function getThemeSubmenu() {
  return [
    {
      label: 'Cosmic Aurora (Electric Cyan & Violet)',
      type: 'radio',
      checked: currentTheme === 'aurora',
      click: () => setTheme('aurora'),
    },
    {
      label: 'Solar Eclipse (Champagne Gold & Amber)',
      type: 'radio',
      checked: currentTheme === 'solar',
      click: () => setTheme('solar'),
    },
    {
      label: 'Emerald Nebula (Bioluminescent Jade & Mint)',
      type: 'radio',
      checked: currentTheme === 'emerald',
      click: () => setTheme('emerald'),
    },
  ];
}

function registerGlobalShortcuts() {
  const shortcut = 'CommandOrControl+Shift+Z';

  // Unregister existing instance if any
  try {
    if (globalShortcut.isRegistered(shortcut)) {
      globalShortcut.unregister(shortcut);
    }
  } catch (_) {}

  const success = globalShortcut.register(shortcut, () => {
    toggleOrbVisibility();
  });

  if (success) {
    console.log(`[Accio Desktop] Global shortcut registered: ${shortcut} (Toggle Orb Visibility)`);
  } else {
    console.warn(`[Accio Desktop] Failed to register global shortcut: ${shortcut}`);
  }
}

function setupIPC() {
  ipcMain.on('orb-drag-start', (_event, offset) => {
    dragOffset = offset;
  });

  ipcMain.on('orb-drag-move', () => {
    if (!dragOffset || !mainWindow) return;
    const cursorPos = screen.getCursorScreenPoint();
    const newX = cursorPos.x - dragOffset.x;
    const newY = cursorPos.y - dragOffset.y;
    mainWindow.setPosition(Math.round(newX), Math.round(newY));
  });

  ipcMain.on('orb-drag-end', () => {
    dragOffset = null;
  });

  ipcMain.on('orb-click', () => {
    console.log('[Accio Desktop] Orb clicked! Announcing voice readiness.');
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('orb-state', { state: 'clicked', timestamp: Date.now() });
      mainWindow.webContents.send('orb-voice-state', { state: 'ready_for_next', message: 'Ready for next' });
    }
  });

  ipcMain.on('orb-toggle-visibility', () => {
    toggleOrbVisibility();
  });

  ipcMain.on('orb-reset-position', () => {
    resetToDefaultPosition();
  });

  ipcMain.on('orb-show-context-menu', () => {
    if (!mainWindow || mainWindow.isDestroyed()) return;
    const contextMenu = Menu.buildFromTemplate([
      { label: 'Accio Persistent Orb', enabled: false },
      { type: 'separator' },
      {
        label: 'Theme',
        submenu: getThemeSubmenu(),
      },
      { type: 'separator' },
      {
        label: 'Hide Orb (Ctrl+Shift+Z)',
        click: () => hideOrb(),
      },
      {
        label: 'Reload Orb UI',
        click: () => {
          mainWindow.setSize(WINDOW_SIZE, WINDOW_SIZE);
          mainWindow.reload();
        },
      },
      {
        label: 'Reset Position',
        click: () => resetToDefaultPosition(),
      },
      {
        label: 'Center on Screen',
        click: () => centerOnScreen(),
      },
      { type: 'separator' },
      {
        label: 'Quit Accio Orb',
        click: () => app.quit(),
      },
    ]);
    contextMenu.popup({ window: mainWindow });
  });

  ipcMain.on('orb-quit', () => {
    app.quit();
  });

  ipcMain.handle('orb-execute-audio', async (_event, audioBuffer) => {
    const byteLen = audioBuffer ? (audioBuffer.byteLength || audioBuffer.length || 0) : 0;
    console.log(`[Accio Desktop] Received audio buffer (${byteLen} bytes) for speech execution.`);
    let res = await forwardAudioToPythonBridge(audioBuffer);
    if (res && res.offline) {
      // If bridge was not online yet, trigger spawn and retry
      ensurePythonVoiceBridge();
      await new Promise((r) => setTimeout(r, 2200));
      res = await forwardAudioToPythonBridge(audioBuffer);
    }
    return res;
  });

  ipcMain.on('orb-mic-state', (_event, data) => {
    const state = (data && data.state) ? data.state : 'idle';
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('orb-voice-state', { state });
    }
  });
}

function centerOnScreen() {
  if (!mainWindow) return;
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;
  mainWindow.setPosition(Math.round((width - WINDOW_WIDTH) / 2), Math.round((height - WINDOW_HEIGHT) / 2));
}

function resetToDefaultPosition() {
  if (!mainWindow) return;
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.workAreaSize;
  const defaultX = width - WINDOW_WIDTH - 20;
  const defaultY = Math.max(60, Math.round(height * 0.40));
  mainWindow.setPosition(defaultX, defaultY);
}

function createTray() {
  try {
    // Generate a clean 16x16 cyber cyan icon for the Windows system tray
    const svgIcon = `
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
        <circle cx="8" cy="8" r="7" fill="#0f172a" stroke="#38bdf8" stroke-width="1.5"/>
        <text x="8" y="11.5" font-family="Arial, sans-serif" font-size="9" font-weight="bold" fill="#f0f9ff" text-anchor="middle">A</text>
      </svg>
    `;
    const icon = nativeImage.createFromBuffer(Buffer.from(svgIcon));
    tray = new Tray(icon);
    tray.setToolTip('Accio - Persistent AI Voice Assistant (Ctrl+Shift+Z)');

    const contextMenu = Menu.buildFromTemplate([
      { label: 'Accio Persistent Orb', enabled: false },
      { type: 'separator' },
      {
        label: 'Theme',
        submenu: getThemeSubmenu(),
      },
      { type: 'separator' },
      {
        label: 'Toggle Visibility (Ctrl+Shift+Z)',
        click: () => toggleOrbVisibility(),
      },
      {
        label: 'Show Orb',
        click: () => showOrb(),
      },
      {
        label: 'Hide Orb',
        click: () => hideOrb(),
      },
      { type: 'separator' },
      {
        label: 'Reload Orb UI (Ctrl+R)',
        click: () => {
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.setSize(WINDOW_SIZE, WINDOW_SIZE);
            mainWindow.reload();
          }
        },
      },
      {
        label: 'Reset to Middle-Right',
        click: () => resetToDefaultPosition(),
      },
      {
        label: 'Center on Screen',
        click: () => centerOnScreen(),
      },
      { type: 'separator' },
      {
        label: 'Quit Accio Overlay',
        click: () => app.quit(),
      },
    ]);

    tray.setContextMenu(contextMenu);
    tray.on('click', () => {
      toggleOrbVisibility();
    });
  } catch (err) {
    console.warn('[Accio Tray] Could not create system tray icon:', err);
  }
}

app.whenReady().then(() => {
  createOverlayWindow();
  registerGlobalShortcuts();
  startVoiceStateServer();
  ensurePythonVoiceBridge();
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
  if (voiceStateServer) {
    try { voiceStateServer.close(); } catch (_) {}
  }
  if (pythonVoiceProcess) {
    try {
      if (process.platform === 'win32' && pythonVoiceProcess.pid) {
        spawn('taskkill', ['/pid', pythonVoiceProcess.pid.toString(), '/f', '/t']);
      } else {
        pythonVoiceProcess.kill();
      }
    } catch (_) {}
    pythonVoiceProcess = null;
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createOverlayWindow();
  }
});
