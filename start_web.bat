@echo off
REM 物流视频录制系统 - Web服务器启动脚本 (Windows)

echo 🚀 正在启动物流视频录制管理系统 Web 服务器...
echo.

REM 检查虚拟环境是否存在
if not exist "venv\" (
    echo 📦 首次运行，正在创建虚拟环境...
    python -m venv venv
    
    echo 📥 安装依赖包...
    call venv\Scripts\activate.bat
    pip install -r requirements-web.txt
    echo ✅ 依赖安装完成！
    echo.
) else (
    echo ✅ 虚拟环境已存在
    call venv\Scripts\activate.bat
)

REM 启动服务器
echo 🌐 启动Web服务器...
echo.
python web_server.py %*

pause
