/**
 * Electron预加载脚本
 * 提供安全的IPC通信桥接
 */

const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的API给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
    // 应用信息
    getAppInfo: () => ipcRenderer.invoke('app:getInfo'),

    // 文件对话框
    openFile: (options) => ipcRenderer.invoke('dialog:openFile', options),
    saveFile: (options) => ipcRenderer.invoke('dialog:saveFile', options),
    showMessage: (options) => ipcRenderer.invoke('dialog:message', options),

    // 应用控制
    restartApp: () => ipcRenderer.send('app:restart'),
    quitApp: () => ipcRenderer.send('app:quit'),

    // 平台信息
    platform: process.platform,
    isElectron: true
});

console.log('Electron preload已加载');
