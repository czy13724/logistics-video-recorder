import cv2
import os
import datetime
import keyboard
from threading import Thread, Event
import time
import json
from pathlib import Path

class LogisticsVideoRecorder:
    def __init__(self):
        # 加载配置
        self.config = self.load_config()
        self.camera = None
        self.current_writer = None
        self.recording = False
        self.current_tracking_number = None
        self.stop_event = Event()
        self.base_path = "videos"
        self.record_start_time = None
        self.frame_count = 0
        self.last_frame = None
        self.recording_error = False

    def load_config(self):
        """加载配置文件，如果不存在则使用默认值"""
        default_config = {
            "camera_index": 0,
            "fps": 30.0,
            "codec": "avc1",
            "resolution": [1920, 1080],
            "font_scale": 1,
            "font_thickness": 2,
            "font_color": [0, 0, 255]  # BGR格式
        }
        
        config_path = Path("config.json")
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return {**default_config, **json.load(f)}
            except Exception as e:
                print(f"加载配置文件失败: {e}，使用默认配置")
                return default_config
        return default_config

    def setup_camera(self):
        """初始化摄像头"""
        try:
            self.camera = cv2.VideoCapture(self.config["camera_index"])
            if not self.camera.isOpened():
                raise Exception("无法打开摄像头")
            
            # 设置分辨率
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config["resolution"][0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config["resolution"][1])
            
        except Exception as e:
            print(f"摄像头初始化失败: {str(e)}")
            raise

    def start_recording(self, tracking_number):
        """开始录制视频"""
        try:
            if self.recording:
                self.stop_recording()

            # 确保videos目录存在
            os.makedirs(self.base_path, exist_ok=True)
            
            # 生成文件名：快递单号_YYYYMMDD_HHMMSS.mp4
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{tracking_number}_{timestamp}.mp4"
            filepath = os.path.join(self.base_path, filename)

            # 尝试不同的编码器
            codecs = [self.config["codec"], "mp4v", "XVID"]
            writer = None
            
            for codec in codecs:
                try:
                    fourcc = cv2.VideoWriter_fourcc(*codec)
                    writer = cv2.VideoWriter(
                        filepath, 
                        fourcc, 
                        self.config["fps"],
                        (int(self.camera.get(3)), int(self.camera.get(4)))
                    )
                    if writer.isOpened():
                        break
                except Exception as e:
                    print(f"编码器 {codec} 初始化失败: {e}")
                    if writer is not None:
                        writer.release()
            
            if writer is None or not writer.isOpened():
                raise Exception("无法创建视频文件，所有编码器都失败了")
            
            self.current_writer = writer
            self.recording = True
            self.current_tracking_number = tracking_number
            self.record_start_time = time.time()
            self.frame_count = 0
            self.recording_error = False
            print(f"开始录制视频: {tracking_number}")
            
        except Exception as e:
            print(f"开始录制失败: {str(e)}")
            self.recording_error = True
            if self.current_writer is not None:
                self.current_writer.release()
                self.current_writer = None

    def stop_recording(self):
        """停止录制视频"""
        if self.recording and self.current_writer is not None:
            try:
                self.recording = False
                self.current_writer.release()
                print(f"结束录制视频: {self.current_tracking_number}")
                print(f"总共录制了 {self.frame_count} 帧")
            except Exception as e:
                print(f"停止录制时发生错误: {str(e)}")
            finally:
                self.current_tracking_number = None
                self.record_start_time = None
                self.current_writer = None

    def draw_status(self, frame):
        """在画面上显示录制状态"""
        try:
            if self.recording:
                # 添加录制状态和时长
                elapsed_time = time.time() - self.record_start_time
                minutes = int(elapsed_time // 60)
                seconds = int(elapsed_time % 60)
                
                # 显示快递单号
                cv2.putText(frame, f"单号: {self.current_tracking_number}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                           self.config["font_scale"], self.config["font_color"], 
                           self.config["font_thickness"])
                
                # 显示录制时长
                cv2.putText(frame, f"时长: {minutes:02d}:{seconds:02d}", 
                           (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 
                           self.config["font_scale"], self.config["font_color"], 
                           self.config["font_thickness"])
                
                # 显示帧率
                if elapsed_time > 0:
                    current_fps = self.frame_count / elapsed_time
                    cv2.putText(frame, f"FPS: {int(current_fps)}", 
                               (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 
                               self.config["font_scale"], self.config["font_color"], 
                               self.config["font_thickness"])
                
                # 添加红点表示录制中
                cv2.circle(frame, (20, 150), 10, (0, 0, 255), -1)
                
            if self.recording_error:
                cv2.putText(frame, "录制错误!", 
                           (10, frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 
                           self.config["font_scale"], (0, 0, 255), 
                           self.config["font_thickness"])
                
        except Exception as e:
            print(f"绘制状态信息时发生错误: {str(e)}")
        
        return frame

    def record_frame(self):
        """录制帧"""
        while not self.stop_event.is_set():
            try:
                ret, frame = self.camera.read()
                if not ret or frame is None:
                    print("无法读取摄像头画面")
                    if self.recording:
                        self.recording_error = True
                    continue

                self.last_frame = frame.copy()
                frame = self.draw_status(frame)
                
                cv2.imshow('Recording', frame)
                
                if self.recording and self.current_writer is not None and not self.recording_error:
                    self.current_writer.write(frame)
                    self.frame_count += 1
                
                # 按ESC键退出
                if cv2.waitKey(1) & 0xFF == 27:
                    break
                    
            except Exception as e:
                print(f"处理视频帧时发生错误: {str(e)}")
                if self.recording:
                    self.recording_error = True

    def handle_barcode_input(self):
        """处理条码扫描输入"""
        tracking_number = ""
        while not self.stop_event.is_set():
            try:
                event = keyboard.read_event(suppress=True)
                if event.event_type == keyboard.KEY_DOWN:
                    if event.name == 'enter':
                        if tracking_number:
                            self.start_recording(tracking_number)
                            tracking_number = ""
                    elif event.name.isalnum():
                        tracking_number += event.name
            except Exception as e:
                print(f"处理扫描输入时发生错误: {str(e)}")

    def run(self):
        """运行录制程序"""
        try:
            self.setup_camera()
            os.makedirs(self.base_path, exist_ok=True)

            # 创建并启动录制线程
            record_thread = Thread(target=self.record_frame)
            record_thread.start()

            # 处理条码输入
            self.handle_barcode_input()

        except KeyboardInterrupt:
            print("正在停止录制...")
        except Exception as e:
            print(f"程序运行时发生错误: {str(e)}")
        finally:
            self.stop_event.set()
            if self.recording:
                self.stop_recording()
            if self.camera is not None:
                self.camera.release()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    recorder = LogisticsVideoRecorder()
    recorder.run()
