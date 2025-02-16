import win32api
import win32con
import os
import subprocess
import time
import logging
import threading
import winshell
import sys
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QFileDialog, QMessageBox, QLabel
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# 显示器信息模块
class DisplayInfo:
    @staticmethod
    def get_monitors():
        """获取所有显示器信息"""
        monitors = []
        try:
            for i, monitor in enumerate(win32api.EnumDisplayMonitors(None, None)):
                monitor_info = win32api.GetMonitorInfo(monitor[0])
                monitors.append({
                    "index": i,
                    "handle": monitor[0],
                    "position": monitor_info["Monitor"],
                    "work_area": monitor_info["Work"],
                    "device": monitor_info["Device"]
                })
        except Exception as e:
            logging.error(f"获取显示器信息失败: {e}")
        return monitors

    @staticmethod
    def get_monitor_info_text():
        """获取格式化显示器信息"""
        info = []
        for monitor in DisplayInfo.get_monitors():
            pos = monitor["position"]
            info.append(
                f"屏幕 {monitor['index'] + 1} ({monitor['device']}):\n"
                f"  位置: 左={pos[0]}, 上={pos[1]}, 右={pos[2]}, 下={pos[3]}\n"
                f"  分辨率: {pos[2] - pos[0]}x{pos[3] - pos[1]}"
            )
        return "\n\n".join(info)


# VLC 控制器模块
class VLCController:
    def __init__(self, vlc_path=None):
        self.logger = logging.getLogger(__name__)
        self.vlc_path = vlc_path or self.find_vlc()
        self.processes = []
        self.playback_status = {}

    def find_vlc(self):
        """自动查找VLC安装路径"""
        possible_paths = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            os.path.expanduser("~\\AppData\\Local\\VLC\\vlc.exe")
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return os.path.normpath(path)
        raise FileNotFoundError("VLC未找到，请手动指定路径")

    def build_command(self, video_path, monitor_info):
        """构建VLC命令行参数"""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        monitor = monitor_info["position"]
        width = monitor[2] - monitor[0]
        height = monitor[3] - monitor[1]
        video_path = os.path.normpath(video_path)
        self.logger.info(f"使用的视频路径: {video_path}")
        return [
            self.vlc_path,
            "--fullscreen",
            video_path
        ]

    def start_vlc_instance(self, video_path, monitor_info):
        """启动VLC实例"""
        try:
            cmd = self.build_command(video_path, monitor_info)
            self.logger.info(f"启动VLC命令: {' '.join(cmd)}")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if stdout:
                self.logger.info(f"VLC 标准输出: {stdout.decode('utf-8', errors='ignore')}")
            if stderr:
                self.logger.error(f"VLC 标准错误: {stderr.decode('utf-8', errors='ignore')}")
            self.processes.append(process)
            self.playback_status[process.pid] = {
                "start_time": time.time(),
                "status": "playing"
            }
            return True
        except Exception as e:
            self.logger.error(f"启动VLC失败: {str(e)}")
            return False

    def stop_all(self):
        """停止所有VLC进程"""
        for p in self.processes:
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception as e:
                try:
                    p.kill()
                except Exception as e2:
                    self.logger.error(f"强制终止 VLC 进程失败: {e2}")
        self.processes = []
        self.playback_status = {}


# 开机自启管理模块
class StartupManager:
    def __init__(self):
        self.startup_folder = winshell.startup()
        self.shortcut_name = "MultiScreenVideoPlayer.lnk"

    def enable_startup(self):
        """启用开机自启"""
        try:
            script_path = os.path.abspath(sys.argv[0])
            shortcut_path = os.path.join(self.startup_folder, self.shortcut_name)

            with winshell.shortcut(shortcut_path) as shortcut:
                shortcut.path = script_path
                shortcut.description = "多屏视频播放器开机自启"
                shortcut.working_directory = os.path.dirname(script_path)
            return True
        except Exception as e:
            logging.error(f"启用开机自启失败: {e}")
            return False

    def disable_startup(self):
        """禁用开机自启"""
        try:
            shortcut_path = os.path.join(self.startup_folder, self.shortcut_name)
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
                return True
            return False
        except Exception as e:
            logging.error(f"禁用开机自启失败: {e}")
            return False

    def is_startup_enabled(self):
        """检查是否已启用开机自启"""
        shortcut_path = os.path.join(self.startup_folder, self.shortcut_name)
        return os.path.exists(shortcut_path)


