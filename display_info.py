import win32api
import win32con
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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