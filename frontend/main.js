const { app, BrowserWindow, Tray, Menu, ipcMain, screen } = require('electron');
const path = require('path');

let mainWindow = null;
let tray = null;
let isDanmakuPaused = false;

const HOT_ZONE_EXPAND = {
  left: 100,
  right: 100,
  top: 50,
  bottom: 50
};

const VIDEO_CONTAINER_SIZE = {
  width: 600,
  height: 337
};

function createWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  mainWindow = new BrowserWindow({
    width: width,
    height: height,
    x: 0,
    y: 0,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    hasShadow: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      webSecurity: false
    }
  });

  mainWindow.loadFile('index.html');

  // 默认鼠标穿透，让桌面图标可点击
  mainWindow.setIgnoreMouseEvents(true, { forward: true });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function createTray() {
  const iconPath = path.join(__dirname, 'icon', 'theme.jpg');
  tray = new Tray(iconPath);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: '暂停弹幕',
      type: 'checkbox',
      checked: false,
      click: (menuItem) => {
        isDanmakuPaused = menuItem.checked;
        if (mainWindow) {
          mainWindow.webContents.send('toggle-danmaku', isDanmakuPaused);
        }
      }
    },
    {
      label: '切换视频源',
      click: () => {
        if (mainWindow) {
          mainWindow.webContents.send('change-video-source');
        }
      }
    },
    { type: 'separator' },
    {
      label: '显示窗口',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
        }
      }
    },
    {
      label: '隐藏窗口',
      click: () => {
        if (mainWindow) {
          mainWindow.hide();
        }
      }
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        app.quit();
      }
    }
  ]);

  tray.setToolTip('B站弹幕播放器');
  tray.setContextMenu(contextMenu);

  tray.on('click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
      }
    }
  });
}

// 启用鼠标穿透（桌面图标可点击）
ipcMain.on('enable-mouse-penetrate', (event) => {
  if (mainWindow) {
    mainWindow.setIgnoreMouseEvents(true, { forward: true });
    console.log('Mouse penetrate enabled');
  }
});

// 禁用鼠标穿透（可交互）
ipcMain.on('disable-mouse-penetrate', (event) => {
  if (mainWindow) {
    mainWindow.setIgnoreMouseEvents(false);
    console.log('Mouse penetrate disabled');
  }
});

ipcMain.on('get-screen-size', (event) => {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;
  event.reply('screen-size', { width, height });
});

ipcMain.on('get-video-container-size', (event) => {
  event.reply('video-container-size', VIDEO_CONTAINER_SIZE);
});

ipcMain.on('get-hot-zone-expand', (event) => {
  event.reply('hot-zone-expand', HOT_ZONE_EXPAND);
});

app.whenReady().then(() => {
  createWindow();
  createTray();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  if (tray) {
    tray.destroy();
  }
});
