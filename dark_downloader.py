#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
黑色主题的 YouTube 下载器命令行版本
使用 yt-dlp 库下载视频，支持代理设置和进度显示
"""

import os
import sys
import time
import argparse
import subprocess
import re
from datetime import datetime

# 检查 yt-dlp 是否已安装
try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False

# 检查 ffmpeg 是否已安装
def check_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

FFMPEG_AVAILABLE = check_ffmpeg()

# ANSI 颜色代码
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# 终端尺寸
def get_terminal_size():
    try:
        columns, rows = os.get_terminal_size()
        return columns
    except:
        return 80

# 进度条
def progress_bar(percent, width=None):
    if width is None:
        width = get_terminal_size() - 30
    
    filled = int(width * percent / 100)
    bar = f"{Colors.BLUE}{'█' * filled}{Colors.ENDC}{'░' * (width - filled)}"
    return f"{Colors.BOLD}[{bar}] {Colors.GREEN}{percent:.1f}%{Colors.ENDC}"

# 安装 yt-dlp
def install_ytdlp():
    print(f"{Colors.YELLOW}正在安装 yt-dlp...{Colors.ENDC}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"])
        print(f"{Colors.GREEN}yt-dlp 安装成功！{Colors.ENDC}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}安装失败: {e}{Colors.ENDC}")
        return False

# 安装 ffmpeg
def install_ffmpeg():
    import platform
    system = platform.system()
    
    print(f"{Colors.YELLOW}正在安装 ffmpeg...{Colors.ENDC}")
    
    try:
        if system == "Darwin":  # macOS
            # 检查 Homebrew 是否已安装
            try:
                subprocess.run(["which", "brew"], check=True, stdout=subprocess.PIPE)
                # 安装 ffmpeg
                subprocess.check_call(["brew", "install", "ffmpeg"])
                print(f"{Colors.GREEN}ffmpeg 安装成功！{Colors.ENDC}")
                return True
            except subprocess.CalledProcessError:
                print(f"{Colors.RED}请先安装 Homebrew (https://brew.sh/)，然后再尝试安装 ffmpeg{Colors.ENDC}")
                return False
                
        elif system == "Windows":
            print(f"{Colors.YELLOW}Windows 系统请手动安装 ffmpeg:{Colors.ENDC}")
            print("1. 访问 https://ffmpeg.org/download.html")
            print("2. 下载 Windows 版本")
            print("3. 解压并将 bin 目录添加到系统 PATH 环境变量")
            return False
            
        elif system == "Linux":
            # 尝试使用系统包管理器
            if subprocess.run(["which", "apt"], stdout=subprocess.PIPE).returncode == 0:
                subprocess.check_call(["sudo", "apt", "update"])
                subprocess.check_call(["sudo", "apt", "install", "-y", "ffmpeg"])
            elif subprocess.run(["which", "yum"], stdout=subprocess.PIPE).returncode == 0:
                subprocess.check_call(["sudo", "yum", "install", "-y", "ffmpeg"])
            elif subprocess.run(["which", "pacman"], stdout=subprocess.PIPE).returncode == 0:
                subprocess.check_call(["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"])
            else:
                print(f"{Colors.RED}无法检测到支持的包管理器，请手动安装 ffmpeg{Colors.ENDC}")
                return False
                
            print(f"{Colors.GREEN}ffmpeg 安装成功！{Colors.ENDC}")
            return True
            
        else:
            print(f"{Colors.RED}不支持的操作系统: {system}{Colors.ENDC}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}安装 ffmpeg 时出错: {str(e)}{Colors.ENDC}")
        return False

# 进度回调
def progress_hook(d):
    if d['status'] == 'downloading':
        downloaded = d.get('downloaded_bytes', 0)
        total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
        
        if total > 0:
            percent = downloaded / total * 100
            speed = d.get('speed', 0)
            
            if speed:
                speed_str = f"{speed / 1024 / 1024:.2f} MB/s"
            else:
                speed_str = "计算中..."
                
            eta = d.get('eta', 0)
            eta_str = str(datetime.timedelta(seconds=eta)) if eta else "计算中..."
            
            # 清除当前行并显示进度
            sys.stdout.write('\r' + ' ' * get_terminal_size())
            sys.stdout.write('\r')
            
            # 显示文件名
            filename = os.path.basename(d.get('filename', ''))
            if len(filename) > 30:
                filename = filename[:27] + "..."
                
            # 显示进度条
            sys.stdout.write(f"{Colors.CYAN}{filename}{Colors.ENDC} {progress_bar(percent)} ")
            sys.stdout.write(f"{Colors.BOLD}{speed_str}{Colors.ENDC} ETA: {Colors.YELLOW}{eta_str}{Colors.ENDC}")
            sys.stdout.flush()
    
    elif d['status'] == 'finished':
        sys.stdout.write('\n')
        print(f"{Colors.GREEN}下载完成！正在处理文件...{Colors.ENDC}")

# 列出可用格式
def list_formats(url, proxy=None):
    if not YTDLP_AVAILABLE:
        print(f"{Colors.RED}请先安装 yt-dlp{Colors.ENDC}")
        return False
    
    ydl_opts = {
        'listformats': True,
        'quiet': False,
        'no_warnings': True
    }
    
    if proxy:
        ydl_opts['proxy'] = proxy
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"{Colors.CYAN}正在获取视频格式信息...{Colors.ENDC}")
            ydl.extract_info(url, download=False)
        return True
    except Exception as e:
        print(f"{Colors.RED}获取视频格式失败: {str(e)}{Colors.ENDC}")
        return False

# 下载视频
def download_video(url, resolution=None, output_path=None, proxy=None):
    if not YTDLP_AVAILABLE:
        print(f"{Colors.RED}请先安装 yt-dlp{Colors.ENDC}")
        return False
    
    if not output_path:
        output_path = os.path.expanduser("~/Downloads")
    
    if not os.path.exists(output_path):
        try:
            os.makedirs(output_path)
        except Exception as e:
            print(f"{Colors.RED}创建下载目录失败: {str(e)}{Colors.ENDC}")
            return False
    
    # 设置格式
    format_spec = 'bestvideo[height<=1080]+bestaudio/best'
    if resolution and resolution.isdigit():
        height = int(resolution)
        format_spec = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'
    
    # 如果 ffmpeg 不可用，使用单一格式
    if not FFMPEG_AVAILABLE:
        if resolution and resolution.isdigit():
            format_spec = f'best[height<={resolution}]/best'
        else:
            format_spec = 'best'
        print(f"{Colors.YELLOW}警告: 未安装 ffmpeg，将下载单一格式视频。质量可能不是最佳。{Colors.ENDC}")
    
    # 设置输出模板
    output_template = os.path.join(output_path, '%(title)s.%(ext)s')
    
    # 设置 yt-dlp 选项 - 优化下载速度
    ydl_opts = {
        'format': format_spec,
        'outtmpl': output_template,
        'progress_hooks': [progress_hook],
        'no_check_certificate': True,
        'quiet': False,
        'no_warnings': True,
        'color': 'always',
        # 优化下载速度的参数
        'concurrent_fragments': 5,  # 并发下载片段数，提高到5个
        'retries': 10,              # 重试次数增加到10次
        'fragment_retries': 10,     # 片段重试次数
        'buffersize': 1024*1024*16, # 增加缓冲区到16MB
        'http_chunk_size': 10485760, # 10MB的块大小，提高吞吐量
        'socket_timeout': 30,       # 增加超时时间
        'extractor_retries': 5,     # 提取器重试次数
        'file_access_retries': 5,   # 文件访问重试
        'postprocessor_args': {     # FFmpeg后处理参数
            'ffmpeg': ['-threads', '4']  # 使用4个线程进行处理
        },
    }
    
    if proxy:
        ydl_opts['proxy'] = proxy
    
    try:
        print(f"{Colors.CYAN}正在下载视频: {url}{Colors.ENDC}")
        print(f"{Colors.CYAN}目标分辨率: {resolution if resolution else '最佳'}{Colors.ENDC}")
        print(f"{Colors.CYAN}保存路径: {output_path}{Colors.ENDC}")
        if proxy:
            print(f"{Colors.CYAN}使用代理: {proxy}{Colors.ENDC}")
        
        print(f"{Colors.YELLOW}已启用多线程下载优化 (并发片段: 5){Colors.ENDC}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        print(f"{Colors.GREEN}下载完成！{Colors.ENDC}")
        return True
    except Exception as e:
        print(f"{Colors.RED}下载失败: {str(e)}{Colors.ENDC}")
        return False

# 主函数
def main():
    global YTDLP_AVAILABLE
    
    # 显示标题
    title = "黑色主题 YouTube 下载器"
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * (len(title) + 4)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}= {title} ={Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * (len(title) + 4)}{Colors.ENDC}\n")
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="带进度条的 YouTube 下载器")
    parser.add_argument("url", nargs="?", help="YouTube视频URL")
    parser.add_argument("-r", "--resolution", help="视频分辨率，例如 360, 720 (默认 720)")
    parser.add_argument("-o", "--output", help="下载保存路径 (默认 ~/Downloads)")
    parser.add_argument("-p", "--proxy", help="代理服务器，例如 http://127.0.0.1:7897")
    parser.add_argument("-l", "--list-formats", action="store_true", help="列出可用格式而不下载")
    parser.add_argument("-i", "--install", action="store_true", help="安装 yt-dlp")
    parser.add_argument("-f", "--install-ffmpeg", action="store_true", help="安装 ffmpeg")
    
    args = parser.parse_args()
    
    # 安装 yt-dlp
    if args.install:
        install_ytdlp()
        return
    
    # 安装 ffmpeg
    if args.install_ffmpeg:
        install_ffmpeg()
        return
    
    # 检查 yt-dlp 是否已安装
    if not YTDLP_AVAILABLE:
        print(f"{Colors.RED}未安装 yt-dlp 库。正在尝试安装...{Colors.ENDC}")
        if not install_ytdlp():
            print(f"{Colors.RED}请手动安装 yt-dlp: pip install yt-dlp{Colors.ENDC}")
            return
        
        # 重新导入 yt-dlp
        try:
            import yt_dlp
            YTDLP_AVAILABLE = True
        except ImportError:
            print(f"{Colors.RED}安装 yt-dlp 失败，请手动安装{Colors.ENDC}")
            return
    
    # 检查是否提供了URL
    if not args.url:
        parser.print_help()
        return
    
    # 设置默认分辨率
    resolution = args.resolution if args.resolution else "720"
    
    # 设置默认输出路径
    output_path = args.output if args.output else os.path.expanduser("~/Downloads")
    
    # 设置代理
    proxy = args.proxy
    
    # 如果未设置代理，尝试使用 Clash Verge 默认代理
    if not proxy:
        print(f"{Colors.YELLOW}未指定代理，尝试使用 Clash Verge 默认代理 (http://127.0.0.1:7897){Colors.ENDC}")
        proxy = "http://127.0.0.1:7897"
    
    # 列出可用格式或下载视频
    if args.list_formats:
        list_formats(args.url, proxy)
    else:
        download_video(args.url, resolution, output_path, proxy)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}下载已取消{Colors.ENDC}")
        sys.exit(0) 