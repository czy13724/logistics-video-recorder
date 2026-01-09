/**
 * Electron主进程
 * 物流视频录制管理系统桌面版
 */

const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const Store = require('electron-store');

const store = new Store();
let mainWindow;
let pythonProcess;

// 配置
const CONFIG = {
    isDev: !app.isPackaged,
    pythonPath: process.platform === 'win32' ? 'python' : 'python3',
    serverPort: store.get('serverPort', 8000)
};

/**
 * 创建主窗口
 */
function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1200,
        minHeight: 700,
        title: '物流视频录制管理系统',
        icon: path.join(__dirname, '../build/icon.png'),
        backgroundColor: '#0f172a',
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        },
        autoHideMenuBar: true,
        show: false
    });

    // 窗口准备好后显示
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    // 开发模式：加载本地服务器
    if (CONFIG.isDev) {
        mainWindow.loadURL(`http://localhost:${CONFIG.serverPort}`);
        mainWindow.webContents.openDevTools();
    } else {
        // 生产模式：等待Python服务器启动后加载
        setTimeout(() => {
            mainWindow.loadURL(`http://localhost:${CONFIG.serverPort}`);
        }, 3000);
    }

    // 窗口关闭事件
    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    // 处理外部链接
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        require('electron').shell.openExternal(url);
        return { action: 'deny' };
    });
}

/**
 * 启动Python后端服务器
 */
function startPythonServer() {
    return new Promise((resolve, reject) => {
        const scriptPath = CONFIG.isDev
            ? path.join(__dirname, '../web_server.py')
            : path.join(process.resourcesPath, 'python-backend/web_server.py');

        console.log('启动Python服务器:', scriptPath);

        pythonProcess = spawn(CONFIG.pythonPath, [
            scriptPath,
            '--port', CONFIG.serverPort.toString(),
            '--host', '0.0.0.0'
        ], {
            cwd: CONFIG.isDev ? path.join(__dirname, '..') : process.resourcesPath
        });

        pythonProcess.stdout.on('data', (data) => {
            console.log(`Python: ${data}`);
            if (data.toString().includes('Uvicorn running')) {
                resolve();
            }
        });

        pythonProcess.stderr.on('data', (data) => {
            console.error(`Python错误: ${data}`);
        });

        pythonProcess.on('error', (err) => {
            console.error('启动Python服务器失败:', err);
            dialog.showErrorBox(
                '启动失败',
                `无法启动后端服务器:\n${err.message}\n\n请确保已安装Python和相关依赖。`
            );
            reject(err);
        });

        pythonProcess.on('close', (code) => {
            console.log(`Python进程退出，代码: ${code}`);
        });

        // 超时检测
        setTimeout(() => {
            resolve(); // 超时也继续，让用户看到错误
        }, 5000);
    });
}

/**
 * 停止Python服务器
 */
function stopPythonServer() {
    if (pythonProcess) {
        console.log('停止Python服务器');
        pythonProcess.kill();
        pythonProcess = null;
    }
}

// ==================== App生命周期 ====================

app.whenReady().then(async () => {
    try {
        // 启动Python服务器
        if (!CONFIG.isDev) {
            await startPythonServer();
        }

        // 创建窗口
        createWindow();
    } catch (err) {
        console.error('应用启动失败:', err);
    }

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    stopPythonServer();
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('before-quit', () => {
    stopPythonServer();
});

// ==================== IPC通信 ====================

// 获取应用信息
ipcMain.handle('app:getInfo', () => {
    return {
        version: app.getVersion(),
        platform: process.platform,
        isDev: CONFIG.isDev
    };
});

// 打开文件对话框
ipcMain.handle('dialog:openFile', async (event, options) => {
    const result = await dialog.showOpenDialog(mainWindow, options);
    return result;
});

// 保存文件对话框
ipcMain.handle('dialog:saveFile', async (event, options) => {
    const result = await dialog.showSaveDialog(mainWindow, options);
    return result;
});

// 显示消息框
ipcMain.handle('dialog:message', async (event, options) => {
    const result = await dialog.showMessageBox(mainWindow, options);
    return result;
});

// 重启应用
ipcMain.on('app:restart', () => {
    app.relaunch();
    app.exit(0);
});

// 退出应用
ipcMain.on('app:quit', () => {
    app.quit();
});

console.log('Electron主进程已启动');
