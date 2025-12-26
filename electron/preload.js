// electron/preload.js
/**
 * Preload Script - 보안 브릿지
 *
 * React(렌더러 프로세스)와 Electron(메인 프로세스) 사이의
 * 안전한 통신 채널을 제공합니다.
 */

const { contextBridge, ipcRenderer } = require('electron');

// React에서 사용할 수 있는 API 노출
contextBridge.exposeInMainWorld('electronAPI', {
  // Backend 상태 체크
  checkBackendStatus: () => ipcRenderer.invoke('check-backend-status'),

  // 플랫폼 정보
  platform: process.platform,

  // 버전 정보
  versions: {
    node: process.versions.node,
    chrome: process.versions.chrome,
    electron: process.versions.electron
  }
});

console.log('[Preload] Electron API exposed to renderer');
