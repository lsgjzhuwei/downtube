#!/usr/bin/env python3
import os
import sys
import argparse
import yt_dlp

# 默认下载路径
DEFAULT_DOWNLOAD_PATH = os.path.expanduser("~/Downloads")

def download_video(url, resolution="720", output_path=DEFAULT_DOWNLOAD_PATH, proxy=None):
    """下载YouTube视频"""
    print(f"正在下载: {url}")
    print(f"目标分辨率: {resolution}p")
    print(f"保存到: {output_path}")
    
    if proxy:
        print(f"使用代理: {proxy}")
    
    # 设置下载选项
    ydl_opts = {
        'format': f'bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'verbose': True,
        'ignoreerrors': True,
        'no_warnings': False,
        'quiet': False,
        'progress': True,
    }
    
    # 添加代理设置
    if proxy:
        ydl_opts['proxy'] = proxy
    
    # 执行下载
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                print(f"\n下载完成: {info.get('title', '未知标题')}")
                return True
            else:
                print("\n下载失败: 无法获取视频信息")
                return False
    except Exception as e:
        print(f"\n下载错误: {str(e)}")
        return False

def list_formats(url, proxy=None):
    """列出可用的视频格式"""
    print(f"正在获取视频信息: {url}")
    
    if proxy:
        print(f"使用代理: {proxy}")
    
    # 设置选项
    ydl_opts = {
        'listformats': True,
        'quiet': False,
    }
    
    # 添加代理设置
    if proxy:
        ydl_opts['proxy'] = proxy
    
    # 获取视频格式
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=False)
        return True
    except Exception as e:
        print(f"获取视频信息错误: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='YouTube 视频下载器 (使用 yt-dlp)')
    parser.add_argument('url', help='YouTube 视频链接')
    parser.add_argument('-r', '--resolution', default='720', help='视频最大分辨率高度 (默认: 720)')
    parser.add_argument('-o', '--output', default=DEFAULT_DOWNLOAD_PATH, help='下载保存路径')
    parser.add_argument('-p', '--proxy', help='代理地址 (格式: http://主机名:端口 或 socks5://主机名:端口)')
    parser.add_argument('-c', '--clash-verge', action='store_true', help='使用 Clash Verge 代理')
    parser.add_argument('-l', '--list', action='store_true', help='仅列出可用格式，不下载')
    
    args = parser.parse_args()
    
    # 设置代理
    proxy = None
    if args.clash_verge:
        proxy = 'http://127.0.0.1:7897'
    elif args.proxy:
        proxy = args.proxy
        if not proxy.startswith(('http://', 'https://', 'socks5://')):
            if ':' in proxy:
                proxy = f'http://{proxy}'  # 默认使用 HTTP 代理
    
    # 列出可用格式或下载视频
    if args.list:
        list_formats(args.url, proxy)
    else:
        download_video(args.url, args.resolution, args.output, proxy)

if __name__ == "__main__":
    main() 