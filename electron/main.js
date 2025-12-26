// electron/main.js
/**
 * Electron Main Process
 *
 * 역할:
 * 1. 앱 창 생성 및 관리
 * 2. Python Backend 자동 실행
 * 3. 시스템 이벤트 처리
 */

const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const isDev = require('electron-is-dev');

let mainWindow;
let backendProcess;

// Python Backend 실행
function startBackend() {
  console.log('[Electron] Starting Python backend...');

  const backendPath = path.join(__dirname, '../backend');
  const pythonScript = path.join(backendPath, 'src/api/main.py');

  // 개발 환경: 직접 Python 실행
  // 프로덕션: 패키징된 실행 파일 사용
  const pythonCmd = isDev ? 'python' : 'python'; // TODO: 프로덕션 경로 설정

  backendProcess = spawn(pythonCmd, ['-m', 'uvicorn', 'src.api.main:app', '--host', '127.0.0.1', '--port', '8000'], {
    cwd: backendPath,
    env: { ...process.env }
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`[Backend] ${data.toString()}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`[Backend Error] ${data.toString()}`);
  });

  backendProcess.on('close', (code) => {
    console.log(`[Backend] Process exited with code ${code}`);
  });
}

// Electron 창 생성
function createWindow() {
  console.log('[Electron] Creating main window...');

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false
    },
    icon: path.join(__dirname, '../frontend/assets/icon.png'),
    titleBarStyle: 'default',
    show: false // 준비될 때까지 숨김
  });

  // React 앱 로드
  const startUrl = isDev
    ? 'http://localhost:3000'  // 개발: React dev server
    : `file://${path.join(__dirname, '../frontend/build/index.html')}`; // 프로덕션: 빌드된 파일

  mainWindow.loadURL(startUrl);

  // 개발 모드에서만 DevTools 자동 열기
  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  // 창이 준비되면 표시
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    console.log('[Electron] Main window ready');
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// 앱 시작
app.whenReady().then(() => {
  console.log('[Electron] App ready');

  // Backend 먼저 시작
  startBackend();

  // Backend 시작 대기 후 UI 창 생성 (3초)
  setTimeout(() => {
    createWindow();
  }, 3000);

  app.on('activate', () => {
    // macOS: Dock 아이콘 클릭 시 창 재생성
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// 모든 창이 닫히면 앱 종료 (macOS 제외)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// 앱 종료 시 Backend 프로세스 정리
app.on('quit', () => {
  console.log('[Electron] Shutting down...');

  if (backendProcess) {
    console.log('[Electron] Killing backend process...');
    backendProcess.kill();
  }
});

// IPC 통신 예시 (Frontend ↔ Electron)
ipcMain.handle('check-backend-status', async () => {
  // Backend API 상태 체크
  try {
    const response = await fetch('http://localhost:8000/health');
    return response.ok;
  } catch (error) {
    return false;
  }
});
