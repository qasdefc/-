import os
import winshell
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class StartupManager:
    def __init__(self):
        self.startup_folder = winshell.startup()
        self.shortcut_name = "MultiScreenVideoPlayer.lnk"

    def enable_startup(self):
        """启用开机自启"""
        try:
            import sys
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