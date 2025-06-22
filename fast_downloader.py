#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
高速 YouTube 下载器
使用 yt-dlp 库下载视频，支持代理设置和进度显示
包含多线程和性能优化
"""

import os
import sys
import time
import argparse
import subprocess
import re
import json
import shutil
from datetime import datetime, timedelta

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

# 高级进度条
def progress_bar(percent, width=None, speed=None, eta=None, size=None, downloaded=None):
    if width is None:
        width = get_terminal_size() - 60  # 为速度和ETA留出空间
    
    filled = int(width * percent / 100)
    bar = f"{Colors.BLUE}{'█' * filled}{Colors.ENDC}{'░' * (width - filled)}"
    
    # 格式化大小
    size_str = ""
    if size and downloaded:
        # 转换为易读的格式 (MB, GB)
        if size > 1024*1024*1024:
            size_str = f"{downloaded/(1024*1024*1024):.2f}/{size/(1024*1024*1024):.2f} GB"
        else:
            size_str = f"{downloaded/(1024*1024):.2f}/{size/(1024*1024):.2f} MB"
    
    # 格式化速度
    speed_str = ""
    if speed:
        if speed > 1024*1024:
            speed_str = f"{speed/(1024*1024):.2f} MB/s"
        else:
            speed_str = f"{speed/1024:.2f} KB/s"
    
    # 格式化ETA
    eta_str = str(eta) if eta else "计算中..."
    
    return f"{Colors.BOLD}[{bar}] {Colors.GREEN}{percent:.1f}%{Colors.ENDC} {size_str} {Colors.BOLD}{speed_str}{Colors.ENDC} ETA: {Colors.YELLOW}{eta_str}{Colors.ENDC}"

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

# 显示格式化的文件大小
def format_size(bytes):
    """将字节数转换为人类可读的格式"""
    if bytes < 1024:
        return f"{bytes} B"
    elif bytes < 1024 * 1024:
        return f"{bytes/1024:.2f} KB"
    elif bytes < 1024 * 1024 * 1024:
        return f"{bytes/(1024*1024):.2f} MB"
    else:
        return f"{bytes/(1024*1024*1024):.2f} GB"

# 记录开始时间和下载大小，用于计算速度
download_start_time = None
last_downloaded_bytes = 0
download_speed_history = []  # 用于计算平均速度

# 高级进度回调
def progress_hook(d):
    global download_start_time, last_downloaded_bytes, download_speed_history
    
    if d['status'] == 'downloading':
        # 初始化开始时间
        if download_start_time is None:
            download_start_time = time.time()
            last_downloaded_bytes = 0
        
        # 获取下载信息
        downloaded = d.get('downloaded_bytes', 0)
        total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
        
        if total > 0:
            percent = downloaded / total * 100
            
            # 计算下载速度 (bytes/second)
            current_time = time.time()
            time_diff = current_time - download_start_time
            if time_diff > 0:
                current_speed = (downloaded - last_downloaded_bytes) / time_diff
                download_speed_history.append(current_speed)
                # 只保留最近10个速度样本
                if len(download_speed_history) > 10:
                    download_speed_history.pop(0)
                # 使用平均速度使显示更平滑
                speed = sum(download_speed_history) / len(download_speed_history)
            else:
                speed = 0
            
            # 估计剩余时间
            if speed > 0:
                remaining_bytes = total - downloaded
                eta_seconds = remaining_bytes / speed
                eta = str(timedelta(seconds=int(eta_seconds)))
            else:
                eta = "计算中..."
            
            # 更新上次下载的字节数和时间
            last_downloaded_bytes = downloaded
            download_start_time = current_time
            
            # 获取文件名
            filename = os.path.basename(d.get('filename', ''))
            if len(filename) > 25:
                filename = filename[:22] + "..."
            
            # 显示进度
            sys.stdout.write('\r' + ' ' * get_terminal_size())  # 清除当前行
            sys.stdout.write('\r')
            
            # 显示更加详细的进度信息
            progress_info = progress_bar(
                percent, 
                speed=speed, 
                eta=eta, 
                size=total, 
                downloaded=downloaded
            )
            
            # 显示当前下载的文件名和片段信息
            fragment_info = ""
            if d.get('fragment_index') and d.get('fragment_count'):
                fragment_info = f"[分片: {d.get('fragment_index')}/{d.get('fragment_count')}]"
            
            sys.stdout.write(f"{Colors.CYAN}{filename}{Colors.ENDC} {fragment_info}\n")
            sys.stdout.write(progress_info)
            sys.stdout.flush()
    
    elif d['status'] == 'finished':
        # 重置下载状态
        download_start_time = None
        last_downloaded_bytes = 0
        download_speed_history = []
        
        sys.stdout.write('\n\n')
        print(f"{Colors.GREEN}下载完成！正在处理文件...{Colors.ENDC}")

# 获取视频信息
def get_video_info(url, proxy=None):
    if not YTDLP_AVAILABLE:
        print(f"{Colors.RED}请先安装 yt-dlp{Colors.ENDC}")
        return None
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True
    }
    
    if proxy:
        ydl_opts['proxy'] = proxy
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"{Colors.CYAN}正在获取视频信息...{Colors.ENDC}")
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        print(f"{Colors.RED}获取视频信息失败: {str(e)}{Colors.ENDC}")
        return None

# 优化的列出可用格式
def list_formats(url, proxy=None):
    if not YTDLP_AVAILABLE:
        print(f"{Colors.RED}请先安装 yt-dlp{Colors.ENDC}")
        return False
    
    # 获取完整的视频信息
    info = get_video_info(url, proxy)
    
    if info:
        # 更漂亮地打印格式列表
        print(f"\n{Colors.BOLD}{Colors.CYAN}视频标题: {info.get('title', '未知')}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.CYAN}上传者: {info.get('uploader', '未知')}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.CYAN}视频长度: {timedelta(seconds=info.get('duration', 0))}{Colors.ENDC}")
        
        # 获取所有格式
        formats = info.get('formats', [])
        
        if formats:
            # 分类格式
            video_formats = []
            audio_formats = []
            combined_formats = []
            
            for fmt in formats:
                format_id = fmt.get('format_id', 'N/A')
                ext = fmt.get('ext', 'N/A')
                resolution = 'audio only' if fmt.get('vcodec') == 'none' else f"{fmt.get('width', 'N/A')}x{fmt.get('height', 'N/A')}"
                filesize = fmt.get('filesize') or fmt.get('filesize_approx')
                filesize_str = format_size(filesize) if filesize else 'N/A'
                note = fmt.get('format_note', '')
                vcodec = fmt.get('vcodec', 'none')
                acodec = fmt.get('acodec', 'none')
                
                format_info = {
                    'id': format_id,
                    'ext': ext,
                    'resolution': resolution,
                    'filesize': filesize_str,
                    'note': note,
                    'vcodec': vcodec,
                    'acodec': acodec
                }
                
                if vcodec == 'none':
                    audio_formats.append(format_info)
                elif acodec == 'none':
                    video_formats.append(format_info)
                else:
                    combined_formats.append(format_info)
            
            # 打印分类的格式列表
            print(f"\n{Colors.BOLD}{Colors.GREEN}== 组合格式（视频+音频） =={Colors.ENDC}")
            print(f"{Colors.BOLD}{'格式ID':<10} {'扩展名':<8} {'分辨率':<15} {'大小':<12} {'备注':<15} {'视频编码':<10} {'音频编码'}{Colors.ENDC}")
            print("-" * get_terminal_size())
            for fmt in combined_formats:
                print(f"{fmt['id']:<10} {fmt['ext']:<8} {fmt['resolution']:<15} {fmt['filesize']:<12} {fmt['note']:<15} {fmt['vcodec']:<10} {fmt['acodec']}")
            
            print(f"\n{Colors.BOLD}{Colors.YELLOW}== 仅视频格式 =={Colors.ENDC}")
            print(f"{Colors.BOLD}{'格式ID':<10} {'扩展名':<8} {'分辨率':<15} {'大小':<12} {'备注':<15} {'视频编码'}{Colors.ENDC}")
            print("-" * get_terminal_size())
            for fmt in video_formats:
                print(f"{fmt['id']:<10} {fmt['ext']:<8} {fmt['resolution']:<15} {fmt['filesize']:<12} {fmt['note']:<15} {fmt['vcodec']}")
            
            print(f"\n{Colors.BOLD}{Colors.BLUE}== 仅音频格式 =={Colors.ENDC}")
            print(f"{Colors.BOLD}{'格式ID':<10} {'扩展名':<8} {'大小':<12} {'备注':<15} {'音频编码'}{Colors.ENDC}")
            print("-" * get_terminal_size())
            for fmt in audio_formats:
                print(f"{fmt['id']:<10} {fmt['ext']:<8} {fmt['filesize']:<12} {fmt['note']:<15} {fmt['acodec']}")
            
            print(f"\n{Colors.BOLD}{Colors.YELLOW}使用格式ID下载: ./fast_downloader.py -f 格式ID \"视频URL\"{Colors.ENDC}")
            print(f"{Colors.BOLD}{Colors.YELLOW}例如: ./fast_downloader.py -f 22 \"{url}\"{Colors.ENDC}\n")
        
        return True
    
    return False

# 高速下载视频
def download_video(url, resolution=None, output_path=None, proxy=None, format_id=None):
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
    
    # 根据是否指定了格式ID来设置格式
    if format_id:
        format_spec = format_id
        print(f"{Colors.CYAN}使用指定格式ID: {format_id}{Colors.ENDC}")
    else:
        # 设置默认格式
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
    
    # 设置 yt-dlp 选项 - 高级性能优化
    ydl_opts = {
        'format': format_spec,
        'outtmpl': output_template,
        'progress_hooks': [progress_hook],
        'no_check_certificate': True,
        'quiet': False,
        'no_warnings': True,
        'color': 'always',
        # 高级下载速度优化
        'concurrent_fragments': 8,      # 提高到8个并发片段
        'retries': 10,                  # 重试次数
        'fragment_retries': 10,         # 片段重试次数
        'buffersize': 1024*1024*32,     # 增加缓冲区到32MB
        'http_chunk_size': 10485760*2,  # 20MB的块大小
        'socket_timeout': 30,           # 超时时间
        'extractor_retries': 5,         # 提取器重试次数
        'file_access_retries': 5,       # 文件访问重试
        # 使用外部下载器加速 (如果可用)
        'external_downloader': 'aria2c' if shutil.which('aria2c') else None,
        'external_downloader_args': {
            'aria2c': ['--min-split-size=1M', '--max-connection-per-server=16', '--max-concurrent-downloads=8']
        },
        # 后处理参数
        'postprocessor_args': {
            'ffmpeg': ['-threads', '4']  # 使用4个线程进行处理
        },
        # 禁用一些不必要的功能以提高速度
        'updatetime': False,            # 不更新文件修改时间
        'ignoreerrors': False,          # 遇到错误时停止
        'geo_bypass': True,             # 尝试绕过地理限制
        'sleep_interval': 0,            # 下载前不等待
    }
    
    if proxy:
        ydl_opts['proxy'] = proxy
    
    try:
        print(f"{Colors.CYAN}正在下载视频: {url}{Colors.ENDC}")
        if not format_id:
            print(f"{Colors.CYAN}目标分辨率: {resolution if resolution else '最佳'}{Colors.ENDC}")
        print(f"{Colors.CYAN}保存路径: {output_path}{Colors.ENDC}")
        if proxy:
            print(f"{Colors.CYAN}使用代理: {proxy}{Colors.ENDC}")
        
        print(f"{Colors.YELLOW}已启用多线程高速下载优化 (并发片段: 8){Colors.ENDC}")
        
        if shutil.which('aria2c'):
            print(f"{Colors.GREEN}已启用 aria2c 外部下载器，可显著提高下载速度{Colors.ENDC}")
        
        # 开始计时
        start_time = time.time()
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # 计算总耗时
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"{Colors.GREEN}下载完成！总耗时: {timedelta(seconds=int(duration))}{Colors.ENDC}")
        return True
    except Exception as e:
        print(f"{Colors.RED}下载失败: {str(e)}{Colors.ENDC}")
        return False

# 主函数
def main():
    global YTDLP_AVAILABLE
    
    # 显示标题
    title = "高速 YouTube 下载器"
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * (len(title) + 4)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}= {title} ={Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * (len(title) + 4)}{Colors.ENDC}\n")
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="高速 YouTube 下载器 - 多线程并发下载")
    parser.add_argument("url", nargs="?", help="YouTube视频URL")
    parser.add_argument("-r", "--resolution", help="视频分辨率，例如 360, 720, 1080 (默认 720)")
    parser.add_argument("-o", "--output", help="下载保存路径 (默认 ~/Downloads)")
    parser.add_argument("-p", "--proxy", help="代理服务器，例如 http://127.0.0.1:7897")
    parser.add_argument("-l", "--list-formats", action="store_true", help="列出可用格式而不下载")
    parser.add_argument("-f", "--format", help="指定yt-dlp格式ID，例如 22 表示720p")
    parser.add_argument("-i", "--install", action="store_true", help="安装 yt-dlp")
    parser.add_argument("-a", "--aria2", action="store_true", help="安装 aria2 下载加速器")
    parser.add_argument("--ffmpeg", action="store_true", help="安装 ffmpeg")
    
    args = parser.parse_args()
    
    # 安装 yt-dlp
    if args.install:
        install_ytdlp()
        return
    
    # 安装 ffmpeg
    if args.ffmpeg:
        install_ffmpeg()
        return
    
    # 安装 aria2
    if args.aria2:
        import platform
        system = platform.system()
        
        print(f"{Colors.YELLOW}正在安装 aria2 下载加速器...{Colors.ENDC}")
        try:
            if system == "Darwin":  # macOS
                subprocess.check_call(["brew", "install", "aria2"])
            elif system == "Linux":
                if subprocess.run(["which", "apt"], stdout=subprocess.PIPE).returncode == 0:
                    subprocess.check_call(["sudo", "apt", "install", "-y", "aria2"])
                elif subprocess.run(["which", "yum"], stdout=subprocess.PIPE).returncode == 0:
                    subprocess.check_call(["sudo", "yum", "install", "-y", "aria2"])
                elif subprocess.run(["which", "pacman"], stdout=subprocess.PIPE).returncode == 0:
                    subprocess.check_call(["sudo", "pacman", "-S", "--noconfirm", "aria2"])
                else:
                    print(f"{Colors.RED}无法检测到支持的包管理器，请手动安装 aria2{Colors.ENDC}")
                    return
            elif system == "Windows":
                print(f"{Colors.YELLOW}Windows 系统请手动安装 aria2:{Colors.ENDC}")
                print("1. 访问 https://github.com/aria2/aria2/releases")
                print("2. 下载对应版本解压，并将路径添加到系统 PATH 环境变量")
                return
                
            print(f"{Colors.GREEN}aria2 安装成功！下载速度将大幅提升{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}安装 aria2 时出错: {str(e)}{Colors.ENDC}")
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
    
    # 根据参数执行操作
    if args.list_formats:
        list_formats(args.url, proxy)
    else:
        download_video(args.url, resolution, output_path, proxy, args.format)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}下载已取消{Colors.ENDC}")
        sys.exit(0) 