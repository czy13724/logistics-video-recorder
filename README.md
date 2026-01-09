# 物流视频录制管理系统 v2.0

> 🎥 专业的物流退货视频录制与管理解决方案

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com)

## ✨ 特性

- 📹 **视频录制** - 支持多摄像头，实时预览，自动保存
- 🌐 **Web管理** - 现代化界面，在线播放，数据可视化  
- 📱 **PWA移动端** - 可安装到手机，离线访问，原生体验
- 💻 **桌面应用** - PyQt6原生应用，支持Windows/Mac/Linux
- 🤖 **自动化构建** - GitHub Actions自动打包所有平台
- 📊 **数据统计** - 图表展示，趋势分析，问题追踪
- 🎨 **现代化UI** - 深色主题，渐变色彩，流畅动画

## 🚀 快速开始

### 方式一：下载安装包（推荐）

从 [Releases](../../releases) 下载对应平台的安装包：
- **Windows**: `物流视频管理.exe`
- **macOS**: `物流视频管理.dmg`
- **Linux**: `物流视频管理-x86_64.AppImage`

双击运行即可使用！

### 方式二：源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/czy13724/logistics-video-recorder.git
cd logistics-video-recorder

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行桌面应用
python run.py

# 或运行Web端
./start_web.sh  # Mac/Linux
start_web.bat   # Windows
```

## 📦 运行模式

## 主要功能

1. **视频录制**
   - 支持多个摄像头选择
   - 实时预览摄像头画面
   - 扫描或输入快递单号后开始录制
   - 自动保存视频到指定目录

2. **视频管理**
   - 查看所有录制的视频记录
   - 预览已录制的视频
   - 为视频添加问题标记和备注
   - 删除不需要的视频

3. **数据导出**
   - 导出视频记录到 CSV 表格（保存在 reports 目录）
   - 导出快递单号条形码到 PDF 文件（保存在 exports 目录）

## 软件包
   - 可自行编辑为软件使用

## 安装说明

1. 确保已安装 Python 3.6 或更高版本
2. 安装依赖包：
   ```bash
   pip install -r requirements.txt
   ```

## 使用说明

1. **启动程序**
   ```bash
   python run.py
   ```

2. **录制视频**
   - 选择要使用的摄像头
   - 输入或扫描快递单号
   - 点击"开始录制"按钮
   - 完成录制后点击"停止录制"按钮

3. **管理视频**
   - 在主界面的表格中查看所有视频记录
   - 使用复选框选择要操作的视频
   - 点击"预览"按钮查看视频
   - 点击"添加问题"按钮记录问题
   - 点击"删除"按钮删除视频

4. **导出数据**
   - 选择要导出的视频记录
   - 点击"导出表格"按钮导出 CSV 文件（保存在 reports 目录）
   - 点击"导出条形码"按钮导出 PDF 文件（保存在 exports 目录）

## 文件说明

- `run.py`: 程序入口文件
- `video_recorder_gui.py`: 主要的 GUI 界面代码
- `video_recorder.py`: 视频录制相关的核心功能
- `config.json`: 配置文件
- `requirements.txt`: 项目依赖包列表
- `videos/`: 存放录制的视频文件
- `reports/`: 存放导出的 CSV 表格文件
- `exports/`: 存放导出的条形码 PDF 文件

## 注意事项

1. 确保摄像头正常连接并且驱动正确安装
2. 视频文件会自动保存在 videos 目录下
3. 导出的 CSV 表格会保存在 reports 目录下
4. 导出的条形码 PDF 会保存在 exports 目录下
5. 文件命名格式：
   - 视频文件：`快递单号_YYYYMMDD_HHMMSS.mp4`
   - CSV 文件：`YYYYMMDD.csv` 或 `YYYYMMDD_1.csv`
   - PDF 文件：`YYYYMMDD.pdf` 或 `YYYYMMDD_1.pdf`

## 常见问题

1. **找不到摄像头**
   - 检查摄像头是否正确连接
   - 检查摄像头驱动是否安装
   - 重新启动程序

2. **无法预览视频**
   - 确认视频文件存在于 videos 目录中
   - 检查视频文件是否损坏
   - 确保系统安装了正确的视频解码器

3. **导出文件失败**
   - 确保有足够的磁盘空间
   - 检查是否有文件写入权限
   - 确保文件没有被其他程序占用

## 🌐 Web端管理系统（新功能）

除了桌面应用，现在支持通过浏览器访问的Web管理界面！

### Web端特性

1. **📊 数据概览仪表板**
   - 实时统计视频数量、问题统计
   - 可视化图表展示录制趋势
   - 问题类型分布饼图
   - 存储空间监控

2. **🎥 视频在线管理**
   - 浏览所有录制视频
   - 在线播放视频
   - 添加/编辑问题标记和备注
   - 高级搜索和筛选功能
   - 删除视频操作

3. **📥 导出文件管理**
   - 查看所有导出的CSV和PDF文件
   - 在线下载导出文件

4. **🎨 现代化界面**
   - 深色主题设计
   - 渐变色彩和流畅动画
   - 响应式布局，支持移动设备访问
   - 直观的用户体验

5. **📱 PWA移动端App（NEW！）**
   - 可安装到手机主屏幕，像原生App一样使用
   - 支持离线访问（缓存静态资源）
   - 全屏沉浸式体验
   - 自动更新，无需手动下载
   - iOS和Android全平台支持
   - 详细安装指南见 `PWA安装指南.md`

### Web端安装

1. 安装Web依赖：
   ```bash
   pip install -r requirements-web.txt
   ```

### Web端使用

1. **启动Web服务器**
   ```bash
   python web_server.py
   ```

2. **自定义端口和地址**
   ```bash
   python web_server.py --port 8080 --host 0.0.0.0
   ```

3. **开发模式（支持热重载）**
   ```bash
   python web_server.py --reload
   ```

4. **访问Web界面**
   - 本地访问: http://localhost:8000
   - 局域网访问: http://your-ip:8000
   - API文档: http://localhost:8000/docs

### Web端使用说明

#### 数据概览
- 打开浏览器访问主页，默认显示数据概览页面
- 查看总视频数、今日录制、问题统计等关键指标
- 通过图表了解最近7天的录制趋势和问题类型分布

#### 视频管理
1. 点击左侧"视频管理"菜单
2. 使用搜索框或日期筛选器查找特定视频
3. 点击视频卡片查看详情和播放
4. 在弹出窗口中可以：
   - 播放视频
   - 添加问题标记
   - 编辑备注信息
   - 删除视频

#### 导出管理
1. 点击左侧"导出文件"菜单
2. 查看所有导出的CSV表格和PDF条形码文件
3. 点击下载按钮获取文件

### Web API接口

系统提供完整的RESTful API，详细文档访问 `/docs`

主要接口：
- `GET /api/videos` - 获取视频列表（支持搜索和筛选）
- `GET /api/videos/{tracking_number}/stream` - 播放视频
- `PUT /api/videos/{tracking_number}/problems` - 更新问题标记
- `DELETE /api/videos/{tracking_number}` - 删除视频
- `GET /api/stats` - 获取统计数据
- `GET /api/exports` - 获取导出文件列表

---

## 更新日志

### 2026-01-09
- 🎉 **重大更新**: 新增Web端管理系统
- 添加FastAPI后端API服务
- 实现现代化的Web界面
- 支持在线视频播放和管理
- 提供数据可视化仪表板
- 完善的搜索和筛选功能

### 2025-01-07
- 修复了视频预览功能
- 改进了文件保存路径管理
- 统一了文件命名规则
- 添加了导出文件的目录管理
- 改进了用户界面提示信息