# 主应用程序模块
class VideoPlayerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.vlc = VLCController()
        self.startup_manager = StartupManager()
        self.video_files = []
        self.is_loop_play = False
        self.init_ui()
        self.current_monitor_index = 0
        self.load_settings()
        self.setup_button_animations()

    def init_ui(self):
        self.setWindowTitle("多屏视频播放系统")
        self.setWindowIcon(QIcon("app_icon.png"))
        self.setFixedSize(600, 950)

        # 样式设置
        self.setStyleSheet("""
            QWidget {
                background-color: #2c3e50;
                color: #ecf0f1;
            }
            QPushButton {
                background-color: #3498db;
                border: 2px solid #2980b9;
                border-radius: 5px;
                padding: 10px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1c6ca7;
            }
            QLabel {
                font-size: 14px;
                padding: 5px;
            }
        """)

        # 布局设置
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 状态显示
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        # 控制按钮
        controls = [
            ("选择视频文件", self.select_video),
            ("立即播放", self.start_playback),
            ("停止播放", self.stop_playback),
            ("显示器检测", self.show_display_info),
            ("开启开机自启", self.enable_startup),
            ("关闭开机自启", self.disable_startup),
            ("更换视频", self.show_change_video_buttons),
            ("检测屏幕位置分辨率", self.detect_screen_info),
            ("保存设置", self.save_settings),
            ("选择视频文件路径", self.select_video_path),
            ("切换播放模式", self.toggle_play_mode)
        ]

        for text, handler in controls:
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            main_layout.addWidget(btn)

        # 显示当前播放模式的标签
        self.mode_label = QLabel(self.get_mode_text())
        self.mode_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.mode_label)

        self.setLayout(main_layout)

    def setup_button_animations(self):
        # 按钮点击动画
        for button in self.findChildren(QPushButton):
            button.clicked.connect(lambda _, btn=button: self.button_click_animation(btn))

    def button_click_animation(self, button):
        # 按钮点击动画，改变按钮大小
        animation = QPropertyAnimation(button, b'size')
        animation.setDuration(100)
        animation.setStartValue(button.size())
        animation.setEndValue(button.size() * 0.9)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.finished.connect(lambda: self.restore_button_size(button))
        animation.start()

    def restore_button_size(self, button):
        animation = QPropertyAnimation(button, b'size')
        animation.setDuration(100)
        animation.setStartValue(button.size())
        animation.setEndValue(button.size() / 0.9)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.start()

    def select_video(self):
        """选择视频文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.wmv);;所有文件 (*.*)"
        )
        if files:
            self.video_files = files
            self.status_label.setText(f"已选择 {len(files)} 个视频文件")
            self.save_settings()

    def start_playback(self):
        """开始播放"""
        if not self.video_files:
            QMessageBox.warning(self, "警告", "请先选择视频文件")
            return
        try:
            monitors = DisplayInfo.get_monitors()
            if len(self.video_files) < len(monitors):
                QMessageBox.warning(self, "警告",
                                    f"视频文件数量 ({len(self.video_files)}) 少于显示器数量 ({len(monitors)})")
                return
            self.vlc.stop_all()
            self.current_monitor_index = 0
            self.monitors = monitors
            self.start_next_playback()
            self.status_label.setText(f"正在 {len(monitors)} 个屏幕上播放")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"播放失败: {str(e)}")
            self.status_label.setText("播放出错")

    def start_next_playback(self):
        if self.current_monitor_index < len(self.monitors):
            monitor = self.monitors[self.current_monitor_index]
            video_path = self.video_files[self.current_monitor_index]
            if not self.vlc.start_vlc_instance(video_path, monitor):
                QMessageBox.critical(self, "错误", f"屏幕 {self.current_monitor_index + 1} 播放失败")
            self.current_monitor_index += 1
            QTimer.singleShot(1000, self.start_next_playback)
        elif self.is_loop_play:
            self.current_monitor_index = 0
            self.vlc.stop_all()
            QTimer.singleShot(1000, self.start_next_playback)

    def stop_playback(self):
        """停止播放"""
        self.vlc.stop_all()
        self.status_label.setText("播放已停止")

    def show_display_info(self):
        """显示显示器信息"""
        info = DisplayInfo.get_monitor_info_text()
        QMessageBox.information(self, "显示器信息", info)

    def enable_startup(self):
        """启用开机自启"""
        if self.startup_manager.enable_startup():
            QMessageBox.information(self, "提示", "开机自启已启用")
        else:
            QMessageBox.critical(self, "错误", "启用开机自启失败")

    def disable_startup(self):
        """禁用开机自启"""
        if self.startup_manager.disable_startup():
            QMessageBox.information(self, "提示", "开机自启已禁用")
        else:
            QMessageBox.critical(self, "错误", "禁用开机自启失败")

    def show_change_video_buttons(self):
        monitor_info = DisplayInfo.get_monitors()
        num_monitors = len(monitor_info)
        file_paths, _ = QFileDialog.getOpenFileNames(self, '选择视频文件', '', '视频文件 (*.mp4 *.avi *.mov)')
        if file_paths:
            new_video_files = list(file_paths)
            if len(new_video_files) > num_monitors:
                QMessageBox.warning(self, "警告", f"你选择的视频文件数量（{len(new_video_files)} 个）超过了显示器数量（{num_monitors} 个），仅前 {num_monitors} 个视频会被使用。")
                new_video_files = new_video_files[:num_monitors]
            elif len(new_video_files) < num_monitors:
                QMessageBox.warning(self, "警告", f"你选择的视频文件数量（{len(new_video_files)} 个）少于显示器数量（{num_monitors} 个），部分显示器将没有对应的视频。")
                for _ in range(num_monitors - len(new_video_files)):
                    new_video_files.append("")
            self.video_files = new_video_files
            QMessageBox.information(self, "提示", f"已为 {len(self.video_files)} 个屏幕分配视频文件")
            self.save_settings()

    def detect_screen_info(self):
        monitor_info = DisplayInfo.get_monitors()
        info_text = ""
        for i, monitor in enumerate(monitor_info):
            monitor_rect = monitor["position"]
            width = monitor_rect[2] - monitor_rect[0]
            height = monitor_rect[3] - monitor_rect[1]
            left = monitor_rect[0]
            top = monitor_rect[1]
            info_text += f"屏幕 {i + 1}：\n"
            info_text += f"  位置：左 {left}，上 {top}\n"
            info_text += f"  分辨率：{width} x {height}\n"
        QMessageBox.information(self, "屏幕信息", info_text)

    def save_settings(self):
        try:
            settings = {
                "video_files": self.video_files,
                "is_loop_play": self.is_loop_play
            }
            with open('settings.json', 'w') as f:
                json.dump(settings, f)
            QMessageBox.information(self, "提示", "设置已保存。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置时出现错误: {str(e)}")

    def load_settings(self):
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
                self.video_files = settings.get("video_files", [])
                self.is_loop_play = settings.get("is_loop_play", False)
                self.update_mode_label()
        except FileNotFoundError:
            self.video_files = []
            self.is_loop_play = False
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "错误", f"解析设置文件时出现错误: {str(e)}")
            self.video_files = []
            self.is_loop_play = False
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载设置时出现错误: {str(e)}")
            self.video_files = []
            self.is_loop_play = False

    def select_video_path(self):
        file_path, _ = QFileDialog.getOpenFileName(self, '选择视频文件', '', '视频文件 (*.mp4 *.avi *.mov)')
        if file_path:
            if os.path.exists(file_path):
                self.video_files = [file_path]
                QMessageBox.information(self, "提示", f"已选择视频文件: {file_path}")
                self.save_settings()
            else:
                QMessageBox.critical(self, "错误", f"选择的文件 {file_path} 不存在。")

    def toggle_play_mode(self):
        """切换播放模式"""
        self.is_loop_play = not self.is_loop_play
        self.update_mode_label()
        self.save_settings()

    def get_mode_text(self):
        return f"当前播放模式: {'循环播放' if self.is_loop_play else '普通播放'}"

    def update_mode_label(self):
        self.mode_label.setText(self.get_mode_text())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoPlayerApp()
    window.show()
    sys.exit(app.exec_())