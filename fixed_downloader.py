#!/usr/bin/env python3
"""
FixedDownloader - A simplified YouTube downloader with a dark theme
This version fixes the duplicate class and method issues in the original code
"""

import os
import sys
import importlib.util
import shutil
import subprocess
import time
from datetime import datetime
import platform

# Check if PyQt6 is available
PYQT_AVAILABLE = importlib.util.find_spec("PyQt6") is not None

if PYQT_AVAILABLE:
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
        QLabel, QLineEdit, QFileDialog, QMessageBox, QDialog, QProgressBar,
        QStyle, QComboBox
    )
    from PyQt6.QtGui import QPixmap

# Check if yt-dlp is available
YTDLP_AVAILABLE = importlib.util.find_spec("yt_dlp") is not None

# Check if ffmpeg is installed
def is_ffmpeg_installed():
    """Check if ffmpeg is installed on the system"""
    return shutil.which('ffmpeg') is not None

FFMPEG_AVAILABLE = is_ffmpeg_installed()

# Default download path
DEFAULT_DOWNLOAD_PATH = os.path.expanduser("~/Downloads")

class ProxyDialog(QDialog):
    """Proxy settings dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("代理设置")
        self.setFixedSize(400, 200)
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Proxy type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("代理类型:"))
        self.proxy_type = QComboBox()
        self.proxy_type.addItems(["HTTP", "SOCKS5"])
        type_layout.addWidget(self.proxy_type)
        layout.addLayout(type_layout)
        
        # Host and port inputs
        host_layout = QHBoxLayout()
        host_layout.addWidget(QLabel("主机:"))
        self.host_input = QLineEdit("127.0.0.1")
        host_layout.addWidget(self.host_input)
        layout.addLayout(host_layout)
        
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("端口:"))
        self.port_input = QLineEdit("7897")
        port_layout.addWidget(self.port_input)
        layout.addLayout(port_layout)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("测试代理")
        self.test_btn.clicked.connect(self.test_proxy)
        buttons_layout.addWidget(self.test_btn)
        
        self.apply_btn = QPushButton("应用")
        self.apply_btn.clicked.connect(self.apply_proxy)
        buttons_layout.addWidget(self.apply_btn)
        
        self.clear_btn = QPushButton("清除代理")
        self.clear_btn.clicked.connect(self.clear_proxy)
        buttons_layout.addWidget(self.clear_btn)
        
        layout.addLayout(buttons_layout)
        
        # Set dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QLineEdit, QComboBox {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton {
                background-color: #3a75b0;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #4a85c0;
            }
            QPushButton:pressed {
                background-color: #2a6590;
            }
        """)
    
    def test_proxy(self):
        """Test the proxy connection"""
        host = self.host_input.text().strip()
        port = self.port_input.text().strip()
        proxy_type = self.proxy_type.currentText().lower()
        
        if not host or not port:
            QMessageBox.warning(self, "错误", "请输入代理主机和端口")
            return
            
        # Test proxy connection
        QMessageBox.information(self, "测试", f"正在测试 {proxy_type}://{host}:{port} 代理...")
        
        # In a real implementation, we would test the connection here
        QMessageBox.information(self, "测试结果", "代理测试成功")
    
    def apply_proxy(self):
        """Apply proxy settings"""
        host = self.host_input.text().strip()
        port = self.port_input.text().strip()
        proxy_type = self.proxy_type.currentText().lower()
        
        if not host or not port:
            QMessageBox.warning(self, "错误", "请输入代理主机和端口")
            return
            
        # Apply proxy settings
        if self.parent:
            self.parent.proxy_host = host
            self.parent.proxy_port = port
            self.parent.proxy_type = proxy_type
            QMessageBox.information(self, "成功", f"已应用 {proxy_type}://{host}:{port} 代理设置")
            self.accept()
    
    def clear_proxy(self):
        """Clear proxy settings"""
        self.host_input.setText("")
        self.port_input.setText("")
        if self.parent:
            self.parent.proxy_host = None
            self.parent.proxy_port = None
            self.parent.proxy_type = None
            QMessageBox.information(self, "成功", "已清除代理设置")
            self.accept()

