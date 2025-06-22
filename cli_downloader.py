#!/usr/bin/env python3
import os
import sys
import ssl
import time
import urllib.request
import socket
import http.client
import json
import argparse
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
PROXY_TYPE = "http"  # "http" 或 "socks5"

def set_proxy(url=None, proxy_type="http"):
    """设置HTTP/HTTPS或SOCKS5代理"""
    global USE_PROXY, PROXY_URL, PROXY_TYPE
    
    if url:
        if proxy_type == "http":
            proxy_handler = urllib.request.ProxyHandler({
                'http': url,
                'https': url
            })
            opener = urllib.request.build_opener(
                proxy_handler,
                urllib.request.HTTPSHandler(context=ssl_context)
            )
        elif proxy_type == "socks5":
            try:
                import socks
                # 解析主机名和端口
                if ":" in url:
                    host, port = url.split(":")
                    port = int(port)
                else:
                    host = url
                    port = 1080  # 默认SOCKS5端口
                    
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
            raise ValueError(f"不支持的代理类型: {proxy_type}, 支持的类型有: http, socks5")
            
        urllib.request.install_opener(opener)
        USE_PROXY = True
        PROXY_URL = url
        PROXY_TYPE = proxy_type
        print(f"已设置{proxy_type}代理: {url}")
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
        print("已清除代理设置")

def set_clash_verge_proxy():
    """设置 Clash Verge 代理"""
    proxy_url = "127.0.0.1:7897"
    proxy_type = "http"  # Clash Verge 同时支持 HTTP 和 SOCKS5，默认使用 HTTP
    set_proxy(proxy_url, proxy_type)
    return proxy_url, proxy_type

def progress_callback(stream, chunk, bytes_remaining):
    """显示下载进度"""
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage = int(bytes_downloaded / total_size * 100)
    sys.stdout.write(f"\r下载进度: {percentage}%")
    sys.stdout.flush()

