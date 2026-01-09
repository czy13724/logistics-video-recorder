"""
物流视频录制系统 - Web服务器
启动FastAPI应用和静态文件服务
"""

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import sys

# 添加web/api目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "web" / "api"))

# 导入API应用
from main import app

# 配置静态文件和模板
WEB_DIR = Path(__file__).parent / "web"
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"

# 挂载静态文件
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# 主页路由
@app.get("/")
async def serve_index():
    """提供主页面"""
    return FileResponse(TEMPLATES_DIR / "index.html")


def start_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """
    启动Web服务器
    
    Args:
        host: 服务器地址，默认0.0.0.0（允许外部访问）
        port: 服务器端口，默认8000
        reload: 是否启用热重载，开发时建议为True
    """
    print(f"""
╔══════════════════════════════════════════════════════╗
║                                                      ║
║     📦 物流视频录制管理系统 Web 服务器               ║
║                                                      ║
║     🌐 访问地址:                                     ║
║        本地: http://localhost:{port:<5}                  ║
║        局域网: http://{host}:{port:<5}              ║
║                                                      ║
║     📖 API文档: http://localhost:{port}/docs         ║
║                                                      ║
║     按 Ctrl+C 停止服务器                             ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "web_server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="物流视频录制系统Web服务器")
    parser.add_argument("--host", default="0.0.0.0", help="服务器地址")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口")
    parser.add_argument("--reload", action="store_true", help="启用热重载（开发模式）")
    
    args = parser.parse_args()
    
    start_server(host=args.host, port=args.port, reload=args.reload)
