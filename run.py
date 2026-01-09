#!/usr/bin/env python3
import os
import sys
import subprocess
import site
import glob

def find_qt_plugin_path():
    """查找 Qt 插件路径（支持PyInstaller打包后的应用）"""
    # 检查是否是PyInstaller打包的应用
    if getattr(sys, 'frozen', False):
        # 打包后的应用
        if sys.platform == 'darwin':  # macOS
            # macOS应用bundle路径
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller临时目录
                base_path = sys._MEIPASS
            else:
                # 应用bundle内的路径
                base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(sys.executable))))
            
            # 在应用bundle中查找Qt插件
            possible_paths = [
                os.path.join(base_path, 'Contents', 'Frameworks', 'PyQt6', 'Qt6', 'plugins'),
                os.path.join(base_path, 'Contents', 'Frameworks', 'PyQt6', 'Qt', 'plugins'),
                os.path.join(base_path, 'PyQt6', 'Qt6', 'plugins'),
                os.path.join(base_path, 'PyQt6', 'Qt', 'plugins'),
            ]
        else:
            # Windows/Linux
            if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(sys.executable))
            
            possible_paths = [
                os.path.join(base_path, 'PyQt6', 'Qt6', 'plugins'),
                os.path.join(base_path, 'PyQt6', 'Qt', 'plugins'),
            ]
    else:
        # 开发环境
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        possible_paths = [
            os.path.join(os.path.dirname(os.__file__), "site-packages", "PyQt6", "Qt6", "plugins"),
            os.path.join(os.path.dirname(os.__file__), "site-packages", "PyQt6", "Qt", "plugins"),
            os.path.join(os.getcwd(), "venv", "lib", f"python{python_version}", "site-packages", "PyQt6", "Qt6", "plugins"),
            os.path.join(os.getcwd(), "venv", "lib", f"python{python_version}", "site-packages", "PyQt6", "Qt", "plugins"),
        ]
    
    for path in possible_paths:
        if os.path.exists(path) and os.path.exists(os.path.join(path, "platforms")):
            print(f"找到 Qt 插件路径: {path}")
            return path
            
    # 如果没找到，尝试使用 pip show 命令（仅开发环境）
    if not getattr(sys, 'frozen', False):
        try:
            result = subprocess.check_output([sys.executable, "-m", "pip", "show", "PyQt6"]).decode()
            for line in result.split("\n"):
                if line.startswith("Location:"):
                    base_path = line.split(": ")[1].strip()
                    qt_path = os.path.join(base_path, "PyQt6", "Qt6", "plugins")
                    if os.path.exists(qt_path) and os.path.exists(os.path.join(qt_path, "platforms")):
                        print(f"找到 Qt 插件路径: {qt_path}")
                        return qt_path
        except:
            pass
        
    return None

# 在导入PyQt6之前设置Qt插件路径（关键！）
def setup_qt_environment():
    """在导入PyQt6之前设置Qt环境"""
    qt_plugin_path = find_qt_plugin_path()
    if qt_plugin_path:
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_plugin_path
        print(f"设置 Qt 插件路径: {qt_plugin_path}")
    else:
        print("警告: 未找到 Qt 插件路径，可能会出现问题")
    
    # macOS特定设置
    if sys.platform == 'darwin':
        # 设置Qt库路径
        if getattr(sys, 'frozen', False):
            if hasattr(sys, '_MEIPASS'):
                qt_lib_path = os.path.join(sys._MEIPASS, 'PyQt6', 'Qt6', 'lib')
                if os.path.exists(qt_lib_path):
                    os.environ['DYLD_LIBRARY_PATH'] = qt_lib_path

# 立即设置Qt环境（在任何PyQt6导入之前）
setup_qt_environment()

def check_and_install_dependencies():
    """检查并安装所需的依赖"""
    required = {
        'PyQt6': ['PyQt6'],
        'opencv-python': ['opencv-python'],
        'numpy': ['numpy'],
        'python-barcode': ['python-barcode'],
        'reportlab': ['reportlab'],
        'Pillow': ['Pillow']
    }
    
    print("正在检查并安装依赖...")
    
    for package_group, packages in required.items():
        print(f"\n检查 {package_group}...")
        try:
            if package_group == 'PyQt6':
                 import PyQt6.QtCore
            else:
                # 尝试导入
                if package_group == 'opencv-python':
                    import cv2
                elif package_group == 'Pillow':
                    import PIL
                else:
                    __import__(package_group.replace('-', '_'))
                print(f"✓ {package_group} 已安装")
        except (ImportError, ModuleNotFoundError):
            print(f"安装 {package_group}...")
            for pkg in packages:
                try:
                    subprocess.check_call([
                        sys.executable, "-m", "pip", "install",
                        "--no-cache-dir",
                        "--index-url", "https://pypi.org/simple",
                        pkg
                    ])
                    print(f"✓ {pkg} 安装成功")
                except subprocess.CalledProcessError as e:
                    print(f"✗ {pkg} 安装失败: {str(e)}")
                    sys.exit(1)
        except Exception as e:
            print(f"✗ {package_group} 检查失败: {str(e)}")
            sys.exit(1)
    
    print("\n所有依赖检查完成")

def main():
    """主函数"""
    # 注意：Qt环境已经在文件顶部设置好了
    # 注意：Qt环境已经在文件顶部设置好了
    if not getattr(sys, 'frozen', False):
        print("检查依赖...")
        check_and_install_dependencies()
    
    print("\n启动应用程序...")
    try:
        # 打印调试信息
        print(f"Python 路径: {sys.executable}")
        print(f"工作目录: {os.getcwd()}")
        print(f"QT_QPA_PLATFORM_PLUGIN_PATH: {os.environ.get('QT_QPA_PLATFORM_PLUGIN_PATH', '未设置')}")
        if sys.platform == 'darwin':
            print(f"DYLD_LIBRARY_PATH: {os.environ.get('DYLD_LIBRARY_PATH', '未设置')}")
        
        # 现在可以安全地导入PyQt6
        import video_recorder_gui
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication(sys.argv)
        window = video_recorder_gui.MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"启动失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