def download_video(url, resolution="720p", download_path=DEFAULT_DOWNLOAD_PATH, max_retries=5):
    """下载视频"""
    retry_count = 0
    retry_delay = 3
    last_error = None
    
    print(f"正在下载: {url}")
    print(f"分辨率: {resolution}")
    print(f"保存到: {download_path}")
    
    while retry_count < max_retries:
        try:
            # 每次重试前重新设置代理，确保代理连接是新的
            if USE_PROXY and PROXY_URL:
                set_proxy(PROXY_URL, PROXY_TYPE)
            
            # 创建 YouTube 对象
            yt = YouTube(
                url,
                use_oauth=True,
                allow_oauth_cache=True,
                on_progress_callback=progress_callback,
                proxies=None if not USE_PROXY else {
                    'http': PROXY_URL if PROXY_TYPE == 'http' else None,
                    'https': PROXY_URL if PROXY_TYPE == 'http' else None
                }
            )
            
            print(f"视频标题: {yt.title}")
            print(f"作者: {yt.author}")
            
            # 获取指定分辨率的视频流
            if resolution != "audio":
                stream = yt.streams.filter(res=resolution, progressive=True).first()
                if not stream:
                    stream = yt.streams.filter(res=resolution).first()
                if not stream:
                    print(f"无法找到 {resolution} 分辨率的视频，尝试最高可用分辨率")
                    stream = yt.streams.get_highest_resolution()
            else:
                stream = yt.streams.get_audio_only()
                print("下载音频")
            
            if not stream:
                print(f"无法找到可用的视频流")
                return False
            
            # 下载视频
            file_path = stream.download(output_path=download_path)
            print(f"\n下载完成: {file_path}")
            return True
            
        except (ssl.SSLError, urllib.error.URLError, ConnectionError, TimeoutError) as e:
            retry_count += 1
            last_error = e
            
            # 对于SSL错误，尝试更改SSL上下文
            if isinstance(e, ssl.SSLError) or (isinstance(e, urllib.error.URLError) and "EOF occurred in violation of protocol" in str(e)):
                # 尝试重置SSL上下文
                global ssl_context
                try:
                    # 创建新的SSL上下文，尝试不同的设置
                    new_context = ssl.create_default_context()
                    new_context.check_hostname = False
                    new_context.verify_mode = ssl.CERT_NONE
                    # 尝试允许所有TLS版本
                    new_context.options = 0
                    ssl_context = new_context
                    
                    # 重新创建opener
                    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
                    urllib.request.install_opener(opener)
                    
                    # 如果使用代理，重新应用代理
                    if USE_PROXY and PROXY_URL:
                        set_proxy(PROXY_URL, PROXY_TYPE)
                except Exception:
                    pass
            
            if retry_count < max_retries:
                print(f"\n遇到错误，正在重试 ({retry_count}/{max_retries}): {str(e)}")
                time.sleep(retry_delay * retry_count)  # 指数退避
                continue
            
            if isinstance(e, ssl.SSLError):
                print(f"\nSSL错误 (尝试 {retry_count}/{max_retries}): {str(e)}")
            elif isinstance(e, urllib.error.URLError):
                print(f"\n网络错误 (尝试 {retry_count}/{max_retries}): {str(e)}")
            elif isinstance(e, ConnectionError):
                print(f"\n连接错误 (尝试 {retry_count}/{max_retries}): {str(e)}")
            else:
                print(f"\n超时错误 (尝试 {retry_count}/{max_retries}): 连接超时")
                
        except exceptions.RegexMatchError:
            print("\n无效的YouTube链接")
            return False
            
        except exceptions.VideoUnavailable:
            print("\n该视频不可用")
            return False
            
        except Exception as e:
            retry_count += 1
            last_error = e
            if retry_count < max_retries:
                print(f"\n遇到错误，正在重试 ({retry_count}/{max_retries}): {str(e)}")
                time.sleep(retry_delay)
                continue
            print(f"\n下载错误: {str(e)}")
            return False

    # 如果所有重试都失败
    if last_error:
        error_type = type(last_error).__name__
        print(f"\n在 {max_retries} 次尝试后仍然失败 ({error_type}): {str(last_error)}")
        
        # 提供更多具体的解决建议
        if "EOF occurred in violation of protocol" in str(last_error):
            print("\n这是一个 SSL 握手问题，请尝试以下解决方法：")
            print("1. 确保您的代理服务器已正确配置并且能够访问 YouTube")
            print("2. 尝试使用 SOCKS5 代理而不是 HTTP 代理")
            print("3. 确保您的系统时间是准确的")
            print("4. 尝试重启您的 VPN 软件")
            print("5. 如果问题持续存在，可能需要更新 Python 或 OpenSSL 库")
        else:
            print("\n请尝试使用代理或者稍后再试。")
    
    return False

