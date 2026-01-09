# 构建资源目录

这个目录用于存放应用打包所需的图标和资源文件。

## 📁 必需文件

### Windows
- **icon.ico** - Windows应用图标 (256x256, ICO格式)

### macOS  
- **icon.icns** - macOS应用图标 (512x512, ICNS格式)
- **entitlements.mac.plist** - macOS权限配置 ✅ 已创建

### Linux
- **icon.png** - Linux应用图标 (512x512, PNG格式)
- **icons/** - 多尺寸图标目录
  - 16x16.png
  - 32x32.png
  - 48x48.png
  - 64x64.png
  - 128x128.png
  - 256x256.png
  - 512x512.png

## 🎨 图标生成

### 方式一：使用在线工具

1. 访问 https://www.electron.build/icons
2. 上传512x512的PNG图标
3. 下载生成的图标包
4. 将文件解压到此目录

### 方式二：使用命令行工具

```bash
# 安装electron-icon-builder
npm install --save-dev electron-icon-builder

# 生成所有平台图标
npx electron-icon-builder --input=./原始图标.png --output=./build
```

### 方式三：手动转换

**from PNG to ICO** (Windows):
- https://cloudconvert.com/png-to-ico
- 选择256x256尺寸

**PNG to ICNS** (macOS):
```bash
# 使用iconutil (仅macOS)
mkdir icon.iconset
sips -z 16 16 icon.png --out icon.iconset/icon_16x16.png
sips -z 32 32 icon.png --out icon.iconset/icon_16x16@2x.png
# ... 更多尺寸
iconutil -c icns icon.iconset
```

## 📋 检查清单

打包前请确认：

- [ ] icon.ico 已放置 (Windows)
- [ ] icon.icns 已放置 (macOS)
- [ ] icon.png 已放置 (Linux)
- [ ] icons/ 目录包含所有尺寸 (Linux)
- [ ] 图标清晰，没有模糊
- [ ] 图标符合品牌设计

## 🎯 推荐图标设计

**物流视频管理系统**建议使用：
- 主元素：📦 包裹 + 🎥 摄像头
- 配色：渐变紫色 (#667eea → #764ba2)
- 风格：扁平化，现代感
- 背景：圆角矩形或圆形

## 📷 临时方案

如果暂时没有图标，可以使用占位图标：

1. 从 `web/static/icons/icon-512x512.png` 复制
2. 使用在线工具转换为所需格式
3. 替换到此目录

---

**注意**: 图标文件不应提交到Git（体积较大），已在.gitignore中配置
