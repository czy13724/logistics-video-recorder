import sys
import cv2
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                            QSpinBox, QComboBox, QMessageBox, QFileDialog,
                            QTableWidget, QTableWidgetItem, QDialog, 
                            QTextEdit, QHeaderView, QCheckBox, QGroupBox,
                            QGridLayout, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QImage, QPixmap, QIcon, QFont
import barcode
from barcode.writer import ImageWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage
import time
import subprocess
import csv
from reportlab.pdfgen import canvas
import fnmatch

class VideoThread(QThread):
    frame_ready = pyqtSignal(QImage)
    error = pyqtSignal(str)
    fps_update = pyqtSignal(float)
    recording_timeout = pyqtSignal()  # 新增录制超时信号
    MAX_RECORDING_TIME = 5 * 60  # 5分钟，单位：秒
    WARNING_TIME = 30  # 剩余30秒时发出警告

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.is_running = True
        self.recording = False
        self.camera = None
        self.writer = None
        self.current_file = None
        self.frame_count = 0
        self.start_time = None
        self.warning_sent = False
        
    def run(self):
        if not self.setup_camera():
            return

        last_fps_update = datetime.now()
        frame_count = 0
        
        while self.is_running:
            ret, frame = self.camera.read()
            if not ret:
                self.error.emit("无法读取摄像头画面")
                time.sleep(0.1)  # 避免过于频繁的错误消息
                continue

            # 转换图像格式用于显示
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            # 发送图像到主线程显示
            self.frame_ready.emit(qt_image)

            # 如果正在录制，写入视频文件
            if self.recording and self.writer is not None:
                try:
                    self.writer.write(frame)
                    frame_count += 1
                    
                    # 检查录制时间
                    elapsed = (datetime.now() - self.start_time).total_seconds()
                    
                    # 检查是否接近时间限制
                    if not self.warning_sent and elapsed >= (self.MAX_RECORDING_TIME - self.WARNING_TIME):
                        self.warning_sent = True
                        self.error.emit(f"录制将在 {self.WARNING_TIME} 秒后自动停止")
                    
                    # 检查是否达到时间限制
                    if elapsed >= self.MAX_RECORDING_TIME:
                        self.recording = False
                        if self.writer:
                            self.writer.release()
                            self.writer = None
                        self.recording_timeout.emit()
                        continue

                    # 每秒更新一次FPS
                    now = datetime.now()
                    if (now - last_fps_update).total_seconds() >= 1:
                        current_fps = frame_count / elapsed if elapsed > 0 else 0
                        self.fps_update.emit(current_fps)
                        last_fps_update = now
                        
                except Exception as e:
                    self.error.emit(f"写入视频文件失败: {str(e)}")
                    self.recording = False
                    if self.writer:
                        self.writer.release()
                        self.writer = None

        # 清理资源
        if self.camera is not None:
            self.camera.release()
        if self.writer is not None:
            self.writer.release()

    def setup_camera(self):
        """设置摄像头"""
        try:
            # 尝试打开配置的摄像头
            camera_index = self.config.get("camera_index", 0)
            self.camera = cv2.VideoCapture(camera_index, cv2.CAP_ANY)
            
            if not self.camera.isOpened():
                self.error.emit(f"无法打开摄像头 {camera_index}")
                return False
                
            # 设置分辨率
            width = self.config.get("width", 640)
            height = self.config.get("height", 480)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            # 读取一帧测试摄像头
            ret, frame = self.camera.read()
            if not ret:
                self.error.emit("无法从摄像头读取画面")
                return False
                
            actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"摄像头已就绪，实际分辨率: {actual_width}x{actual_height}")
            
            return True
            
        except Exception as e:
            self.error.emit(f"设置摄像头失败: {str(e)}")
            return False