def list_available_resolutions(url, max_retries=5):
    """列出可用的分辨率"""
    retry_count = 0
    retry_delay = 3
    last_error = None
    
    print(f"正在获取视频信息: {url}")
    
    while retry_count < max_retries:
        try:
            # 每次重试前重新设置代理，确保代理连接是新的
            if USE_PROXY and PROXY_URL:
                set_proxy(PROXY_URL, PROXY_TYPE)
            
            # 创建 YouTube 对象
            yt = YouTube(
                url,
                use_oauth=True,
                allow_oauth_cache=True,
                proxies=None if not USE_PROXY else {
                    'http': PROXY_URL if PROXY_TYPE == 'http' else None,
                    'https': PROXY_URL if PROXY_TYPE == 'http' else None
                }
            )
            
            print(f"视频标题: {yt.title}")
            print(f"作者: {yt.author}")
            
            # 获取所有可用分辨率
            streams = yt.streams.filter(progressive=True).order_by('resolution')
            resolutions = []
            
            for stream in streams:
                if stream.resolution and stream.resolution not in resolutions:
                    resolutions.append(stream.resolution)
            
            # 如果没有可用分辨率，寻找其他流
            if not resolutions:
                streams = yt.streams.filter(file_extension="mp4").order_by('resolution')
                for stream in streams:
                    if stream.resolution and stream.resolution not in resolutions:
                        resolutions.append(stream.resolution)
            
            # 按分辨率降序排序
            resolutions.sort(key=lambda x: int(x[:-1]) if x[:-1].isdigit() else 0, reverse=True)
            
            print("\n可用分辨率:")
            for res in resolutions:
                print(f"- {res}")
            print("- audio (仅音频)")
            
            return resolutions
            
        except (ssl.SSLError, urllib.error.URLError, ConnectionError, TimeoutError) as e:
            retry_count += 1
            last_error = e
            
            # 对于SSL错误，尝试更改SSL上下文
            if isinstance(e, ssl.SSLError) or (isinstance(e, urllib.error.URLError) and "EOF occurred in violation of protocol" in str(e)):
                # 尝试重置SSL上下文
                global ssl_context
                try:
                    # 创建新的SSL上下文，尝试不同的设置
                    new_context = ssl.create_default_context()
                    new_context.check_hostname = False
                    new_context.verify_mode = ssl.CERT_NONE
                    # 尝试允许所有TLS版本
                    new_context.options = 0
                    ssl_context = new_context
                    
                    # 重新创建opener
                    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
                    urllib.request.install_opener(opener)
                    
                    # 如果使用代理，重新应用代理
                    if USE_PROXY and PROXY_URL:
                        set_proxy(PROXY_URL, PROXY_TYPE)
                except Exception:
                    pass
            
            if retry_count < max_retries:
                print(f"遇到错误，正在重试 ({retry_count}/{max_retries}): {str(e)}")
                time.sleep(retry_delay * retry_count)  # 指数退避
                continue
            
            if isinstance(e, ssl.SSLError):
                print(f"SSL连接错误 (尝试 {retry_count}/{max_retries}): {str(e)}")
            elif isinstance(e, urllib.error.URLError):
                print(f"网络连接错误 (尝试 {retry_count}/{max_retries}): {str(e)}")
            elif isinstance(e, ConnectionError):
                print(f"连接错误 (尝试 {retry_count}/{max_retries}): {str(e)}")
            else:
                print(f"连接超时 (尝试 {retry_count}/{max_retries})")
                
        except exceptions.RegexMatchError:
            print("无效的YouTube链接")
            return []
            
        except exceptions.VideoUnavailable:
            print("该视频不可用")
            return []
            
        except Exception as e:
            retry_count += 1
            last_error = e
            if retry_count < max_retries:
                print(f"遇到错误，正在重试 ({retry_count}/{max_retries}): {str(e)}")
                time.sleep(retry_delay)
                continue
            print(f"获取视频信息错误: {str(e)}")
            return []
    
    # 如果所有重试都失败
    if last_error:
        error_type = type(last_error).__name__
        print(f"在 {max_retries} 次尝试后仍然失败 ({error_type}): {str(last_error)}")
        
        # 提供更多具体的解决建议
        if "EOF occurred in violation of protocol" in str(last_error):
            print("\n这是一个 SSL 握手问题，请尝试以下解决方法：")
            print("1. 确保您的代理服务器已正确配置并且能够访问 YouTube")
            print("2. 尝试使用 SOCKS5 代理而不是 HTTP 代理")
            print("3. 确保您的系统时间是准确的")
            print("4. 尝试重启您的 VPN 软件")
            print("5. 如果问题持续存在，可能需要更新 Python 或 OpenSSL 库")
        else:
            print("\n请尝试使用代理或者稍后再试。")
    
    return []

def main():
    parser = argparse.ArgumentParser(description='YouTube 视频下载器命令行版本')
    parser.add_argument('url', help='YouTube 视频链接')
    parser.add_argument('-r', '--resolution', default='720p', help='视频分辨率 (默认: 720p)')
    parser.add_argument('-o', '--output', default=DEFAULT_DOWNLOAD_PATH, help='下载保存路径')
    parser.add_argument('-p', '--proxy', help='代理地址 (格式: 主机名:端口)')
    parser.add_argument('-t', '--proxy-type', default='http', choices=['http', 'socks5'], help='代理类型 (默认: http)')
    parser.add_argument('-c', '--clash-verge', action='store_true', help='使用 Clash Verge 代理 (127.0.0.1:7897)')
    parser.add_argument('-l', '--list', action='store_true', help='仅列出可用分辨率，不下载')
    
    args = parser.parse_args()
    
    # 设置代理
    if args.clash_verge:
        set_clash_verge_proxy()
    elif args.proxy:
        set_proxy(args.proxy, args.proxy_type)
    
    # 列出可用分辨率或下载视频
    if args.list:
        list_available_resolutions(args.url)
    else:
        download_video(args.url, args.resolution, args.output)

if __name__ == "__main__":
    main() 