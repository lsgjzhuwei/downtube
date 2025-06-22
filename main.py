import http.client
import importlib.util
import os
import shutil
import socket
import ssl
import sys
import time
import urllib.request
import re
import requests

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton,
                             QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QComboBox, QFileDialog, QMessageBox, QListWidget,
                             QListWidgetItem, QDialog, QRadioButton, QGroupBox,
                             QStyle, QTextEdit, QProgressBar, QCheckBox)
from PyQt6.QtGui import QPixmap
from pytubefix import YouTube, exceptions

# 默认下载路径
DEFAULT_DOWNLOAD_PATH = os.path.expanduser("~/Downloads")

# 配置超时时间（单位：秒）
socket.setdefaulttimeout(15)  # 设置默认Socket超时（减少等待时间）
http.client.HTTPConnection._http_vsn = 10  # 使用HTTP/1.0而非HTTP/1.1
http.client.HTTPConnection._http_vsn_str = 'HTTP/1.0'

# 创建一个默认的SSL上下文
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1  # 仅使用TLS 1.2+

# 尝试不同的SSL配置
try:
    # 设置更宽松的SSL选项
    ssl_context.options &= ~ssl.OP_NO_TLSv1
    ssl_context.options &= ~ssl.OP_NO_TLSv1_1
    # 尝试使用更兼容的密码套件配置
    try:
        # 尝试设置更宽松的密码套件
        ssl_context.set_ciphers('HIGH:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK')
    except ssl.SSLError:
        # 如果失败，不设置特定的密码套件
        pass
except AttributeError:
    # 某些旧版本Python可能不支持这些选项
    pass

# 重写urllib的opener，使用我们的SSL上下文
opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
urllib.request.install_opener(opener)

# 代理支持
USE_PROXY = False
PROXY_URL = None
PROXY_HOST = None
PROXY_PORT = None
PROXY_TYPE = "http"  # "http" 或 "socks5"

# 常用代理端口列表（用于自动探测）
COMMON_PROXY_PORTS = {
    "http": [7897, 1080, 8080, 7890, 10809, 8118, 3128, 8000],
    "socks5": [7897, 1080, 10808, 7891, 1081, 9050]
}

# 检查是否安装了 yt-dlp
YTDLP_AVAILABLE = importlib.util.find_spec("yt_dlp") is not None

# 检查是否安装了 ffmpeg
def is_ffmpeg_installed():
    """检查系统是否安装了 ffmpeg"""
    return shutil.which('ffmpeg') is not None

# 全局变量，存储 ffmpeg 安装状态
FFMPEG_AVAILABLE = is_ffmpeg_installed()

def test_proxy(proxy_url, proxy_type="http", timeout=5):
    """测试代理是否可用"""
    handlers = []
    
    try:
        if proxy_type == "http":
            proxy_handler = urllib.request.ProxyHandler({
                'http': proxy_url,
                'https': proxy_url
            })
            handlers.append(proxy_handler)
        elif proxy_type == "socks5":
            try:
                import socks
                # 解析主机名和端口
                if ":" in proxy_url:
                    host, port = proxy_url.split(":")
                    port = int(port)
                else:
                    host = proxy_url
                    port = 1080  # 默认SOCKS5端口
                    
                # 创建临时socket以进行测试
                old_socket = socket.socket
                socks.set_default_proxy(socks.PROXY_TYPE_SOCKS5, host, port)
                socket.socket = socks.socksocket
            except ImportError:
                return False, "请先安装 PySocks: pip install PySocks"
                
        handlers.append(urllib.request.HTTPSHandler(context=ssl_context))
        test_opener = urllib.request.build_opener(*handlers)
        
        # 使用较短的测试超时时间
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)
        
        try:
            # 尝试访问一个简单的网站
            response = test_opener.open("https://www.google.com", timeout=timeout)
            content = response.read(100)
            # 如果是SOCKS5代理，恢复旧的socket
            if proxy_type == "socks5":
                socket.socket = old_socket
            socket.setdefaulttimeout(old_timeout)
            return True, "代理测试成功"
        except Exception as e:
            # 确保恢复旧的socket
            if proxy_type == "socks5":
                socket.socket = old_socket
            socket.setdefaulttimeout(old_timeout)
            return False, f"代理测试失败: {str(e)}"
            
    except Exception as e:
        # 确保恢复旧的socket
        if proxy_type == "socks5" and 'old_socket' in locals():
            socket.socket = old_socket
        return False, f"代理配置错误: {str(e)}"

def detect_local_proxies(callback=None):
    """探测本地可能的代理"""
    working_proxies = []
    hosts = ["127.0.0.1", "localhost"]
    total_tests = len(hosts) * (len(COMMON_PROXY_PORTS["http"]) + len(COMMON_PROXY_PORTS["socks5"]))
    completed = 0
    
    for host in hosts:
        # 测试HTTP代理
        for port in COMMON_PROXY_PORTS["http"]:
            proxy_url = f"{host}:{port}"
            success, _ = test_proxy(proxy_url, "http", 2)
            if success:
                working_proxies.append({"url": proxy_url, "type": "http"})
            completed += 1
            if callback:
                callback(completed / total_tests, working_proxies)
                
        # 测试SOCKS5代理
        for port in COMMON_PROXY_PORTS["socks5"]:
            try:
                import socks
                proxy_url = f"{host}:{port}"
                success, _ = test_proxy(proxy_url, "socks5", 2)
                if success:
                    working_proxies.append({"url": proxy_url, "type": "socks5"})
            except ImportError:
                pass  # 如果没有安装PySocks库，跳过SOCKS5测试
            completed += 1
            if callback:
                callback(completed / total_tests, working_proxies)
    
    return working_proxies