class ProblemDialog(QDialog):
    # 预设的问题类型
    PROBLEM_TYPES = [
        "退回商品非本店所售",
        "退回商品数量与申请售后数量不符",
        "商品损坏",
        "包装破损",
        "商品缺失",
        "商品型号不符",
        "其他问题"
    ]

    def __init__(self, tracking_number, parent=None):
        super().__init__(parent)
        self.tracking_number = tracking_number
        self.selected_problems = set()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"添加问题 - {self.tracking_number}")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)

        # 问题类型组
        problem_group = QGroupBox("选择问题类型")
        problem_layout = QVBoxLayout()

        # 添加预设问题类型的复选框
        self.problem_checkboxes = {}
        for problem_type in self.PROBLEM_TYPES:
            checkbox = QCheckBox(problem_type)
            checkbox.stateChanged.connect(self.on_problem_changed)
            self.problem_checkboxes[problem_type] = checkbox
            problem_layout.addWidget(checkbox)

        # 自定义问题类型
        custom_layout = QHBoxLayout()
        self.custom_problem = QLineEdit()
        self.custom_problem.setPlaceholderText("输入其他问题类型")
        add_custom_btn = QPushButton("添加")
        add_custom_btn.clicked.connect(self.add_custom_problem)
        custom_layout.addWidget(self.custom_problem)
        custom_layout.addWidget(add_custom_btn)
        problem_layout.addLayout(custom_layout)

        problem_group.setLayout(problem_layout)
        layout.addWidget(problem_group)

        # 备注输入框
        notes_group = QGroupBox("备注")
        notes_layout = QVBoxLayout()
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("在此输入详细备注信息...")
        notes_layout.addWidget(self.notes_edit)
        notes_group.setLayout(notes_layout)
        layout.addWidget(notes_group)

        # 已选问题类型显示
        selected_group = QGroupBox("已选问题")
        selected_layout = QVBoxLayout()
        self.selected_list = QListWidget()
        selected_layout.addWidget(self.selected_list)
        selected_group.setLayout(selected_layout)
        layout.addWidget(selected_group)

        # 按钮
        buttons = QHBoxLayout()
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

    def on_problem_changed(self, state):
        checkbox = self.sender()
        problem_type = checkbox.text()
        
        if state == Qt.CheckState.Checked.value:
            self.selected_problems.add(problem_type)
        else:
            self.selected_problems.discard(problem_type)
            
        self.update_selected_list()

    def add_custom_problem(self):
        custom_type = self.custom_problem.text().strip()
        if custom_type:
            if custom_type not in self.selected_problems:
                self.selected_problems.add(custom_type)
                self.update_selected_list()
                self.custom_problem.clear()

    def update_selected_list(self):
        self.selected_list.clear()
        for problem in sorted(self.selected_problems):
            self.selected_list.addItem(problem)

    def get_problems(self):
        return {
            "types": sorted(list(self.selected_problems)),
            "notes": self.notes_edit.toPlainText().strip()
        }