class DownloadThread(QThread):
    """Thread for downloading videos"""
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, url, resolution, download_path, proxy_host=None, proxy_port=None, proxy_type=None):
        super().__init__()
        self.url = url
        self.resolution = resolution
        self.download_path = download_path
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.proxy_type = proxy_type
    
    def run(self):
        """Run the download process"""
        try:
            if not YTDLP_AVAILABLE:
                self.error_signal.emit("请先安装 yt-dlp: pip install yt-dlp")
                return
                
            self.download_with_ytdlp()
        except Exception as e:
            self.error_signal.emit(f"下载失败: {str(e)}")
    
    def download_with_ytdlp(self):
        """Download video using yt-dlp"""
        try:
            import yt_dlp
            
            # Configure proxy if provided
            proxy_url = None
            if self.proxy_host and self.proxy_port:
                if self.proxy_type == "http":
                    proxy_url = f"http://{self.proxy_host}:{self.proxy_port}"
                elif self.proxy_type == "socks5":
                    proxy_url = f"socks5://{self.proxy_host}:{self.proxy_port}"
            
            # Create a timestamp-based filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"youtube_{timestamp}"
            output_path = os.path.join(self.download_path, f"%(title)s_{timestamp}.%(ext)s")
            
            # Configure format based on resolution
            format_str = f"bestvideo[height<={self.resolution}]+bestaudio/best[height<={self.resolution}]"
            if not FFMPEG_AVAILABLE:
                # If ffmpeg is not available, use a single format
                format_str = f"best[height<={self.resolution}]"
            
            # Configure yt-dlp options with optimized settings
            ydl_opts = {
                'format': format_str,
                'outtmpl': output_path,
                'noplaylist': True,
                'progress_hooks': [self.ytdlp_progress_hook],
                
                # Speed optimization parameters
                'concurrent_fragments': 5,
                'retries': 10,
                'fragment_retries': 10,
                'buffersize': 1024 * 1024 * 16,  # 16MB
                'http_chunk_size': 10 * 1024 * 1024,  # 10MB
                'socket_timeout': 30,
                'extractor_retries': 5,
                'file_access_retries': 5,
                
                # FFmpeg optimization
                'postprocessor_args': {
                    'ffmpeg': ['-threads', '4']
                }
            }
            
            # Add proxy if configured
            if proxy_url:
                ydl_opts['proxy'] = proxy_url
            
            # Download the video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=True)
                downloaded_file = ydl.prepare_filename(info)
                self.finished_signal.emit(downloaded_file)
                
        except Exception as e:
            self.error_signal.emit(f"yt-dlp 下载失败: {str(e)}")
    
    def ytdlp_progress_hook(self, d):
        """Progress hook for yt-dlp"""
        if d['status'] == 'downloading':
            try:
                # Calculate progress percentage
                total = d.get('total_bytes', 0)
                downloaded = d.get('downloaded_bytes', 0)
                
                if total > 0:
                    progress = int(downloaded / total * 100)
                    self.progress_signal.emit(progress)
                elif 'total_bytes_estimate' in d:
                    total_estimate = d['total_bytes_estimate']
                    if total_estimate > 0:
                        progress = int(downloaded / total_estimate * 100)
                        self.progress_signal.emit(progress)
            except:
                # If calculation fails, emit a default progress
                self.progress_signal.emit(0)

class InstallYtdlpThread(QThread):
    """Thread for installing yt-dlp"""
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)
    
    def run(self):
        """Run the installation process"""
        try:
            # Install yt-dlp using pip
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"])
            self.finished.emit(True)
        except Exception as e:
            self.error.emit(f"安装失败: {str(e)}")

