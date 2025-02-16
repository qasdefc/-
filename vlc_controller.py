import os
import subprocess
import time
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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