def set_proxy(host=None, port=None, proxy_type="http"):
    """设置HTTP/HTTPS或SOCKS5代理"""
    global USE_PROXY, PROXY_URL, PROXY_TYPE, PROXY_HOST, PROXY_PORT
    
    if host and port:
        PROXY_HOST = host
        PROXY_PORT = port
        PROXY_TYPE = proxy_type
        PROXY_URL = f"{host}:{port}"
        
        if proxy_type == "http" or proxy_type == "https":
            proxy_handler = urllib.request.ProxyHandler({
                'http': f"{proxy_type}://{host}:{port}",
                'https': f"{proxy_type}://{host}:{port}"
            })
            opener = urllib.request.build_opener(
                proxy_handler,
                urllib.request.HTTPSHandler(context=ssl_context)
            )
        elif proxy_type == "socks5":
            try:
                import socks
                # 设置默认的SOCKS5代理
                socks.set_default_proxy(socks.PROXY_TYPE_SOCKS5, host, port)
                socket.socket = socks.socksocket
                
                # 为urllib建立opener
                opener = urllib.request.build_opener(
                    urllib.request.HTTPSHandler(context=ssl_context)
                )
            except ImportError:
                raise ImportError("使用SOCKS5代理需要安装PySocks库: pip install PySocks")
        else:
            raise ValueError(f"不支持的代理类型: {proxy_type}, 支持的类型有: http, https, socks5")
            
        urllib.request.install_opener(opener)
        USE_PROXY = True
        return True
    else:
        # 如果之前设置了SOCKS5代理，需要恢复默认socket
        if PROXY_TYPE == "socks5" and USE_PROXY:
            try:
                # 恢复默认socket
                socket.socket = socket._socketobject
            except:
                # 如果失败，尝试其他方法恢复
                import socket as socket_module
                socket.socket = socket_module.socket
            
        # 重置为无代理状态
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
        urllib.request.install_opener(opener)
        USE_PROXY = False
        PROXY_URL = None
        PROXY_HOST = None
        PROXY_PORT = None
        return False

def set_clash_verge_proxy():
    """直接设置 Clash Verge 代理"""
    host = "127.0.0.1"
    port = 7897
    proxy_type = "http"  # Clash Verge 同时支持 HTTP 和 SOCKS5，默认使用 HTTP
    
    if set_proxy(host, port, proxy_type):
        return f"{proxy_type}://{host}:{port}", proxy_type
    else:
        return None, None

