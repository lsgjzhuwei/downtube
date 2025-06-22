#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
带进度条的 YouTube 下载器
这个脚本提供了更直观的进度条显示功能
"""

import os
import sys
import argparse
import importlib.util
import time
import shutil

# 检查是否安装了 yt-dlp
YTDLP_AVAILABLE = importlib.util.find_spec("yt_dlp") is not None

# 检查是否安装了 ffmpeg
def is_ffmpeg_installed():
    """检查系统是否安装了 ffmpeg"""
    return shutil.which('ffmpeg') is not None

# 全局变量，存储 ffmpeg 安装状态
FFMPEG_AVAILABLE = is_ffmpeg_installed()

# 获取终端宽度
def get_terminal_width():
    """获取终端宽度"""
    try:
        return shutil.get_terminal_size().columns
    except:
        return 80  # 默认宽度

# 绘制进度条
def draw_progress_bar(percent, width=30):
    """绘制进度条"""
    # 计算已完成的部分
    done = int(width * percent / 100)
    
    # 创建进度条字符串
    bar = '█' * done + '░' * (width - done)
    
    return f"[{bar}] {percent:.1f}%"

def progress_hook(d):
    """下载进度回调函数"""
    if d['status'] == 'downloading':
        # 计算下载百分比
        if d.get('total_bytes'):
            # 如果知道总大小，直接计算百分比
            percent = d.get('downloaded_bytes', 0) / d['total_bytes'] * 100
            downloaded = d.get('downloaded_bytes', 0) / (1024 * 1024)
            total = d['total_bytes'] / (1024 * 1024)
            speed = d.get('speed', 0) / (1024 * 1024) if d.get('speed') else 0
            eta = d.get('eta', 0)
            
            # 获取终端宽度并创建进度条
            term_width = get_terminal_width()
            progress_bar = draw_progress_bar(percent, min(30, term_width - 50))
            
            # 清除当前行并打印进度
            sys.stdout.write('\r')
            sys.stdout.write(f"{progress_bar} {downloaded:.1f}MB/{total:.1f}MB "
                            f"@ {speed:.2f}MB/s ETA: {eta}秒 ")
            sys.stdout.flush()
        elif d.get('downloaded_bytes'):
            # 如果不知道总大小，只显示已下载的大小
            downloaded = d.get('downloaded_bytes', 0) / (1024 * 1024)
            speed = d.get('speed', 0) / (1024 * 1024) if d.get('speed') else 0
            
            sys.stdout.write('\r')
            sys.stdout.write(f"已下载: {downloaded:.1f}MB 速度: {speed:.2f}MB/s ")
            sys.stdout.flush()
    
    elif d['status'] == 'finished':
        sys.stdout.write('\n')
        sys.stdout.write(f"下载完成，正在处理文件...\n")
        sys.stdout.flush()

def download_video(url, resolution="720", output_path=os.path.expanduser("~/Downloads"), proxy=None):
    """
    下载YouTube视频
    
    参数:
        url (str): YouTube视频URL
        resolution (str): 视频分辨率，例如 "360", "720" (默认 "720")
        output_path (str): 下载保存路径 (默认 ~/Downloads)
        proxy (str): 代理服务器，例如 "http://127.0.0.1:7897"
    
    返回:
        tuple: (成功状态, 文件路径或错误消息)
    """
    if not YTDLP_AVAILABLE:
        print("错误: 未安装 yt-dlp，请先运行: pip install yt-dlp")
        return False, "未安装 yt-dlp"
    
    try:
        import yt_dlp
        
        print(f"下载视频: {url}")
        print(f"目标分辨率: {resolution}p")
        print(f"保存路径: {output_path}")
        
        if proxy:
            print(f"使用代理: {proxy}")
        
        # 创建输出目录（如果不存在）
        os.makedirs(output_path, exist_ok=True)
        
        # 设置 yt-dlp 选项
        ydl_opts = {
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': True,
            'noplaylist': True,  # 不下载播放列表，只下载单个视频
            'progress_hooks': [progress_hook],  # 添加进度回调
            'noprogress': False,  # 确保显示进度
        }
        
        # 根据 ffmpeg 是否安装选择不同的格式
        if FFMPEG_AVAILABLE:
            # 如果 ffmpeg 已安装，使用最佳质量（可能需要合并）
            if resolution != "audio":
                ydl_opts['format'] = f'bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]'
            else:
                ydl_opts['format'] = 'bestaudio'
            print("使用 ffmpeg 合并模式，将获得最佳视频质量")
        else:
            # 如果 ffmpeg 未安装，使用单一格式（不需要合并）
            if resolution != "audio":
                ydl_opts['format'] = f'best[height<={resolution}]/best'
            else:
                ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio'
            print("警告: 未安装 ffmpeg，将下载单一格式视频。质量可能不是最佳。")
        
        # 添加代理设置
        if proxy:
            ydl_opts['proxy'] = proxy
        
        # 下载视频
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                return False, "下载失败: 无法获取视频信息"
            
            # 获取下载的文件路径
            if 'requested_downloads' in info:
                for download in info['requested_downloads']:
                    if 'filepath' in download:
                        return True, download['filepath']
            
            # 如果无法获取精确路径，构造一个可能的路径
            filename = ydl.prepare_filename(info)
            return True, filename
    
    except Exception as e:
        return False, f"下载错误: {str(e)}"

def list_formats(url, proxy=None):
    """
    列出视频的可用格式
    
    参数:
        url (str): YouTube视频URL
        proxy (str): 代理服务器
    
    返回:
        bool: 是否成功列出格式
    """
    if not YTDLP_AVAILABLE:
        print("错误: 未安装 yt-dlp，请先运行: pip install yt-dlp")
        return False
    
    try:
        import yt_dlp
        
        # 设置 yt-dlp 选项
        ydl_opts = {
            'listformats': True,
            'quiet': False,
            'no_warnings': False,
        }
        
        # 添加代理设置
        if proxy:
            ydl_opts['proxy'] = proxy
            print(f"使用代理: {proxy}")
        
        # 列出格式
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=False)
        return True
    
    except Exception as e:
        print(f"错误: {str(e)}")
        return False

def install_ytdlp():
    """安装 yt-dlp"""
    import subprocess
    
    print("正在安装 yt-dlp...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp"], check=True)
        print("yt-dlp 安装成功!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"安装失败: {str(e)}")
        return False

def install_ffmpeg():
    """安装 ffmpeg"""
    import subprocess
    import platform
    
    print("正在安装 ffmpeg...")
    try:
        system = platform.system()
        
        if system == "Darwin":  # macOS
            # 使用 Homebrew 安装
            try:
                # 检查 Homebrew 是否已安装
                subprocess.run(["which", "brew"], check=True, capture_output=True)
                # 安装 ffmpeg
                subprocess.run(["brew", "install", "ffmpeg"], check=True)
                print("ffmpeg 安装成功!")
                return True
            except subprocess.CalledProcessError:
                print("安装失败: 请先安装 Homebrew (https://brew.sh/)，然后再尝试安装 ffmpeg")
                return False
        
        elif system == "Windows":
            # 显示安装指南
            print("Windows 系统请手动安装 ffmpeg:")
            print("1. 访问 https://ffmpeg.org/download.html")
            print("2. 下载 Windows 版本")
            print("3. 解压并将 bin 目录添加到系统 PATH 环境变量")
            return False
        
        elif system == "Linux":
            # 尝试使用系统包管理器
            try:
                # 检测包管理器
                if subprocess.run(["which", "apt"], capture_output=True).returncode == 0:
                    subprocess.run(["sudo", "apt", "update"], check=True)
                    subprocess.run(["sudo", "apt", "install", "-y", "ffmpeg"], check=True)
                elif subprocess.run(["which", "yum"], capture_output=True).returncode == 0:
                    subprocess.run(["sudo", "yum", "install", "-y", "ffmpeg"], check=True)
                elif subprocess.run(["which", "pacman"], capture_output=True).returncode == 0:
                    subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"], check=True)
                else:
                    print("无法检测到支持的包管理器，请手动安装 ffmpeg")
                    return False
                
                print("ffmpeg 安装成功!")
                return True
            except subprocess.CalledProcessError as e:
                print(f"安装失败: {e}")
                return False
        else:
            print(f"不支持的操作系统: {system}")
            return False
                
    except Exception as e:
        print(f"发生错误: {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="带进度条的 YouTube 下载器")
    parser.add_argument("url", help="YouTube视频URL")
    parser.add_argument("-r", "--resolution", default="720", help="视频分辨率，例如 360, 720 (默认 720)")
    parser.add_argument("-o", "--output", default=os.path.expanduser("~/Downloads"), help="下载保存路径 (默认 ~/Downloads)")
    parser.add_argument("-p", "--proxy", help="代理服务器，例如 http://127.0.0.1:7897")
    parser.add_argument("-l", "--list-formats", action="store_true", help="列出可用格式而不下载")
    parser.add_argument("-i", "--install", action="store_true", help="安装 yt-dlp")
    parser.add_argument("-f", "--install-ffmpeg", action="store_true", help="安装 ffmpeg")
    
    args = parser.parse_args()
    
    # 检查是否需要安装 ffmpeg
    if args.install_ffmpeg:
        if install_ffmpeg():
            global FFMPEG_AVAILABLE
            FFMPEG_AVAILABLE = True
        else:
            print("ffmpeg 安装失败，将使用单一格式下载模式")
    
    # 检查是否需要安装 yt-dlp
    if args.install:
        if install_ytdlp():
            global YTDLP_AVAILABLE
            YTDLP_AVAILABLE = True
        else:
            return 1
    
    # 检查 yt-dlp 是否已安装
    if not YTDLP_AVAILABLE:
        print("错误: 未安装 yt-dlp")
        print("请使用 -i 选项安装 yt-dlp 或手动运行: pip install yt-dlp")
        return 1
    
    # 设置默认代理 (Clash Verge)
    if not args.proxy:
        clash_proxy = "http://127.0.0.1:7897"
        print(f"未指定代理，尝试使用默认 Clash Verge 代理: {clash_proxy}")
        args.proxy = clash_proxy
    
    # 列出格式或下载视频
    if args.list_formats:
        if not list_formats(args.url, args.proxy):
            return 1
    else:
        try:
            success, result = download_video(args.url, args.resolution, args.output, args.proxy)
            if success:
                print(f"\n下载成功: {result}")
            else:
                print(f"\n下载失败: {result}")
                return 1
        except KeyboardInterrupt:
            print("\n下载已取消")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 