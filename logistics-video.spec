# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# 收集PyQt6的插件文件
pyqt6_plugins = []
try:
    import PyQt6
    pyqt6_path = os.path.dirname(PyQt6.__file__)
    qt_plugins_path = os.path.join(pyqt6_path, 'Qt6', 'plugins')
    
    if os.path.exists(qt_plugins_path):
        # 收集platforms插件（最重要）
        platforms_path = os.path.join(qt_plugins_path, 'platforms')
        if os.path.exists(platforms_path):
            for file in os.listdir(platforms_path):
                if file.endswith(('.so', '.dylib', '.dll')):
                    src = os.path.join(platforms_path, file)
                    dst = os.path.join('PyQt6', 'Qt6', 'plugins', 'platforms')
                    pyqt6_plugins.append((src, dst))
        
        # 收集其他插件目录（可选，根据需要添加）
        # 例如：imageformats, styles, 等
except Exception as e:
    print(f"警告: 无法收集PyQt6插件: {e}")

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.json.example', '.'),
        ('web', 'web'),
        ('video_recorder.py', '.'),
        ('video_recorder_gui.py', '.'),
        ('web_server.py', '.'),
    ] + pyqt6_plugins,
    hiddenimports=[
        'cv2',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtMultimedia',
        'PyQt6.QtMultimediaWidgets',
        'reportlab',
        'reportlab.pdfgen',
        'reportlab.lib',
        'reportlab.platypus',
        'barcode',
        'barcode.writer',
        'PIL',
        'PIL.Image',
        'fastapi',
        'uvicorn',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='物流视频管理',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='build/icon.png',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='物流视频管理',
)

# macOS App bundle
app = BUNDLE(
    coll,
    name='物流视频管理.app',
    icon='build/icon.png',
    bundle_identifier='com.logistics.video.recorder',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
        'LSMinimumSystemVersion': '10.13.0',
        'NSCameraUsageDescription': '需要使用摄像头录制视频',
        'NSMicrophoneUsageDescription': '需要使用麦克风录制声音',
    },
)