class ProxyDialog(QDialog):
    """代理设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("代理设置")
        self.resize(450, 300)
        
        # 布局
        layout = QVBoxLayout()
        
        # 代理类型选择
        type_group = QGroupBox("代理类型")
        type_layout = QHBoxLayout()
        
        self.http_radio = QRadioButton("HTTP/HTTPS")
        self.socks_radio = QRadioButton("SOCKS5")
        
        if PROXY_TYPE == "http":
            self.http_radio.setChecked(True)
        else:
            self.socks_radio.setChecked(True)
            
        type_layout.addWidget(self.http_radio)
        type_layout.addWidget(self.socks_radio)
        type_group.setLayout(type_layout)
        
        # 代理地址
        address_layout = QHBoxLayout()
        address_layout.addWidget(QLabel("代理地址:"))
        
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("127.0.0.1:端口号")
        if PROXY_URL:
            self.address_input.setText(PROXY_URL)
        
        address_layout.addWidget(self.address_input)
        
        # 测试按钮
        self.test_btn = QPushButton("测试代理")
        self.test_btn.clicked.connect(self.test_proxy)
        address_layout.addWidget(self.test_btn)
        
        # 自动探测代理
        self.detect_btn = QPushButton("自动探测本地代理")
        self.detect_btn.clicked.connect(self.detect_proxies)
        
        # 代理列表
        self.proxy_list = QListWidget()
        self.proxy_list.itemDoubleClicked.connect(self.select_proxy)
        
        # 进度指示器
        self.progress_label = QLabel("准备就绪")
        self.progress_label.setVisible(False)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.clear_btn = QPushButton("清除代理")
        self.clear_btn.clicked.connect(self.clear_proxy)
        
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        
        # 组装界面
        layout.addWidget(type_group)
        layout.addLayout(address_layout)
        layout.addWidget(self.detect_btn)
        layout.addWidget(self.proxy_list)
        layout.addWidget(self.progress_label)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
    def test_proxy(self):
        """测试当前配置的代理"""
        proxy_url = self.address_input.text().strip()
        if not proxy_url:
            QMessageBox.warning(self, "错误", "请输入代理地址")
            return
            
        proxy_type = "http" if self.http_radio.isChecked() else "socks5"
        
        self.progress_label.setText("正在测试代理...")
        self.progress_label.setVisible(True)
        QApplication.processEvents()
        
        success, message = test_proxy(proxy_url, proxy_type)
        
        self.progress_label.setVisible(False)
        if success:
            QMessageBox.information(self, "测试成功", f"代理 {proxy_url} 工作正常!")
        else:
            QMessageBox.warning(self, "测试失败", message)
    
    def detect_proxies(self):
        """启动代理探测线程"""
        self.proxy_list.clear()
        self.progress_label.setText("正在探测本地代理...")
        self.progress_label.setVisible(True)
        self.detect_btn.setEnabled(False)
        
        # 创建探测线程
        self.detect_thread = ProxyDetectThread()
        self.detect_thread.progress_signal.connect(self.update_detect_progress)
        self.detect_thread.finished_signal.connect(self.detection_finished)
        self.detect_thread.start()
    
    def update_detect_progress(self, progress, proxies):
        """更新探测进度"""
        self.progress_label.setText(f"探测进度: {int(progress * 100)}%")
        
        # 更新列表
        self.proxy_list.clear()
        for proxy in proxies:
            self.proxy_list.addItem(f"{proxy['type']}: {proxy['url']}")
            
    def detection_finished(self, proxies):
        """探测完成"""
        self.progress_label.setVisible(False)
        self.detect_btn.setEnabled(True)
        
        if not proxies:
            QMessageBox.information(self, "探测结果", "未找到可用的本地代理")
    
    def select_proxy(self, item):
        """从列表中选择代理"""
        text = item.text()
        proxy_type, url = text.split(": ")
        
        self.address_input.setText(url)
        if proxy_type == "http":
            self.http_radio.setChecked(True)
        else:
            self.socks_radio.setChecked(True)
    
    def clear_proxy(self):
        """清除代理设置"""
        self.address_input.clear()
        self.http_radio.setChecked(True)
        
    def get_proxy_settings(self):
        """获取用户配置的代理设置"""
        proxy_url = self.address_input.text().strip()
        proxy_type = "http" if self.http_radio.isChecked() else "socks5"
        
        return proxy_url, proxy_type

class ProxyDetectThread(QThread):
    """代理探测线程"""
    progress_signal = pyqtSignal(float, list)  # 进度, 已发现的代理列表
    finished_signal = pyqtSignal(list)  # 所有找到的代理
    
    def run(self):
        detect_local_proxies(lambda progress, proxies: 
                            self.progress_signal.emit(progress, proxies))
        
        # 获取最终结果
        working_proxies = detect_local_proxies()
        self.finished_signal.emit(working_proxies)

class DownloadThread(QThread):
    """下载视频的线程"""
    progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal(int, str)
    error_signal = pyqtSignal(int, str)
    warning_signal = pyqtSignal(str)  # 新增警告信号，用于非致命性错误提示
    
    def __init__(self, idx, video, download_path, proxy_host=None, proxy_port=None, proxy_type=None):
        super().__init__()
        self.idx = idx
        self.video = video
        self.download_path = download_path
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.proxy_type = proxy_type
        self.max_retries = 5  # 最大重试次数
        self.retry_delay = 3  # 重试延迟时间（秒）
        
    def run(self):
        """运行线程"""
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:
                # 根据视频信息中的引擎选择下载方法
                engine = getattr(self.video, 'engine', 'auto')
                
                if engine == 'yt-dlp' or (engine == 'auto' and YTDLP_AVAILABLE):
                    # 使用 yt-dlp 下载
                    self.download_with_ytdlp()
                    return
                else:
                    # 使用 pytubefix 下载
                    self.download_with_pytube()
                    return
                    
            except Exception as e:
                last_error = str(e)
                
                # 检查特定的警告信息
                if "ANDROID_VR client returned: This video is not available" in last_error or "Switching to client: TV" in last_error:
                    # 发送警告信号，但不中断下载
                    self.warning_signal.emit(last_error)
                    # 继续尝试下载
                    retry_count += 1
                    if retry_count < self.max_retries:
                        time.sleep(self.retry_delay)
                        continue
                
                # 检查是否为 SSL 错误
                if "SSL" in last_error or "EOF occurred" in last_error or "连接错误" in last_error:
                    if retry_count < self.max_retries:
                        time.sleep(self.retry_delay)
                        continue
                    
                    # 如果是 SSL 错误且 pytubefix 失败，尝试使用 yt-dlp
                    if YTDLP_AVAILABLE and engine != 'yt-dlp':
                        try:
                            self.download_with_ytdlp()
                            return
                        except Exception as ytdlp_error:
                            last_error = f"pytubefix 失败: {last_error}\n\nyt-dlp 失败: {str(ytdlp_error)}"
                
                # 其他错误或重试次数用尽
                break
        
        # 所有重试都失败了
        error_msg = f"下载失败: {last_error}"
        if "SSL" in str(last_error):
            error_msg += "\n\n这可能是由于 SSL 证书问题或网络连接问题导致的。请检查您的网络连接和代理设置。"
        
        self.error_signal.emit(self.idx, error_msg)
    
    def download_with_pytube(self):
        """使用 pytubefix 下载视频"""
        # 设置代理
        if self.proxy_host and self.proxy_port:
            os.environ['HTTP_PROXY'] = f"{self.proxy_type}://{self.proxy_host}:{self.proxy_port}"
            os.environ['HTTPS_PROXY'] = f"{self.proxy_type}://{self.proxy_host}:{self.proxy_port}"
        
        try:
            # 创建 YouTube 对象
            yt = YouTube(
                self.video.url,
                on_progress_callback=lambda stream, chunk, bytes_remaining: self.update_progress(stream, bytes_remaining)
            )
            
            # 选择要下载的流
            if self.video.resolution == "仅音频":
                # 下载音频
                stream = yt.streams.filter(only_audio=True).first()
                if not stream:
                    raise Exception("无法找到合适的音频流")
                    
                # 下载音频
                file_path = stream.download(output_path=self.download_path)
                
                # 如果有ffmpeg，转换为mp3格式
                if FFMPEG_AVAILABLE:
                    try:
                        import subprocess
                        mp3_path = os.path.splitext(file_path)[0] + ".mp3"
                        subprocess.run(['ffmpeg', '-i', file_path, '-vn', '-ar', '44100', '-ac', '2', '-b:a', '192k', mp3_path], 
                                      check=True, capture_output=True)
                        # 删除原始文件
                        os.remove(file_path)
                        file_path = mp3_path
                    except Exception as e:
                        self.warning_signal.emit(f"转换为MP3格式失败: {str(e)}")
                
                # 发送完成信号
                self.finished_signal.emit(self.idx, file_path)
                return
            else:
                # 尝试找到指定分辨率的流
                stream = yt.streams.filter(resolution=self.video.resolution, progressive=True).first()
                
                # 如果没有找到，尝试自适应流
                if not stream:
                    stream = yt.streams.filter(resolution=self.video.resolution, adaptive=True).first()
                
                # 如果仍然没有找到，使用最高分辨率
                if not stream:
                    stream = yt.streams.get_highest_resolution()
            
            if not stream:
                raise Exception("无法找到合适的视频流")
            
            # 检查是否是自适应流（没有音频）
            has_audio = stream.includes_audio_track
            
            # 下载视频
            file_path = stream.download(output_path=self.download_path)
            
            # 如果视频没有音频，尝试下载并合并音频
            if not has_audio and FFMPEG_AVAILABLE:
                try:
                    # 获取最佳音频流
                    audio_stream = yt.streams.filter(only_audio=True).first()
                    if audio_stream:
                        # 下载音频
                        audio_path = audio_stream.download(output_path=self.download_path, 
                                                          filename=f"audio_{os.path.basename(file_path)}")
                        
                        # 合并视频和音频
                        import subprocess
                        output_path = os.path.join(self.download_path, f"merged_{os.path.basename(file_path)}")
                        subprocess.run(['ffmpeg', '-i', file_path, '-i', audio_path, '-c:v', 'copy', 
                                        '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0', output_path], 
                                      check=True, capture_output=True)
                        
                        # 删除原始文件
                        os.remove(file_path)
                        os.remove(audio_path)
                        
                        # 重命名合并后的文件
                        os.rename(output_path, file_path)
                    else:
                        self.warning_signal.emit("视频可能没有音频，无法找到合适的音频流")
                except Exception as e:
                    self.warning_signal.emit(f"合并音频失败: {str(e)}")
            elif not has_audio and not FFMPEG_AVAILABLE:
                self.warning_signal.emit("视频可能没有音频。未检测到ffmpeg，无法合并音频。")
            
            # 检查视频是否包含音频
            if FFMPEG_AVAILABLE:
                self.check_audio_in_video(file_path)
            
            # 发送完成信号
            self.finished_signal.emit(self.idx, file_path)
            
        except Exception as e:
            error_msg = str(e)
            # 检查特定的警告信息
            if "ANDROID_VR client returned: This video is not available" in error_msg or "Switching to client: TV" in error_msg:
                # 发送警告信号
                self.warning_signal.emit(error_msg)
                # 如果是警告信息，继续尝试下载
                try:
                    # 重试下载，使用不同的客户端
                    yt = YouTube(
                        self.video.url,
                        on_progress_callback=lambda stream, chunk, bytes_remaining: self.update_progress(stream, bytes_remaining),
                        use_oauth=True,
                        allow_oauth_cache=True
                    )
                    
                    # 选择要下载的流
                    if self.video.resolution == "仅音频":
                        stream = yt.streams.filter(only_audio=True).first()
                    else:
                        stream = yt.streams.filter(resolution=self.video.resolution, progressive=True).first() or \
                                yt.streams.filter(resolution=self.video.resolution, adaptive=True).first() or \
                                yt.streams.get_highest_resolution()
                    
                    if stream:
                        file_path = stream.download(output_path=self.download_path)
                        
                        # 检查视频是否包含音频
                        if FFMPEG_AVAILABLE and self.video.resolution != "仅音频":
                            self.check_audio_in_video(file_path)
                            
                        self.finished_signal.emit(self.idx, file_path)
                        return
                except Exception as retry_error:
                    # 如果重试失败，抛出原始错误
                    raise Exception(f"{error_msg}\n\n重试失败: {str(retry_error)}")
            
            # 如果失败，尝试使用yt-dlp下载
            if YTDLP_AVAILABLE:
                self.warning_signal.emit(f"使用pytubefix下载失败: {error_msg}\n尝试使用yt-dlp下载...")
                try:
                    self.download_with_ytdlp()
                    return
                except Exception as ytdlp_error:
                    raise Exception(f"pytubefix 失败: {error_msg}\n\nyt-dlp 失败: {str(ytdlp_error)}")
            
            # 如果不是警告信息或重试失败，抛出原始错误
            raise e
    
    def download_with_ytdlp(self):
        """使用 yt-dlp 下载视频"""
        import yt_dlp
        
        # 设置代理
        proxy_opts = {}
        if self.proxy_host and self.proxy_port:
            proxy_url = f"{self.proxy_type}://{self.proxy_host}:{self.proxy_port}"
            proxy_opts = {'proxy': proxy_url}
        
        # 创建文件名
        safe_title = re.sub(r'[\\/*?:"<>|]', '', self.video.title)
        output_file = os.path.join(self.download_path, f"{safe_title}.mp4")
        
        # 设置格式
        if self.video.resolution == "仅音频":
            format_spec = 'bestaudio/best'
            output_file = os.path.join(self.download_path, f"{safe_title}.mp3")
        elif self.video.resolution == "最高质量":
            # 确保获取最高质量的视频和音频并合并
            format_spec = 'bestvideo+bestaudio/best'
        else:
            # 根据选定的分辨率获取视频和音频
            height = self.video.resolution.replace('p', '')
            format_spec = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'
        
        # 创建 yt-dlp 选项 - 优化下载速度
        ydl_opts = {
            'format': format_spec,
            'outtmpl': output_file,
            'no_check_certificate': True,  # 避免SSL证书问题
            'progress_hooks': [self.ytdlp_progress_hook],
            'quiet': False,
            'no_warnings': False,  # 允许警告，以便捕获
            'logger': self.ytdlp_logger(),  # 自定义日志处理
            'merge_output_format': 'mp4',  # 强制使用mp4作为输出格式
            # 优化下载速度的参数
            'concurrent_fragments': 5,     # 并发下载片段数，提高到5个
            'retries': 10,                 # 重试次数增加到10次
            'fragment_retries': 10,        # 片段重试次数
            'buffersize': 1024*1024*16,    # 增加缓冲区到16MB
            'http_chunk_size': 10485760,   # 10MB的块大小，提高吞吐量
            'socket_timeout': 30,          # 增加超时时间
            'extractor_retries': 5,        # 提取器重试次数
            'file_access_retries': 5,      # 文件访问重试
            'postprocessor_args': {        # FFmpeg后处理参数
                'ffmpeg': ['-threads', '4', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k']  # 使用4个线程进行处理，复制视频流，使用AAC编码音频
            },
            **proxy_opts
        }
        
        # 根据用户选择添加字幕下载选项
        if hasattr(self.video, 'download_subtitles') and self.video.download_subtitles:
            ydl_opts.update({
                'writesubtitles': True,        # 下载字幕
                'writeautomaticsub': True,     # 下载自动生成的字幕
                'subtitleslangs': ['zh-CN', 'zh-TW', 'en'],  # 优先下载中文和英文字幕
                'subtitlesformat': 'srt',      # 使用SRT格式字幕
            })
        
        # 如果 ffmpeg 不可用，使用单一格式
        if not FFMPEG_AVAILABLE and resolution != "仅音频":
            if self.video.resolution == "仅音频":
                ydl_opts['format'] = 'bestaudio/best'
                # 警告用户没有ffmpeg可能导致音频质量降低
                self.warning_signal.emit("未检测到ffmpeg，音频质量可能受到影响。")
            else:
                # 对于视频，使用单一格式（包含音频的格式）
                height = self.video.resolution.replace('p', '')
                ydl_opts['format'] = f'best[height<={height}]/best'
                # 警告用户没有ffmpeg可能导致无法获取最佳质量
                self.warning_signal.emit("未检测到ffmpeg，无法合并单独的视频和音频流。将下载包含音频的单一视频流，质量可能较低。")
        
        try:
            # 下载视频
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.video.url])
            
            # 验证文件是否存在
            if not os.path.exists(output_file):
                # 尝试查找可能的输出文件（yt-dlp有时会修改文件名）
                possible_files = [f for f in os.listdir(self.download_path) if safe_title in f]
                if possible_files:
                    output_file = os.path.join(self.download_path, possible_files[0])
                else:
                    raise Exception("下载完成，但找不到输出文件")
            
            # 如果不是仅音频模式，检查视频是否包含音频
            if self.video.resolution != "仅音频" and FFMPEG_AVAILABLE:
                self.check_audio_in_video(output_file)
            
            # 发送完成信号
            self.finished_signal.emit(self.idx, output_file)
            
        except Exception as e:
            # 如果出现错误，尝试使用更简单的格式重新下载
            error_msg = str(e)
            self.warning_signal.emit(f"下载过程中出现问题: {error_msg}\n尝试使用备用方法下载...")
            
            try:
                # 使用更简单的格式配置
                ydl_opts['format'] = 'best'
                ydl_opts['merge_output_format'] = 'mp4'
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([self.video.url])
                
                # 验证文件是否存在
                if not os.path.exists(output_file):
                    possible_files = [f for f in os.listdir(self.download_path) if safe_title in f]
                    if possible_files:
                        output_file = os.path.join(self.download_path, possible_files[0])
                
                # 发送完成信号
                self.finished_signal.emit(self.idx, output_file)
            except Exception as retry_error:
                # 如果重试失败，抛出原始错误
                raise Exception(f"下载失败: {error_msg}\n\n重试失败: {str(retry_error)}")
    
    def check_audio_in_video(self, file_path):
        """检查视频文件是否包含音频流"""
        if not FFMPEG_AVAILABLE:
            return
            
        try:
            import subprocess
            
            # 使用ffprobe检查视频文件的音频流
            cmd = ['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=codec_type', '-of', 'default=noprint_wrappers=1', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # 如果没有音频流，输出将为空
            if not result.stdout.strip():
                self.warning_signal.emit(f"警告：下载的视频文件 {os.path.basename(file_path)} 不包含音频流。这可能是由于YouTube的限制或下载过程中的问题。")
        except Exception as e:
            # 如果检查过程出错，发出警告但不中断下载
            self.warning_signal.emit(f"无法检查视频是否包含音频: {str(e)}")
    
    def ytdlp_logger(self):
        """创建自定义的yt-dlp日志处理器，用于捕获警告信息"""
        class YtdlpLogger:
            def __init__(self, thread):
                self.thread = thread
                
            def debug(self, msg):
                # 调试信息不处理
                pass
                
            def info(self, msg):
                # 检查信息中是否包含特定警告
                if "ANDROID_VR client returned: This video is not available" in msg or "Switching to client: TV" in msg:
                    self.thread.warning_signal.emit(msg)
                
            def warning(self, msg):
                # 发送所有警告信息
                self.thread.warning_signal.emit(msg)
                
            def error(self, msg):
                # 错误信息不在这里处理，会通过异常机制处理
                pass
                
        return YtdlpLogger(self)
    
    def update_progress(self, stream, bytes_remaining):
        """更新下载进度"""
        file_size = stream.filesize
        bytes_downloaded = file_size - bytes_remaining
        progress = int(bytes_downloaded / file_size * 100)
        self.progress_signal.emit(self.idx, progress)
    
    def ytdlp_progress_hook(self, d):
        """yt-dlp 进度回调"""
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            if total_bytes > 0:
                downloaded_bytes = d.get('downloaded_bytes', 0)
                progress = int(downloaded_bytes / total_bytes * 100)
                self.progress_signal.emit(self.idx, progress)
        elif d['status'] == 'error':
            # 如果有错误信息，检查是否为特定警告
            error_msg = d.get('error', '')
            if "ANDROID_VR client returned: This video is not available" in error_msg or "Switching to client: TV" in error_msg:
                self.warning_signal.emit(error_msg)
    
    def download_finished(self, idx, file_path):
        """下载完成回调"""
        if 0 <= idx < len(self.videos):
            self.videos[idx].status = "已完成"
            self.videos[idx].progress = 100
            
            # 检查是否同时下载了字幕文件
            subtitle_files = []
            base_path = os.path.splitext(file_path)[0]
            for ext in ['.zh-CN.srt', '.zh-TW.srt', '.en.srt', '.srt']:
                if os.path.exists(base_path + ext):
                    subtitle_files.append(os.path.basename(base_path + ext))
            
            # 构建消息
            message = f"视频已下载到:\n{file_path}"
            if subtitle_files:
                message += f"\n\n同时下载了以下字幕文件:\n" + "\n".join(subtitle_files)
            
            QMessageBox.information(self, "下载完成", message)
            
            # 清理线程引用
            if idx in self.download_threads:
                del self.download_threads[idx]
    
    def download_error(self, idx, error_msg):
        """下载错误回调"""
        if 0 <= idx < len(self.videos):
            self.videos[idx].status = "下载失败"
            QMessageBox.warning(self, "下载错误", error_msg)
            
            # 清理线程引用
            if idx in self.download_threads:
                del self.download_threads[idx]

class VideoItem:
    """视频项目类，用于存储视频信息"""
    def __init__(self, title, author, url, resolution, engine="auto"):
        self.title = title
        self.author = author
        self.url = url
        self.resolution = resolution
        self.status = "等待下载"
        self.progress = 0
        self.engine = engine
        self.download_subtitles = True  # 默认下载字幕

class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VideoDownloader")
        self.resize(800, 600)
        
        # 初始化变量
        self.videos = []
        self.download_threads = {}
        self.download_path = DEFAULT_DOWNLOAD_PATH
        self.proxy_host = None
        self.proxy_port = None
        self.proxy_type = "http"
        
        # 设置界面
        self.init_ui()
        
        # 检查 yt-dlp 和 ffmpeg 是否已安装
        self.check_ytdlp_installed()
        self.check_ffmpeg_installed()
        
    def init_ui(self):
        """初始化界面"""
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 视频列表
        self.video_list = QListWidget()
        self.video_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: white;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #3a3a3a;
            }
            QListWidget::item:selected {
                background-color: #3a75b0;
            }
        """)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        # 添加视频按钮
        self.add_btn = QPushButton("添加视频")
        self.add_btn.clicked.connect(self.add_video)
        btn_layout.addWidget(self.add_btn)
        
        # 下载选中视频按钮
        self.download_selected_btn = QPushButton("下载选中")
        self.download_selected_btn.clicked.connect(self.download_selected)
        btn_layout.addWidget(self.download_selected_btn)
        
        # 下载全部视频按钮
        self.download_all_btn = QPushButton("下载全部")
        self.download_all_btn.clicked.connect(self.download_all)
        btn_layout.addWidget(self.download_all_btn)
        
        # 设置下载路径按钮
        self.path_btn = QPushButton("下载路径")
        self.path_btn.clicked.connect(self.set_download_path)
        btn_layout.addWidget(self.path_btn)
        
        # 设置代理按钮
        self.proxy_btn = QPushButton("代理设置")
        self.proxy_btn.clicked.connect(self.set_proxy)
        btn_layout.addWidget(self.proxy_btn)
        
        # 添加按钮区域到主布局
        main_layout.addLayout(btn_layout)
        
        # 添加视频列表到主布局
        main_layout.addWidget(self.video_list)
        
        # 添加 yt-dlp 安装状态和按钮
        ytdlp_layout = QHBoxLayout()
        self.ytdlp_label = QLabel("yt-dlp: 检查中...")
        self.ytdlp_label.setStyleSheet("background-color: #2a2a2a; padding: 5px; border-radius: 4px;")
        
        self.install_ytdlp_btn = QPushButton("安装 yt-dlp")
        self.install_ytdlp_btn.clicked.connect(self.install_ytdlp)
        
        ytdlp_layout.addWidget(self.ytdlp_label)
        ytdlp_layout.addStretch()
        ytdlp_layout.addWidget(self.install_ytdlp_btn)
        
        main_layout.addLayout(ytdlp_layout)
        
        # 添加 ffmpeg 安装状态和按钮
        ffmpeg_layout = QHBoxLayout()
        self.ffmpeg_label = QLabel("ffmpeg: 检查中...")
        self.ffmpeg_label.setStyleSheet("background-color: #2a2a2a; padding: 5px; border-radius: 4px;")
        
        self.install_ffmpeg_btn = QPushButton("安装 ffmpeg")
        self.install_ffmpeg_btn.clicked.connect(self.install_ffmpeg)
        
        ffmpeg_layout.addWidget(self.ffmpeg_label)
        ffmpeg_layout.addStretch()
        ffmpeg_layout.addWidget(self.install_ffmpeg_btn)
        
        main_layout.addLayout(ffmpeg_layout)
        
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QWidget {
                background-color: #121212;
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #3a75b0;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a85c0;
            }
            QPushButton:pressed {
                background-color: #2a6590;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #aaaaaa;
            }
            QLabel {
                color: #e0e0e0;
            }
        """)
        
    def add_video(self):
        """添加视频"""
        # 创建URL输入对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("添加视频")
        dialog.resize(500, 150)
        
        # 设置对话框样式
        dialog.setStyleSheet("""
            QDialog {
                background-color: #121212;
            }
            QLabel {
                color: #e0e0e0;
            }
            QLineEdit {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton {
                background-color: #3a75b0;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #4a85c0;
            }
        """)
        
        # 创建布局
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # URL输入
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("视频URL:"))
        
        url_edit = QLineEdit()
        url_edit.setPlaceholderText("请输入YouTube视频URL")
        url_layout.addWidget(url_edit)
        
        # 粘贴按钮
        paste_btn = QPushButton("粘贴")
        paste_btn.clicked.connect(lambda: url_edit.setText(QApplication.clipboard().text()))
        url_layout.addWidget(paste_btn)
        
        layout.addLayout(url_layout)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        
        self.main_download_btn = QPushButton("获取视频信息")
        self.main_download_btn.clicked.connect(dialog.accept)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.main_download_btn)
        
        layout.addLayout(btn_layout)
        
        # 显示对话框
        if dialog.exec() == QDialog.DialogCode.Accepted:
            url = url_edit.text().strip()
            if not url:
                QMessageBox.warning(self, "错误", "请输入视频URL")
                return
                
            # 显示忙碌对话框
            self.busy_dialog = QMessageBox(self)
            self.busy_dialog.setWindowTitle("请稍候")
            self.busy_dialog.setText("正在获取视频信息...")
            self.busy_dialog.setStandardButtons(QMessageBox.StandardButton.NoButton)
            self.busy_dialog.show()
            
            # 禁用URL输入和下载按钮
            url_edit.setEnabled(False)
            url_edit.setPlaceholderText("正在获取视频信息...")
            self.main_download_btn.setEnabled(False)
            self.main_download_btn.setText("正在获取...")
            
            # 创建获取视频信息的线程
            self.fetch_thread = FetchThread(url)
            self.fetch_thread.finished.connect(self.show_video_info)
            self.fetch_thread.error.connect(self.fetch_error)
            self.fetch_thread.warning.connect(self.show_warning)  # 连接警告信号
            self.fetch_thread.start()
    
    def show_warning(self, warning_msg):
        """显示警告信息"""
        QMessageBox.warning(self, "警告", warning_msg)
    
    def show_video_info(self, video_info):
        """显示视频信息"""
        # 关闭忙碌对话框
        if hasattr(self, 'busy_dialog') and self.busy_dialog:
            self.busy_dialog.close()
            
        # 创建并显示添加视频对话框
        dialog = AddVideoDialog(self)
        
        # 设置视频信息
        dialog.url_edit.setText(video_info['url'])
        dialog.title_label.setText(video_info['title'])
        dialog.duration_label.setText(f"视频时长: {self.format_duration(video_info['duration'])}")
        dialog.platform_label.setText(f"作者: {video_info.get('author', 'Unknown')}")
        
        # 显示缩略图
        if 'thumbnail' in video_info:
            try:
                thumbnail_data = urllib.request.urlopen(video_info['thumbnail']).read()
                pixmap = QPixmap()
                pixmap.loadFromData(thumbnail_data)
                dialog.thumbnail_label.setPixmap(pixmap.scaled(240, 135, Qt.AspectRatioMode.KeepAspectRatio))
            except:
                # 如果缩略图加载失败，显示默认图像
                dialog.thumbnail_label.setText("缩略图加载失败")
        
        # 显示视频信息区域，隐藏获取按钮
        dialog.video_info_widget.setVisible(True)
        dialog.fetch_btn.setVisible(False)
        
        # 存储视频信息以便后续使用
        dialog.video_info = video_info
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 用户点击了确认按钮，添加视频到下载列表
            resolution = dialog.res_combo.currentText()
            engine, download_subtitles = dialog.get_selected_engine()
            
            # 创建VideoItem对象
            video = VideoItem(
                title=video_info['title'],
                author=video_info.get('author', 'Unknown'),
                url=video_info['url'],
                resolution=resolution,
                engine=engine
            )
            
            # 添加字幕下载选项
            video.download_subtitles = download_subtitles
            
            # 添加到视频列表
            self.videos.append(video)
            
            # 更新视频列表显示
            self.video_list.addItem(f"{video.title} ({video.resolution})")
    
    def fetch_error(self, error_msg):
        """获取视频信息错误回调"""
        # 关闭忙碌对话框
        if hasattr(self, 'busy_dialog') and self.busy_dialog:
            self.busy_dialog.close()
            
        QMessageBox.warning(self, "错误", f"获取视频信息失败:\n{error_msg}")
    
    def format_duration(self, seconds):
        """格式化视频时长"""
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{int(hours)}:{int(minutes):02d}:{int(seconds):02d}"
        else:
            return f"{int(minutes):02d}:{int(seconds):02d}"
    
    def download_selected(self):
        """下载选中的视频"""
        selected_items = self.video_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "错误", "请先选择要下载的视频")
            return
            
        for item in selected_items:
            idx = self.video_list.row(item)
            self.start_download(idx)
    
    def download_all(self):
        """下载所有视频"""
        if not self.videos:
            QMessageBox.warning(self, "错误", "请先添加视频")
            return
            
        for idx in range(len(self.videos)):
            if self.videos[idx].status == "等待下载":
                self.start_download(idx)
    
    def start_download(self, idx):
        """开始下载指定索引的视频"""
        if idx < 0 or idx >= len(self.videos):
            return
            
        if self.videos[idx].status != "等待下载" and self.videos[idx].status != "下载失败":
            return
            
        # 更新视频状态
        self.videos[idx].status = "下载中"
        self.videos[idx].progress = 0
        self.update_video_item(idx)
        
        # 创建下载线程
        thread = DownloadThread(
            idx, 
            self.videos[idx], 
            self.download_path,
            self.proxy_host,
            self.proxy_port,
            self.proxy_type
        )
        
        thread.progress_signal.connect(self.update_progress)
        thread.finished_signal.connect(self.download_finished)
        thread.error_signal.connect(self.download_error)
        thread.warning_signal.connect(self.show_warning)
        
        # 保存线程引用
        self.download_threads[idx] = thread
        
        # 启动线程
        thread.start()
    
    def update_progress(self, idx, progress):
        """更新下载进度"""
        if 0 <= idx < len(self.videos):
            self.videos[idx].progress = progress
            self.update_video_item(idx)
    
    def update_video_item(self, idx):
        """更新视频列表项的显示"""
        if 0 <= idx < len(self.videos):
            video = self.videos[idx]
            item = self.video_list.item(idx)
            
            if video.status == "下载中":
                item.setText(f"{video.title} ({video.resolution}) - {video.progress}%")
            else:
                item.setText(f"{video.title} ({video.resolution}) - {video.status}")
    
    def download_finished(self, idx, file_path):
        """下载完成回调"""
        if 0 <= idx < len(self.videos):
            self.videos[idx].status = "已完成"
            self.videos[idx].progress = 100
            self.update_video_item(idx)
            
            # 检查是否同时下载了字幕文件
            subtitle_files = []
            base_path = os.path.splitext(file_path)[0]
            for ext in ['.zh-CN.srt', '.zh-TW.srt', '.en.srt', '.srt']:
                if os.path.exists(base_path + ext):
                    subtitle_files.append(os.path.basename(base_path + ext))
            
            # 构建消息
            message = f"视频已下载到:\n{file_path}"
            if subtitle_files:
                message += f"\n\n同时下载了以下字幕文件:\n" + "\n".join(subtitle_files)
            
            QMessageBox.information(self, "下载完成", message)
            
            # 清理线程引用
            if idx in self.download_threads:
                del self.download_threads[idx]
    
    def download_error(self, idx, error_msg):
        """下载错误回调"""
        if 0 <= idx < len(self.videos):
            self.videos[idx].status = "下载失败"
            self.update_video_item(idx)
            QMessageBox.warning(self, "下载错误", error_msg)
            
            # 清理线程引用
            if idx in self.download_threads:
                del self.download_threads[idx]
    
    def set_download_path(self):
        """设置下载路径"""
        path = QFileDialog.getExistingDirectory(
            self, 
            "选择下载路径", 
            self.download_path,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if path:
            self.download_path = path
            QMessageBox.information(self, "下载路径", f"已设置下载路径为:\n{path}")
    
    def set_proxy(self):
        """打开代理设置对话框"""
        dialog = ProxyDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            proxy_url, proxy_type = dialog.get_proxy_settings()
            
            if proxy_url:
                # 解析代理地址
                if ":" in proxy_url:
                    host, port = proxy_url.split(":")
                    port = int(port)
                    
                    # 设置代理
                    try:
                        set_proxy(host, port, proxy_type)
                        self.proxy_host = host
                        self.proxy_port = port
                        self.proxy_type = proxy_type
                        QMessageBox.information(self, "代理设置", f"已设置代理: {proxy_type}://{host}:{port}")
                    except Exception as e:
                        QMessageBox.warning(self, "代理设置错误", str(e))
                else:
                    QMessageBox.warning(self, "代理格式错误", "代理地址格式应为: 主机名:端口号")
            else:
                # 清除代理设置
                set_proxy()
                self.proxy_host = None
                self.proxy_port = None
                QMessageBox.information(self, "代理设置", "已清除代理设置")
    
    def check_ytdlp_installed(self):
        """检查是否安装了yt-dlp"""
        if YTDLP_AVAILABLE:
            self.ytdlp_label.setText("yt-dlp: 已安装")
            self.ytdlp_label.setStyleSheet("color: green; background-color: #2a2a2a; padding: 5px; border-radius: 4px;")
            self.install_ytdlp_btn.setText("更新 yt-dlp")
        else:
            self.ytdlp_label.setText("yt-dlp: 未安装")
            self.ytdlp_label.setStyleSheet("color: red; background-color: #2a2a2a; padding: 5px; border-radius: 4px;")
            self.install_ytdlp_btn.setText("安装 yt-dlp")

    def install_ytdlp(self):
        """安装或更新 yt-dlp 库"""
        self.install_ytdlp_btn.setEnabled(False)
        self.ytdlp_label.setText("yt-dlp: 正在安装...")
        
        # 创建安装线程
        self.install_ytdlp_thread = InstallYtdlpThread()
        self.install_ytdlp_thread.finished.connect(self.ytdlp_installed)
        self.install_ytdlp_thread.error.connect(self.ytdlp_install_error)
        self.install_ytdlp_thread.start()
        
    def ytdlp_installed(self, success):
        """yt-dlp 安装完成回调"""
        global YTDLP_AVAILABLE
        if success:
            YTDLP_AVAILABLE = True
            self.ytdlp_label.setText("yt-dlp: 已安装 ✓")
            self.ytdlp_label.setStyleSheet("color: green; background-color: #2a2a2a; padding: 5px; border-radius: 4px;")
            self.install_ytdlp_btn.setText("更新 yt-dlp")
            QMessageBox.information(self, "安装成功", "yt-dlp 已成功安装/更新！")
        else:
            self.ytdlp_label.setText("yt-dlp: 安装失败 ✗")
            self.ytdlp_label.setStyleSheet("color: red; background-color: #2a2a2a; padding: 5px; border-radius: 4px;")
        self.install_ytdlp_btn.setEnabled(True)
        
    def ytdlp_install_error(self, error_msg):
        """yt-dlp 安装错误回调"""
        self.ytdlp_label.setText("yt-dlp: 安装失败 ✗")
        self.ytdlp_label.setStyleSheet("color: red; background-color: #2a2a2a; padding: 5px; border-radius: 4px;")
        self.install_ytdlp_btn.setEnabled(True)
        QMessageBox.warning(self, "安装错误", f"安装 yt-dlp 时出错:\n{error_msg}")

    def check_ffmpeg_installed(self):
        """检查 ffmpeg 是否已安装"""
        if FFMPEG_AVAILABLE:
            self.ffmpeg_label.setText("ffmpeg: 已安装 ✓")
            self.ffmpeg_label.setStyleSheet("color: green; background-color: #2a2a2a; padding: 5px; border-radius: 4px;")
            self.install_ffmpeg_btn.setVisible(False)
        else:
            self.ffmpeg_label.setText("ffmpeg: 未安装 ✗")
            self.ffmpeg_label.setStyleSheet("color: red; background-color: #2a2a2a; padding: 5px; border-radius: 4px;")
            self.install_ffmpeg_btn.setVisible(True)
            
    def install_ffmpeg(self):
        """安装或更新 ffmpeg"""
        self.install_ffmpeg_btn.setEnabled(False)
        self.ffmpeg_label.setText("ffmpeg: 正在安装...")
        
        # 创建安装线程
        self.install_ffmpeg_thread = InstallFFmpegThread()
        self.install_ffmpeg_thread.finished.connect(self.ffmpeg_installed)
        self.install_ffmpeg_thread.error.connect(self.ffmpeg_install_error)
        self.install_ffmpeg_thread.start()
        
    def ffmpeg_installed(self, success):
        """ffmpeg 安装完成回调"""
        global FFMPEG_AVAILABLE
        if success:
            FFMPEG_AVAILABLE = True
            self.ffmpeg_label.setText("ffmpeg: 已安装 ✓")
            self.ffmpeg_label.setStyleSheet("color: green; background-color: #2a2a2a; padding: 5px; border-radius: 4px;")
            self.install_ffmpeg_btn.setVisible(False)
            QMessageBox.information(self, "安装成功", "ffmpeg 已成功安装！")
        else:
            self.ffmpeg_label.setText("ffmpeg: 安装失败 ✗")
            self.ffmpeg_label.setStyleSheet("color: red; background-color: #2a2a2a; padding: 5px; border-radius: 4px;")
        self.install_ffmpeg_btn.setEnabled(True)
        
    def ffmpeg_install_error(self, error_msg):
        """ffmpeg 安装错误回调"""
        self.ffmpeg_label.setText("ffmpeg: 安装失败 ✗")
        self.ffmpeg_label.setStyleSheet("color: red; background-color: #2a2a2a; padding: 5px; border-radius: 4px;")
        self.install_ffmpeg_btn.setEnabled(True)
        QMessageBox.warning(self, "安装错误", f"安装 ffmpeg 时出错:\n{error_msg}")

def get_video_info_with_ytdlp(url):
    """使用 yt-dlp 获取视频信息"""
    import yt_dlp
    
    # 设置代理
    proxy_opts = {}
    if USE_PROXY and PROXY_URL:
        proxy_url = f"{PROXY_TYPE}://{PROXY_URL}"
        proxy_opts = {'proxy': proxy_url}
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'no_check_certificate': True,
        **proxy_opts
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
    # 构建视频信息
    video_info = {
        'url': url,
        'title': info.get('title', 'Unknown'),
        'author': info.get('uploader', 'Unknown'),
        'thumbnail': info.get('thumbnail'),
        'duration': info.get('duration', 0),
        'streams': []
    }
    
    # 获取可用的视频流
    formats = info.get('formats', [])
    for f in formats:
        height = f.get('height')
        if height:
            video_info['streams'].append({
                'resolution': f"{height}p",
                'fps': f.get('fps'),
                'ext': f.get('ext'),
                'filesize': f.get('filesize'),
                'format_id': f.get('format_id'),
                'is_progressive': f.get('acodec', 'none') != 'none' and f.get('vcodec', 'none') != 'none'
            })
        elif f.get('acodec', 'none') != 'none' and f.get('vcodec', 'none') == 'none':
            # 音频流
            video_info['streams'].append({
                'resolution': 'audio',
                'abr': f.get('abr'),
                'ext': f.get('ext'),
                'filesize': f.get('filesize'),
                'format_id': f.get('format_id'),
                'is_progressive': False
            })
    
    return video_info

if __name__ == "__main__":
    print("Application starting...")
    app = QApplication(sys.argv)
    print("QApplication created")
    window = MainWindow()
    print("MainWindow created")
    
    # 自动尝试设置 Clash Verge 代理
    try:
        proxy_url, proxy_type = set_clash_verge_proxy()
        window.proxy_host = "127.0.0.1"
        window.proxy_port = 7897
        window.proxy_type = "http"
        print(f"已自动设置 Clash Verge 代理: {proxy_url}")
    except Exception as e:
        print(f"自动设置代理失败: {str(e)}")
    
    print("About to show window")
    window.show()
    print("Window shown, entering event loop")
    sys.exit(app.exec()) 