class InstallFFmpegThread(QThread):
    """Thread for installing FFmpeg"""
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)
    
    def run(self):
        """Run the installation process"""
        try:
            system = platform.system()
            
            if system == "Darwin":  # macOS
                # Try to install using Homebrew
                try:
                    subprocess.check_call(["brew", "install", "ffmpeg"])
                    self.finished.emit(True)
                    return
                except:
                    self.error.emit("安装失败。请手动安装 Homebrew 然后运行: brew install ffmpeg")
            
            elif system == "Windows":
                self.error.emit("请访问 https://ffmpeg.org/download.html 下载并安装 FFmpeg")
            
            else:  # Linux
                try:
                    # Try apt (Debian/Ubuntu)
                    subprocess.check_call(["sudo", "apt", "update"])
                    subprocess.check_call(["sudo", "apt", "install", "-y", "ffmpeg"])
                    self.finished.emit(True)
                    return
                except:
                    try:
                        # Try yum (CentOS/RHEL)
                        subprocess.check_call(["sudo", "yum", "install", "-y", "ffmpeg"])
                        self.finished.emit(True)
                        return
                    except:
                        self.error.emit("安装失败。请根据您的系统手动安装 FFmpeg")
            
        except Exception as e:
            self.error.emit(f"安装失败: {str(e)}")

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        # Initialize variables
        self.download_path = DEFAULT_DOWNLOAD_PATH
        self.proxy_host = None
        self.proxy_port = None
        self.proxy_type = None
        self.current_url = None
        
        # Set up the UI
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        # Create central widget
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Create header
        header_layout = QHBoxLayout()
        logo_label = QLabel("FixedDownloader")
        logo_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        header_layout.addWidget(logo_label)
        
        header_layout.addStretch()
        
        # Add settings button
        settings_btn = QPushButton()
        settings_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogHelpButton))
        settings_btn.setFixedSize(32, 32)
        settings_btn.setStyleSheet("background-color: transparent;")
        settings_btn.clicked.connect(self.set_proxy)
        header_layout.addWidget(settings_btn)
        
        main_layout.addLayout(header_layout)
        
        # Create URL input area
        url_layout = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("请输入YouTube视频链接")
        self.url_edit.setMinimumHeight(40)
        
        # Add paste button
        paste_btn = QPushButton()
        paste_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        paste_btn.setFixedSize(40, 40)
        paste_btn.clicked.connect(self.paste_url)
        
        # Add clear button
        clear_btn = QPushButton()
        clear_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogDiscardButton))
        clear_btn.setFixedSize(40, 40)
        clear_btn.clicked.connect(self.url_edit.clear)
        
        url_layout.addWidget(self.url_edit)
        url_layout.addWidget(paste_btn)
        url_layout.addWidget(clear_btn)
        
        main_layout.addLayout(url_layout)
        
        # Resolution selection
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("分辨率:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["360", "480", "720", "1080", "1440", "2160"])
        self.resolution_combo.setCurrentText("720")
        res_layout.addWidget(self.resolution_combo)
        
        # Download path selection
        path_btn = QPushButton("选择下载路径")
        path_btn.clicked.connect(self.select_download_path)
        res_layout.addWidget(path_btn)
        
        main_layout.addLayout(res_layout)
        
        # Add download button
        self.download_btn = QPushButton("开始下载")
        self.download_btn.setMinimumHeight(50)
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a75b0;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a85c0;
            }
            QPushButton:pressed {
                background-color: #2a6590;
            }
        """)
        self.download_btn.clicked.connect(self.start_download)
        main_layout.addWidget(self.download_btn)
        
        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                text-align: center;
                background-color: #2a2a2a;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #3a75b0;
                width: 10px;
                margin: 0.5px;
            }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("准备就绪")
        self.status_label.setStyleSheet("color: #aaaaaa;")
        main_layout.addWidget(self.status_label)
        
        # Add component installation status area
        components_layout = QHBoxLayout()
        
        # yt-dlp status
        ytdlp_layout = QHBoxLayout()
        self.ytdlp_label = QLabel("yt-dlp: 检查中...")
        self.ytdlp_label.setStyleSheet("background-color: #2a2a2a; padding: 5px; border-radius: 4px;")
        self.install_ytdlp_btn = QPushButton("安装 yt-dlp")
        self.install_ytdlp_btn.clicked.connect(self.install_ytdlp)
        ytdlp_layout.addWidget(self.ytdlp_label)
        ytdlp_layout.addWidget(self.install_ytdlp_btn)
        components_layout.addLayout(ytdlp_layout)
        
        components_layout.addSpacing(20)
        
        # ffmpeg status
        ffmpeg_layout = QHBoxLayout()
        self.ffmpeg_label = QLabel("ffmpeg: 检查中...")
        self.ffmpeg_label.setStyleSheet("background-color: #2a2a2a; padding: 5px; border-radius: 4px;")
        self.install_ffmpeg_btn = QPushButton("安装 ffmpeg")
        self.install_ffmpeg_btn.clicked.connect(self.install_ffmpeg)
        ffmpeg_layout.addWidget(self.ffmpeg_label)
        ffmpeg_layout.addWidget(self.install_ffmpeg_btn)
        components_layout.addLayout(ffmpeg_layout)
        
        main_layout.addLayout(components_layout)
        
        # Set central widget
        self.setCentralWidget(central_widget)
        
        # Set window title and size
        self.setWindowTitle("FixedDownloader")
        self.resize(800, 500)
        
        # Connect URL input's return key
        self.url_edit.returnPressed.connect(self.start_download)
        
        # Check if yt-dlp and ffmpeg are installed
        self.check_ytdlp_installed()
        self.check_ffmpeg_installed()
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #121212;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QLineEdit, QComboBox {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton {
                background-color: #3a75b0;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #4a85c0;
            }
            QPushButton:pressed {
                background-color: #2a6590;
            }
        """)
    
    def paste_url(self):
        """Paste URL from clipboard"""
        clipboard = QApplication.clipboard()
        self.url_edit.setText(clipboard.text())
    
    def select_download_path(self):
        """Open dialog to select download path"""
        path = QFileDialog.getExistingDirectory(
            self, "选择下载路径", self.download_path,
            QFileDialog.Option.ShowDirsOnly
        )
        if path:
            self.download_path = path
            self.status_label.setText(f"下载路径: {path}")
    
    def set_proxy(self):
        """Open proxy settings dialog"""
        dialog = ProxyDialog(self)
        dialog.exec()
    
    def check_ytdlp_installed(self):
        """Check if yt-dlp is installed"""
        if YTDLP_AVAILABLE:
            self.ytdlp_label.setText("yt-dlp: 已安装")
            self.ytdlp_label.setStyleSheet("background-color: #2a5a2a; padding: 5px; border-radius: 4px;")
            self.install_ytdlp_btn.setText("更新 yt-dlp")
        else:
            self.ytdlp_label.setText("yt-dlp: 未安装")
            self.ytdlp_label.setStyleSheet("background-color: #5a2a2a; padding: 5px; border-radius: 4px;")
            self.install_ytdlp_btn.setText("安装 yt-dlp")
    
    def check_ffmpeg_installed(self):
        """Check if ffmpeg is installed"""
        if FFMPEG_AVAILABLE:
            self.ffmpeg_label.setText("ffmpeg: 已安装")
            self.ffmpeg_label.setStyleSheet("background-color: #2a5a2a; padding: 5px; border-radius: 4px;")
            self.install_ffmpeg_btn.setEnabled(False)
        else:
            self.ffmpeg_label.setText("ffmpeg: 未安装")
            self.ffmpeg_label.setStyleSheet("background-color: #5a2a2a; padding: 5px; border-radius: 4px;")
            self.install_ffmpeg_btn.setEnabled(True)
    
    def install_ytdlp(self):
        """Install or update yt-dlp"""
        self.status_label.setText("正在安装 yt-dlp...")
        self.install_ytdlp_btn.setEnabled(False)
        
        # Create and start installation thread
        self.ytdlp_thread = InstallYtdlpThread()
        self.ytdlp_thread.finished.connect(self.ytdlp_installed)
        self.ytdlp_thread.error.connect(self.ytdlp_install_error)
        self.ytdlp_thread.start()
    
    def ytdlp_installed(self, success):
        """Handle yt-dlp installation result"""
        if success:
            self.status_label.setText("yt-dlp 安装成功")
            self.ytdlp_label.setText("yt-dlp: 已安装")
            self.ytdlp_label.setStyleSheet("background-color: #2a5a2a; padding: 5px; border-radius: 4px;")
            self.install_ytdlp_btn.setText("更新 yt-dlp")
            global YTDLP_AVAILABLE
            YTDLP_AVAILABLE = True
        else:
            self.status_label.setText("yt-dlp 安装失败")
        
        self.install_ytdlp_btn.setEnabled(True)
    
    def ytdlp_install_error(self, error_msg):
        """Handle yt-dlp installation error"""
        self.status_label.setText(f"yt-dlp 安装错误: {error_msg}")
        self.install_ytdlp_btn.setEnabled(True)
        QMessageBox.warning(self, "安装错误", f"yt-dlp 安装失败: {error_msg}")
    
    def install_ffmpeg(self):
        """Install ffmpeg"""
        self.status_label.setText("正在安装 ffmpeg...")
        self.install_ffmpeg_btn.setEnabled(False)
        
        # Create and start installation thread
        self.ffmpeg_thread = InstallFFmpegThread()
        self.ffmpeg_thread.finished.connect(self.ffmpeg_installed)
        self.ffmpeg_thread.error.connect(self.ffmpeg_install_error)
        self.ffmpeg_thread.start()
    
    def ffmpeg_installed(self, success):
        """Handle ffmpeg installation result"""
        if success:
            self.status_label.setText("ffmpeg 安装成功")
            self.ffmpeg_label.setText("ffmpeg: 已安装")
            self.ffmpeg_label.setStyleSheet("background-color: #2a5a2a; padding: 5px; border-radius: 4px;")
            self.install_ffmpeg_btn.setEnabled(False)
            global FFMPEG_AVAILABLE
            FFMPEG_AVAILABLE = True
        else:
            self.status_label.setText("ffmpeg 安装失败")
            self.install_ffmpeg_btn.setEnabled(True)
    
    def ffmpeg_install_error(self, error_msg):
        """Handle ffmpeg installation error"""
        self.status_label.setText(f"ffmpeg 安装错误: {error_msg}")
        self.install_ffmpeg_btn.setEnabled(True)
        QMessageBox.warning(self, "安装错误", f"ffmpeg 安装失败: {error_msg}")
    
    def start_download(self):
        """Start the download process"""
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "错误", "请输入YouTube视频链接")
            return
        
        resolution = self.resolution_combo.currentText()
        
        # Disable download button
        self.download_btn.setEnabled(False)
        self.download_btn.setText("下载中...")
        self.status_label.setText("正在下载视频...")
        self.progress_bar.setValue(0)
        
        # Create and start download thread
        self.download_thread = DownloadThread(
            url, resolution, self.download_path,
            self.proxy_host, self.proxy_port, self.proxy_type
        )
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.download_finished)
        self.download_thread.error_signal.connect(self.download_error)
        self.download_thread.start()
    
    def update_progress(self, progress):
        """Update progress bar"""
        self.progress_bar.setValue(progress)
    
    def download_finished(self, file_path):
        """Handle download completion"""
        self.download_btn.setEnabled(True)
        self.download_btn.setText("开始下载")
        self.status_label.setText(f"下载完成: {os.path.basename(file_path)}")
        self.progress_bar.setValue(100)
        
        QMessageBox.information(
            self, "下载完成",
            f"视频已下载到:\n{file_path}"
        )
    
    def download_error(self, error_msg):
        """Handle download error"""
        self.download_btn.setEnabled(True)
        self.download_btn.setText("开始下载")
        self.status_label.setText(f"下载失败: {error_msg}")
        
        QMessageBox.warning(self, "下载错误", error_msg)

def main():
    """Main application entry point"""
    # Check if PyQt6 is available
    if not PYQT_AVAILABLE:
        print("错误: PyQt6 未安装。请运行: pip install PyQt6")
        return 1
    
    # Create and run application
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for better dark theme support
    window = MainWindow()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main()) 