class BarcodeExportDialog(QDialog):
    def __init__(self, tracking_data, parent=None):
        super().__init__(parent)
        self.tracking_data = tracking_data  # [(tracking_number, time, problem_types, notes), ...]
        self.selected_numbers = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("导出条形码设置")
        self.setMinimumWidth(600)
        layout = QVBoxLayout(self)

        # 创建选项表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["选择", "快递单号", "录制时间", "问题类型", "备注"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

        # 填充表格数据
        self.table.setRowCount(len(self.tracking_data))
        for row, (number, time, problems, notes) in enumerate(self.tracking_data):
            # 添加复选框
            checkbox = QCheckBox()
            checkbox.setChecked(True)  # 默认选中
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 0, checkbox_widget)
            
            # 添加其他信息
            self.table.setItem(row, 1, QTableWidgetItem(number))
            self.table.setItem(row, 2, QTableWidgetItem(time))
            self.table.setItem(row, 3, QTableWidgetItem(problems))
            self.table.setItem(row, 4, QTableWidgetItem(notes))

        # 添加全选/取消全选按钮
        select_layout = QHBoxLayout()
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self.select_all)
        deselect_all_btn = QPushButton("取消全选")
        deselect_all_btn.clicked.connect(self.deselect_all)
        select_layout.addWidget(select_all_btn)
        select_layout.addWidget(deselect_all_btn)
        select_layout.addStretch()
        layout.addLayout(select_layout)

        # 添加设置选项
        settings_group = QWidget()
        settings_layout = QGridLayout(settings_group)

        # 条形码大小设置
        settings_layout.addWidget(QLabel("条形码宽度:"), 0, 0)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 400)
        self.width_spin.setValue(200)
        self.width_spin.setSuffix(" px")
        settings_layout.addWidget(self.width_spin, 0, 1)

        settings_layout.addWidget(QLabel("条形码高度:"), 0, 2)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(50, 200)
        self.height_spin.setValue(100)
        self.height_spin.setSuffix(" px")
        settings_layout.addWidget(self.height_spin, 0, 3)

        # 每行条形码数量
        settings_layout.addWidget(QLabel("每行条形码数:"), 1, 0)
        self.codes_per_row = QSpinBox()
        self.codes_per_row.setRange(1, 4)
        self.codes_per_row.setValue(2)
        settings_layout.addWidget(self.codes_per_row, 1, 1)

        # 附加信息选项
        self.show_time = QCheckBox("显示录制时间")
        self.show_time.setChecked(True)
        settings_layout.addWidget(self.show_time, 1, 2)

        self.show_problems = QCheckBox("显示问题描述")
        self.show_problems.setChecked(True)
        settings_layout.addWidget(self.show_problems, 1, 3)

        layout.addWidget(settings_group)

        # 添加按钮
        buttons = QHBoxLayout()
        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(export_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def select_all(self):
        self.set_all_checkboxes(True)

    def deselect_all(self):
        self.set_all_checkboxes(False)

    def set_all_checkboxes(self, checked):
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(checked)

    def get_selected_data(self):
        selected_data = []
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            if checkbox and checkbox.isChecked():
                number = self.table.item(row, 1).text()
                time = self.table.item(row, 2).text()
                problems = self.table.item(row, 3).text()
                notes = self.table.item(row, 4).text()
                selected_data.append((number, time, problems, notes))
        return selected_data

    def get_settings(self):
        return {
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "codes_per_row": self.codes_per_row.value(),
            "show_time": self.show_time.isChecked(),
            "show_problems": self.show_problems.isChecked()
        }

class VideoManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("视频管理")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        
        # 创建表格
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "选择", "快递单号", "录制时间", "问题类型", "备注", "操作", "预览"
        ])
        
        # 设置列宽
        self.table.setColumnWidth(0, 50)   # 选择
        self.table.setColumnWidth(1, 150)  # 快递单号
        self.table.setColumnWidth(2, 150)  # 录制时间
        self.table.setColumnWidth(3, 100)  # 问题类型
        self.table.setColumnWidth(4, 150)  # 备注
        self.table.setColumnWidth(5, 80)   # 操作
        self.table.setColumnWidth(6, 80)   # 预览
        
        layout.addWidget(self.table)
        
        # 添加按钮区域
        button_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self.select_all)
        button_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("取消全选")
        deselect_all_btn.clicked.connect(self.deselect_all)
        button_layout.addWidget(deselect_all_btn)
        
        save_btn = QPushButton("保存所选视频")
        save_btn.clicked.connect(self.save_selected)
        button_layout.addWidget(save_btn)
        
        delete_btn = QPushButton("删除未选视频")
        delete_btn.clicked.connect(self.delete_unselected)
        button_layout.addWidget(delete_btn)
        
        export_barcode_btn = QPushButton("导出条形码")
        export_barcode_btn.clicked.connect(self.export_barcodes)
        button_layout.addWidget(export_barcode_btn)
        
        export_csv_btn = QPushButton("导出表格")
        export_csv_btn.clicked.connect(self.export_to_csv)
        button_layout.addWidget(export_csv_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 加载视频列表
        self.load_videos()

    def preview_video(self, tracking_number, timestamp):
        """预览视频"""
        try:
            # 获取视频存放目录的绝对路径
            videos_dir = os.path.abspath(os.path.join(os.getcwd(), "videos"))
            if not os.path.exists(videos_dir):
                os.makedirs(videos_dir)
                
            # 查找匹配的视频文件
            pattern = f"{tracking_number}_{timestamp}_*.mp4"
            matching_files = [f for f in os.listdir(videos_dir) if fnmatch.fnmatch(f, pattern)]
            
            if not matching_files:
                QMessageBox.warning(self, "错误", f"找不到视频文件: {pattern}")
                return
                
            # 使用最新的文件（如果有多个匹配的文件）
            video_file = sorted(matching_files)[-1]
            video_path = os.path.join(videos_dir, video_file)
            
            print(f"正在打开视频: {video_path}")
            
            # 根据操作系统选择合适的打开方式
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", video_path])
            elif sys.platform == "win32":  # Windows
                os.startfile(video_path)
            else:  # Linux
                subprocess.run(["xdg-open", video_path])
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开视频: {str(e)}")

    def load_videos(self):
        """加载视频列表"""
        try:
            # 获取视频存放目录的绝对路径
            videos_dir = os.path.abspath(os.path.join(os.getcwd(), "videos"))
            if not os.path.exists(videos_dir):
                os.makedirs(videos_dir)
                return
                
            # 清空表格
            self.table.clearContents()
            self.table.setRowCount(0)
            
            # 获取所有MP4文件
            video_files = []
            for f in os.listdir(videos_dir):
                if f.endswith('.mp4'):
                    file_path = os.path.join(videos_dir, f)
                    # 获取文件修改时间
                    mod_time = os.path.getmtime(file_path)
                    video_files.append((f, mod_time))
            
            # 按修改时间排序（最新的在前）
            video_files.sort(key=lambda x: x[1], reverse=True)
            
            # 添加到表格
            for row, (video_file, _) in enumerate(video_files):
                try:
                    # 从文件名中提取单号和时间
                    parts = video_file.split('_')
                    if len(parts) >= 3:  # 确保至少有单号、日期和时间三部分
                        tracking_number = parts[0]
                        timestamp = parts[1]  # 只显示日期部分
                        
                        # 设置表格行数
                        self.table.setRowCount(row + 1)
                        
                        # 添加复选框
                        checkbox = QCheckBox()
                        checkbox.setChecked(True)
                        self.table.setCellWidget(row, 0, checkbox)
                        
                        # 添加其他列
                        self.table.setItem(row, 1, QTableWidgetItem(tracking_number))
                        self.table.setItem(row, 2, QTableWidgetItem(timestamp))
                        
                        # 添加问题和备注占位符
                        self.table.setItem(row, 3, QTableWidgetItem(""))
                        self.table.setItem(row, 4, QTableWidgetItem(""))
                        
                        # 添加操作按钮
                        problem_btn = QPushButton("添加问题")
                        problem_btn.clicked.connect(lambda checked, r=row: self.add_problem(r))
                        self.table.setCellWidget(row, 5, problem_btn)
                        
                        # 添加预览按钮
                        preview_btn = QPushButton("预览")
                        # 使用 lambda 捕获当前值而不是引用
                        preview_btn.clicked.connect(
                            lambda checked, t=tracking_number, ts=timestamp: 
                            self.preview_video(t, ts)
                        )
                        self.table.setCellWidget(row, 6, preview_btn)
                        
                except Exception as e:
                    print(f"处理视频文件 {video_file} 时出错: {str(e)}")
                    continue
            
            print(f"已加载 {len(video_files)} 个视频")
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载视频列表失败: {str(e)}")

    def select_all(self):
        """选择所有视频"""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)

    def deselect_all(self):
        """取消选择所有视频"""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)

    def save_selected(self):
        """保存选中的视频"""
        try:
            selected = self.get_selected_videos()
            if not selected:
                QMessageBox.warning(self, "警告", "请先选择要保存的视频")
                return
                
            save_dir = QFileDialog.getExistingDirectory(self, "选择保存目录")
            if not save_dir:
                return
                
            videos_dir = os.path.abspath(os.path.join(os.getcwd(), "videos"))
            
            for tracking_number, time_str, _, _ in selected:
                time_str = time_str.replace(":", "")
                source_file = os.path.join(videos_dir, f"{tracking_number}_{time_str}.mp4")
                target_file = os.path.join(save_dir, f"{tracking_number}_{time_str}.mp4")
                
                if os.path.exists(source_file):
                    shutil.copy2(source_file, target_file)
            
            QMessageBox.information(self, "成功", "选中的视频已保存")
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存视频失败: {str(e)}")

    def delete_unselected(self):
        """删除未选中的视频"""
        try:
            reply = QMessageBox.question(
                self, "确认删除", 
                "确定要删除未选中的视频吗？此操作不可恢复。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
                
            selected = self.get_selected_videos()
            selected_files = set()
            
            videos_dir = os.path.abspath(os.path.join(os.getcwd(), "videos"))
            
            # 收集选中的文件名
            for tracking_number, time_str, _, _ in selected:
                time_str = time_str.replace(":", "")
                selected_files.add(f"{tracking_number}_{time_str}.mp4")
            
            # 删除未选中的文件
            deleted_count = 0
            for file in os.listdir(videos_dir):
                if file.endswith(".mp4") and file not in selected_files:
                    os.remove(os.path.join(videos_dir, file))
                    deleted_count += 1
            
            QMessageBox.information(self, "成功", f"已删除 {deleted_count} 个未选中的视频")
            self.load_videos()  # 重新加载列表
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"删除视频失败: {str(e)}")

    def get_next_pdf_filename(self, directory, base_name, extension):
        """获取下一个可用的文件名
        例如: 20250107.pdf, 20250107_1.pdf, 20250107_2.pdf"""
        # 确保目录存在
        os.makedirs(directory, exist_ok=True)
        
        # 确保扩展名以.开头
        if not extension.startswith('.'):
            extension = '.' + extension
            
        # 检查基本文件名是否存在
        if not os.path.exists(os.path.join(directory, base_name + extension)):
            return base_name + extension
            
        # 如果存在，添加数字后缀
        index = 1
        while True:
            new_name = f"{base_name}_{index}{extension}"
            if not os.path.exists(os.path.join(directory, new_name)):
                return new_name
            index += 1

    def export_barcodes(self):
        """导出所选视频的条形码"""
        try:
            selected = self.get_selected_videos()
            if not selected:
                QMessageBox.warning(self, "警告", "请先选择要导出条形码的视频")
                return
            
            # 获取下一个可用的文件名
            exports_dir = os.path.abspath(os.path.join(os.getcwd(), "exports"))
            os.makedirs(exports_dir, exist_ok=True)
            base_name = datetime.now().strftime("%Y%m%d")
            default_filename = self.get_next_pdf_filename(exports_dir, base_name, '.pdf')
            
            # 选择保存路径，使用默认文件名
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "保存条形码PDF", 
                os.path.join(exports_dir, default_filename),
                "PDF文件 (*.pdf)"
            )
            
            if not file_path:
                return
            
            if not file_path.endswith('.pdf'):
                file_path += '.pdf'
            
            # 确保文件保存在exports目录下
            if not os.path.dirname(file_path) == exports_dir:
                file_path = os.path.join(exports_dir, os.path.basename(file_path))
            
            # 创建PDF
            settings = {
                "width": 300,
                "height": 100,
                "show_time": True,
                "show_problems": True
            }
            
            if self.create_barcode_pdf(selected, file_path, settings):
                QMessageBox.information(self, "成功", f"条形码PDF已生成: {os.path.basename(file_path)}")
            else:
                QMessageBox.warning(self, "错误", "生成PDF失败")
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导出条形码失败: {str(e)}")

    def generate_barcode(self, tracking_number, output_path):
        """生成单个条形码图片"""
        try:
            # 使用 Code128 生成条形码
            code128 = barcode.get('code128', tracking_number, writer=ImageWriter())
            filename = code128.save(output_path)
            
            # 使用 PIL 调整图片大小
            with PILImage.open(filename) as img:
                # 调整到合适的大小
                new_size = (300, 100)  # 根据需要调整尺寸
                img = img.resize(new_size, PILImage.LANCZOS)
                img.save(filename)
                
            return filename
        except Exception as e:
            print(f"生成条形码失败: {str(e)}")
            return None

    def create_barcode_pdf(self, tracking_data, output_path, settings):
        """创建包含所有条形码的PDF文件"""
        try:
            # 创建临时目录存放条形码图片
            temp_dir = "temp_barcodes"
            os.makedirs(temp_dir, exist_ok=True)
            
            # 准备文档
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            elements = []
            
            # 添加标题
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30
            )
            elements.append(Paragraph("物流单号条形码", title_style))
            
            # 为每个单号生成条形码
            for tracking_number, time_str, problems, notes in tracking_data:
                # 生成条形码图片
                barcode_path = os.path.join(temp_dir, f"{tracking_number}.png")
                barcode_file = self.generate_barcode(tracking_number, barcode_path)
                
                if barcode_file and os.path.exists(barcode_file):
                    # 添加条形码图片
                    img = Image(barcode_file, width=300, height=100)
                    elements.append(img)
                    
                    # 添加单号文本
                    elements.append(Paragraph(f"单号: {tracking_number}", styles['Normal']))
                    if problems:
                        elements.append(Paragraph(f"问题: {problems}", styles['Normal']))
                    if notes:
                        elements.append(Paragraph(f"备注: {notes}", styles['Normal']))
                    
                    # 添加间距
                    elements.append(Spacer(1, 20))
            
            # 生成PDF
            doc.build(elements)
            
            # 清理临时文件
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return True
        except Exception as e:
            print(f"生成PDF失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def add_problem(self, row):
        tracking_number = self.table.item(row, 1).text()
        dialog = ProblemDialog(tracking_number, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            problems = dialog.get_problems()
            # 更新表格
            self.table.setItem(row, 3, QTableWidgetItem(", ".join(problems["types"])))
            self.table.setItem(row, 4, QTableWidgetItem(problems["notes"]))

    def get_selected_videos(self):
        """获取选中的视频"""
        selected = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                tracking_number = self.table.item(row, 1).text()
                time_str = self.table.item(row, 2).text()
                problems = self.table.item(row, 3).text()
                notes = self.table.item(row, 4).text()
                selected.append((tracking_number, time_str, problems, notes))
        return selected

    def export_to_csv(self):
        """导出表格到CSV"""
        try:
            # 创建reports目录
            reports_dir = os.path.abspath(os.path.join(os.getcwd(), "reports"))
            os.makedirs(reports_dir, exist_ok=True)
            
            # 生成默认文件名（日期）
            base_name = datetime.now().strftime("%Y%m%d")
            default_filename = self.get_next_pdf_filename(reports_dir, base_name, '.csv')
            
            # 获取保存文件路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出表格",
                os.path.join(reports_dir, default_filename),
                "CSV Files (*.csv)"
            )
            
            if not file_path:
                return
                
            # 确保文件以.csv结尾
            if not file_path.endswith('.csv'):
                file_path += '.csv'
                
            # 确保文件保存在reports目录下
            if not os.path.dirname(file_path) == reports_dir:
                file_path = os.path.join(reports_dir, os.path.basename(file_path))
                
            # 写入CSV文件
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # 写入表头
                writer.writerow(["快递单号", "录制时间", "问题类型", "备注"])
                
                # 写入数据
                for row in range(self.table.rowCount()):
                    checkbox = self.table.cellWidget(row, 0)
                    if checkbox and checkbox.isChecked():
                        # 获取每列的数据
                        tracking_number = self.table.item(row, 1).text()
                        timestamp = self.table.item(row, 2).text()
                        problems = self.table.item(row, 3).text()
                        notes = self.table.item(row, 4).text()
                        
                        # 写入一行数据
                        writer.writerow([tracking_number, timestamp, problems, notes])
            
            QMessageBox.information(self, "成功", f"表格已导出到: {file_path}")
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导出表格失败: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("物流退货拆包视频录制工具")
        self.video_thread = None
        self.ready_to_record = False
        self.recording_start_time = None
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self.update_duration)
        self.available_cameras = self.get_available_cameras()
        self.setup_ui()
        # 使用第一个可用的摄像头
        if self.available_cameras:
            self.setup_video_thread(self.available_cameras[0]['index'])

    def get_available_cameras(self):
        """获取所有可用的摄像头"""
        available_cameras = []
        try:
            # 在 macOS 上检测摄像头
            for i in range(10):  # 检查前10个摄像头索引
                try:
                    cap = cv2.VideoCapture(i, cv2.CAP_ANY)
                    if cap.isOpened():
                        ret, _ = cap.read()  # 尝试读取一帧
                        if ret:
                            available_cameras.append({
                                'index': i,
                                'name': f'摄像头 {i}'
                            })
                    cap.release()
                except Exception as e:
                    print(f"检测摄像头 {i} 失败: {str(e)}")
                    continue
                    
            # 如果没有找到摄像头，添加默认摄像头
            if not available_cameras:
                available_cameras.append({
                    'index': 0,
                    'name': '默认摄像头'
                })
                
            print(f"找到 {len(available_cameras)} 个摄像头")
            return available_cameras
            
        except Exception as e:
            print(f"检测摄像头时出错: {str(e)}")
            # 返回默认摄像头
            return [{
                'index': 0,
                'name': '默认摄像头'
            }]

    def setup_ui(self):
        self.setMinimumSize(800, 600)

        # 创建中心部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # 添加摄像头选择下拉框
        camera_layout = QHBoxLayout()
        camera_label = QLabel("选择摄像头:")
        self.camera_combo = QComboBox()
        for camera in self.available_cameras:
            self.camera_combo.addItem(camera['name'], camera['index'])
        self.camera_combo.currentIndexChanged.connect(self.change_camera)
        camera_layout.addWidget(camera_label)
        camera_layout.addWidget(self.camera_combo)
        camera_layout.addStretch()
        layout.addLayout(camera_layout)

        # 快递单号输入框
        tracking_layout = QHBoxLayout()
        tracking_label = QLabel("快递单号:")
        self.tracking_input = QLineEdit()
        self.tracking_input.setPlaceholderText("请扫描或输入快递单号")
        self.tracking_input.returnPressed.connect(self.handle_input)
        tracking_layout.addWidget(tracking_label)
        tracking_layout.addWidget(self.tracking_input)
        layout.addLayout(tracking_layout)

        # 当前单号显示
        current_number_layout = QHBoxLayout()
        current_number_label = QLabel("当前单号:")
        self.current_number_label = QLabel("")
        current_number_layout.addWidget(current_number_label)
        current_number_layout.addWidget(self.current_number_label)
        layout.addLayout(current_number_layout)

        # 状态显示
        status_layout = QHBoxLayout()
        status_label = QLabel("状态:")
        self.status_label = QLabel("等待新的单号")
        self.status_label.setStyleSheet("color: gray;")
        status_layout.addWidget(status_label)
        status_layout.addWidget(self.status_label)
        layout.addLayout(status_layout)

        # 录制时长显示
        duration_layout = QHBoxLayout()
        duration_label = QLabel("录制时长:")
        self.duration_label = QLabel("00:00")
        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(self.duration_label)
        duration_layout.addWidget(QLabel("(最长录制时间: 5分钟)"))
        layout.addLayout(duration_layout)

        # 视频预览区域
        self.video_label = QLabel()
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_label)

        # 按钮区域
        button_layout = QHBoxLayout()
        self.record_button = QPushButton("开始录制")
        self.record_button.clicked.connect(self.start_recording)
        self.record_button.setEnabled(True)  # 初始状态可用
        
        self.stop_button = QPushButton("停止录制")
        self.stop_button.clicked.connect(self.stop_recording)
        self.stop_button.setEnabled(False)
        
        self.manage_button = QPushButton("管理视频")
        self.manage_button.clicked.connect(self.show_video_manager)
        
        button_layout.addWidget(self.record_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.manage_button)
        layout.addLayout(button_layout)

        # 状态栏
        self.statusBar()

    def change_camera(self, index):
        """切换摄像头"""
        try:
            if self.video_thread and self.video_thread.recording:
                QMessageBox.warning(self, "警告", "请先停止当前视频的录制")
                # 恢复之前的选择
                self.camera_combo.setCurrentIndex(self.camera_combo.findData(self.video_thread.config["camera_index"]))
                return

            camera_index = self.camera_combo.currentData()
            if self.video_thread:
                self.video_thread.is_running = False
                self.video_thread.wait()
                self.video_thread = None

            self.setup_video_thread(camera_index)
            print(f"已切换到摄像头 {camera_index}")

        except Exception as e:
            self.show_error(f"切换摄像头失败: {str(e)}")

    def setup_video_thread(self, camera_index):
        """设置视频线程"""
        try:
            if self.video_thread is None:
                config = {
                    "camera_index": camera_index,
                    "width": 640,
                    "height": 480
                }
                self.video_thread = VideoThread(config)
                self.video_thread.frame_ready.connect(self.update_frame)
                self.video_thread.error.connect(self.show_error)
                self.video_thread.fps_update.connect(self.update_fps)
                self.video_thread.recording_timeout.connect(self.handle_recording_timeout)
                self.video_thread.start()
                
                # 等待摄像头初始化
                time.sleep(1)
                
                if not self.video_thread.camera or not self.video_thread.camera.isOpened():
                    raise Exception("摄像头初始化失败")
                    
                print(f"视频线程已启动，使用摄像头 {camera_index}")
        except Exception as e:
            self.show_error(f"设置视频线程失败: {str(e)}")

    def update_frame(self, image):
        scaled_image = image.scaled(self.video_label.size(), 
                                  Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
        self.video_label.setPixmap(QPixmap.fromImage(scaled_image))

    def show_error(self, message):
        QMessageBox.warning(self, "错误", message)

    def update_fps(self, fps):
        self.statusBar().showMessage(f"当前FPS: {fps:.1f}")

    def start_recording(self):
        """开始录制"""
        try:
            tracking_number = self.tracking_input.text().strip()
            if not tracking_number:
                QMessageBox.warning(self, "警告", "请先输入或扫描快递单号")
                return
                
            if self.video_thread and self.video_thread.recording:
                QMessageBox.warning(self, "警告", "请先停止当前视频的录制")
                return
                
            if not self.video_thread or not self.video_thread.camera or not self.video_thread.camera.isOpened():
                # 使用当前选择的摄像头
                camera_index = self.camera_combo.currentData()
                self.setup_video_thread(camera_index)
                
            if not self.video_thread or not self.video_thread.camera or not self.video_thread.camera.isOpened():
                raise Exception("摄像头未就绪，请检查摄像头连接")
                
            # 创建视频保存目录
            videos_dir = os.path.abspath(os.path.join(os.getcwd(), "videos"))
            os.makedirs(videos_dir, exist_ok=True)
            
            # 生成视频文件名（包含时分秒）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_filename = f"{tracking_number}_{timestamp}.mp4"
            video_path = os.path.join(videos_dir, video_filename)
            
            # 设置视频写入器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            frame_size = (int(self.video_thread.camera.get(cv2.CAP_PROP_FRAME_WIDTH)),
                         int(self.video_thread.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)))
            self.video_thread.writer = cv2.VideoWriter(
                video_path, 
                fourcc, 
                30.0,  # FPS
                frame_size
            )
            
            if not self.video_thread.writer.isOpened():
                raise Exception("无法创建视频文件")
            
            # 设置录制状态
            self.video_thread.recording = True
            self.video_thread.start_time = datetime.now()
            self.recording_start_time = datetime.now()
            self.video_thread.frame_count = 0
            self.video_thread.warning_sent = False
            self.video_thread.current_file = video_path
            
            # 更新界面状态
            self.current_number_label.setText(tracking_number)
            self.status_label.setText("正在录制")
            self.status_label.setStyleSheet("color: red;")
            self.record_button.setEnabled(False)  # 录制时禁用开始录制按钮
            self.stop_button.setEnabled(True)
            self.tracking_input.setEnabled(True)
            self.tracking_input.clear()
            
            # 开始计时
            self.recording_timer.start(1000)
            
            print(f"开始录制视频: {video_path}")
            
        except Exception as e:
            self.show_error(f"开始录制失败: {str(e)}")

    def stop_recording(self):
        """停止录制"""
        try:
            if self.video_thread and self.video_thread.recording:
                self.video_thread.recording = False
                if self.video_thread.writer:
                    self.video_thread.writer.release()
                    print(f"视频已保存: {self.video_thread.current_file}")
                    self.video_thread.writer = None
                
            # 停止计时器
            self.recording_timer.stop()
            self.recording_start_time = None
            
            # 重置界面状态
            self.status_label.setText("等待新的单号")
            self.status_label.setStyleSheet("color: gray;")
            self.record_button.setEnabled(True)  # 停止录制后启用开始录制按钮
            self.stop_button.setEnabled(False)
            self.ready_to_record = False
            
            # 清空当前单号显示
            self.current_number_label.setText("")
            
            # 重置录制时间显示
            self.duration_label.setText("00:00")
            
        except Exception as e:
            self.show_error(f"停止录制失败: {str(e)}")

    def show_video_manager(self):
        dialog = VideoManagerDialog(self)
        dialog.exec()

    def handle_input(self):
        """处理输入框的回车事件"""
        tracking_number = self.tracking_input.text().strip()
        if not tracking_number:
            QMessageBox.warning(self, "警告", "请输入快递单号")
            return
            
        # 验证单号格式
        if len(tracking_number) < 5:  # 假设单号至少5位
            QMessageBox.warning(self, "警告", "请输入有效的快递单号")
            return
            
        # 回车后直接开始录制
        self.start_recording()

    def handle_barcode_input(self, tracking_number):
        """处理条码输入（扫描或手动）"""
        if self.video_thread and self.video_thread.recording:
            QMessageBox.warning(self, "警告", "请先停止当前视频的录制")
            return
            
        # 扫描输入时直接开始录制
        self.start_recording(tracking_number)

    def update_duration(self):
        """更新录制时长显示"""
        if not self.recording_start_time:
            return
            
        elapsed = int((datetime.now() - self.recording_start_time).total_seconds())
        minutes = elapsed // 60
        seconds = elapsed % 60
        self.duration_label.setText(f"{minutes:02d}:{seconds:02d}")

    def handle_recording_timeout(self):
        """处理录制超时"""
        self.stop_recording()
        QMessageBox.information(self, "录制结束", 
            "已达到最大录制时间（5分钟），录制已自动停止。\n请扫描或输入新的单号开始下一个录制。")

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "确认退出", 
            "确定要退出程序吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.video_thread.is_running = False
            self.video_thread.wait()
            event.accept()
        else:
            event.ignore()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
