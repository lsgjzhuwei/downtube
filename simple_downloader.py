#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简化版YouTube下载器 - 无需 ffmpeg
这个脚本专门用于在没有安装 ffmpeg 的情况下下载YouTube视频
使用单一格式下载，避免需要合并视频和音频流
"""

import os
import sys
import argparse
import importlib.util
import time
import shutil
import re

# 检查是否安装了 yt-dlp
YTDLP_AVAILABLE = importlib.util.find_spec("yt_dlp") is not None

# 检查是否安装了 ffmpeg
def is_ffmpeg_installed():
    """检查系统是否安装了 ffmpeg"""
    return shutil.which('ffmpeg') is not None

# 全局变量，存储 ffmpeg 安装状态
FFMPEG_AVAILABLE = is_ffmpeg_installed()

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
            
            # 清除当前行并打印进度
            sys.stdout.write('\r')
            sys.stdout.write(f"下载进度: {percent:.1f}% ({downloaded:.1f}MB/{total:.1f}MB) "
                            f"速度: {speed:.2f}MB/s ETA: {eta}秒 ")
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

def download_with_ytdlp(url, resolution=None, download_path=None, proxy=None):
    """使用 yt-dlp 下载视频"""
    if not YTDLP_AVAILABLE:
        print("错误: 未安装 yt-dlp 库，请运行: pip install yt-dlp")
        return False
    
    try:
        import yt_dlp
        
        # 设置默认下载路径
        if not download_path:
            download_path = os.path.expanduser("~/Downloads")
            
        # 确保下载路径存在
        os.makedirs(download_path, exist_ok=True)
        
        # 设置代理
        proxy_opts = {}
        if proxy:
            proxy_opts = {'proxy': proxy}
        
        # 创建文件名
        safe_title = f"youtube_video_{int(time.time())}"
        output_file = os.path.join(download_path, f"{safe_title}.mp4")
        
        # 设置格式
        format_spec = 'bestvideo+bestaudio/best'
        if resolution == "audio":
            format_spec = 'bestaudio/best'
            output_file = os.path.join(download_path, f"{safe_title}.mp3")
        elif resolution:
            try:
                height = int(resolution)
                format_spec = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'
            except ValueError:
                print(f"警告: 无效的分辨率 '{resolution}'，使用最佳质量")
        
        # 创建 yt-dlp 选项
        ydl_opts = {
            'format': format_spec,
            'outtmpl': output_file,
            'no_check_certificate': True,  # 避免SSL证书问题
            'quiet': False,
            'no_warnings': False,  # 允许警告，以便捕获
            'writesubtitles': True,        # 下载字幕
            'writeautomaticsub': True,     # 下载自动生成的字幕
            'subtitleslangs': ['zh-CN', 'zh-TW', 'en'],  # 优先下载中文和英文字幕
            'subtitlesformat': 'srt',      # 使用SRT格式字幕
            # 优化下载速度的参数
            'concurrent_fragments': 5,     # 并发下载片段数，提高到5个
            'retries': 10,                 # 重试次数增加到10次
            'fragment_retries': 10,        # 片段重试次数
            'buffersize': 1024*1024*16,    # 增加缓冲区到16MB
            'http_chunk_size': 10485760,   # 10MB的块大小，提高吞吐量
            'socket_timeout': 30,          # 增加超时时间
            'extractor_retries': 5,        # 提取器重试次数
            'file_access_retries': 5,      # 文件访问重试
            **proxy_opts
        }
        
        # 如果 ffmpeg 可用，设置后处理参数
        if FFMPEG_AVAILABLE:
            ydl_opts['postprocessor_args'] = {
                'ffmpeg': ['-threads', '4', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k']
            }
        # 如果 ffmpeg 不可用，使用单一格式
        elif resolution != "audio":
            if resolution:
                try:
                    height = int(resolution)
                    ydl_opts['format'] = f'best[height<={height}]/best'
                except ValueError:
                    ydl_opts['format'] = 'best'
            else:
                ydl_opts['format'] = 'best'
            print("警告: 未检测到ffmpeg，无法合并单独的视频和音频流。将下载包含音频的单一视频流，质量可能较低。")
        
        # 下载视频
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        print(f"下载完成! 文件保存在: {download_path}")
        return True
        
    except Exception as e:
        print(f"下载失败: {str(e)}")
        return False

def list_formats(url, proxy=None):
    """列出可用的视频格式"""
    if not YTDLP_AVAILABLE:
        print("错误: 未安装 yt-dlp 库，请运行: pip install yt-dlp")
        return False
    
    try:
        import yt_dlp
        
        # 设置代理
        proxy_opts = {}
        if proxy:
            proxy_opts = {'proxy': proxy}
        
        # 创建 yt-dlp 选项
        ydl_opts = {
            'listformats': True,
            'no_check_certificate': True,  # 避免SSL证书问题
            **proxy_opts
        }
        
        # 列出格式
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        return True
        
    except Exception as e:
        print(f"获取格式列表失败: {str(e)}")
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

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='YouTube视频下载工具')
    parser.add_argument('url', help='要下载的YouTube视频URL')
    parser.add_argument('-r', '--resolution', help='视频分辨率 (例如: 1080, 720, 480, 360) 或 "audio" 仅下载音频')
    parser.add_argument('-o', '--output', help='下载路径')
    parser.add_argument('-p', '--proxy', help='代理服务器 (例如: http://127.0.0.1:7897)')
    parser.add_argument('-l', '--list', action='store_true', help='列出可用的视频格式')
    
    args = parser.parse_args()
    
    # 检查是否需要安装 yt-dlp
    if not YTDLP_AVAILABLE:
        print("错误: 未安装 yt-dlp")
        print("请使用 -i 选项安装 yt-dlp 或手动运行: pip install yt-dlp")
        return 1
    
    # 设置默认代理
    if not args.proxy:
        args.proxy = "http://127.0.0.1:7897"
        print(f"使用默认代理: {args.proxy}")
    
    # 列出格式或下载视频
    if args.list:
        list_formats(args.url, args.proxy)
    else:
        download_with_ytdlp(args.url, args.resolution, args.output, args.proxy)

if __name__ == "__main__":
    sys.exit(main()) 