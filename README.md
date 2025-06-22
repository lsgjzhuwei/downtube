# YouTube 视频下载器

一个简单易用的 YouTube 视频下载客户端工具，基于 Python 和 PyQt5 实现。

## 功能特点

- 添加 YouTube 视频链接
- 选择下载视频的清晰度
- 支持仅下载音频
- 可设置下载保存位置
- 批量下载多个视频
- 支持 HTTP/HTTPS 和 SOCKS5 代理设置
- 内置代理测试和自动代理探测功能
- 支持 yt-dlp 作为备选下载引擎
- 提供简化版下载器，无需 ffmpeg
- 提供带进度条的命令行下载器
- **新增！** 高速多线程下载器，支持 aria2c 加速

## 安装

1. 确保已安装 Python 3.6 或更高版本
2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 运行程序：

```bash
python main.py
```

## 使用方法

1. 点击左下角的"+"按钮添加 YouTube 视频链接
2. 点击"获取视频信息"按钮
3. 从下拉菜单中选择下载清晰度
4. 选择下载引擎（自动、pytubefix 或 yt-dlp）
5. 点击"确定"添加到下载列表
6. 点击"下载选中"或"下载全部"开始下载

### 设置代理

如果你所在的网络环境访问 YouTube 受限，或者遇到持续的 SSL 错误，可以通过设置代理来解决：

1. 点击主界面上的"设置代理"按钮
2. 选择代理类型：HTTP/HTTPS 或 SOCKS5
3. 输入代理地址，格式为 `主机名:端口号`（例如：`127.0.0.1:7890`）
4. 点击"测试代理"按钮验证代理是否可用
5. 点击"确定"应用代理设置

#### 自动探测代理

如果你正在使用 VPN 软件但不知道其代理端口，程序提供了自动探测功能：

1. 在代理设置对话框中点击"自动探测本地代理"按钮
2. 程序会自动扫描常用的代理端口
3. 发现可用的代理后，双击列表项选择该代理
4. 点击"确定"应用所选代理

#### 常见 VPN 软件的代理设置

| VPN 软件 | 代理类型 | 常见地址 |
|---------|---------|---------|
| Clash | HTTP | 127.0.0.1:7890 |
| Clash | SOCKS5 | 127.0.0.1:7891 |
| Clash Verge | HTTP/SOCKS5 | 127.0.0.1:7897 |
| V2Ray | HTTP | 127.0.0.1:10809 |
| V2Ray | SOCKS5 | 127.0.0.1:10808 |
| Shadowsocks | HTTP | 127.0.0.1:1080 |
| Lantern | HTTP | 127.0.0.1:8118 |
| ShadowsocksR | HTTP | 127.0.0.1:1080 |

### 关于 ffmpeg

yt-dlp 在下载某些视频格式时需要 ffmpeg 来合并视频和音频流。如果你遇到以下错误：

```
ERROR: You have requested merging of multiple formats but ffmpeg is not installed. Aborting due to --abort-on-error
```

你有两个选择：

1. **安装 ffmpeg**：
   - 在主界面点击"安装 ffmpeg"按钮
   - 或者根据你的操作系统手动安装：
     - macOS: `brew install ffmpeg`
     - Ubuntu/Debian: `sudo apt install ffmpeg`
     - Windows: 下载安装包并添加到 PATH 环境变量

2. **使用简化版下载器**：
   - 我们提供了一个不需要 ffmpeg 的简化版下载器 `simple_downloader.py`
   - 此下载器会使用单一格式下载，避免需要合并视频和音频流

### 使用命令行下载器

我们提供了三个命令行下载器，方便在不同场景下使用：

#### 1. 简化版下载器（无需 ffmpeg）

```bash
# 基本用法
python simple_downloader.py "https://www.youtube.com/watch?v=视频ID"

# 指定分辨率
python simple_downloader.py -r 720 "https://www.youtube.com/watch?v=视频ID"

# 指定输出路径
python simple_downloader.py -o "/下载路径" "https://www.youtube.com/watch?v=视频ID"

# 指定代理
python simple_downloader.py -p "http://127.0.0.1:7897" "https://www.youtube.com/watch?v=视频ID"

# 列出可用格式
python simple_downloader.py -l "https://www.youtube.com/watch?v=视频ID"

# 安装 yt-dlp
python simple_downloader.py -i "https://www.youtube.com/watch?v=视频ID"
```

#### 2. 带进度条的下载器

这个下载器提供了更直观的进度条显示，并且会根据是否安装了 ffmpeg 自动选择最佳下载方式：

```bash
# 基本用法
python progress_downloader.py "https://www.youtube.com/watch?v=视频ID"

# 指定分辨率
python progress_downloader.py -r 720 "https://www.youtube.com/watch?v=视频ID"

# 指定输出路径
python progress_downloader.py -o "/下载路径" "https://www.youtube.com/watch?v=视频ID"

# 指定代理
python progress_downloader.py -p "http://127.0.0.1:7897" "https://www.youtube.com/watch?v=视频ID"

# 列出可用格式
python progress_downloader.py -l "https://www.youtube.com/watch?v=视频ID"

# 安装 ffmpeg
python progress_downloader.py -f "https://www.youtube.com/watch?v=视频ID"

# 安装 yt-dlp
python progress_downloader.py -i "https://www.youtube.com/watch?v=视频ID"
```

#### 3. 高速多线程下载器（推荐）

这个全新的下载器针对下载速度进行了全面优化，具有以下特点：

- 多线程并发下载，最多同时下载 8 个片段
- 支持 aria2c 外部下载器加速（如果已安装）
- 更大的缓冲区和块大小（32MB 缓冲区，20MB 块大小）
- 更详细的格式信息显示和分类
- 更美观的彩色终端界面和进度显示
- 高度优化的网络参数

```bash
# 基本用法
./fast_downloader.py "https://www.youtube.com/watch?v=视频ID"

# 指定分辨率
./fast_downloader.py -r 720 "https://www.youtube.com/watch?v=视频ID"

# 指定输出路径
./fast_downloader.py -o "/下载路径" "https://www.youtube.com/watch?v=视频ID"

# 指定代理
./fast_downloader.py -p "http://127.0.0.1:7897" "https://www.youtube.com/watch?v=视频ID"

# 列出可用格式（详细分类显示）
./fast_downloader.py -l "https://www.youtube.com/watch?v=视频ID"

# 使用特定格式ID下载
./fast_downloader.py -f 22 "https://www.youtube.com/watch?v=视频ID"

# 安装 yt-dlp
./fast_downloader.py -i

# 安装 ffmpeg
./fast_downloader.py --ffmpeg

# 安装 aria2c 下载加速器
./fast_downloader.py -a
```

所有下载器都会自动尝试使用 Clash Verge 代理（127.0.0.1:7897），如果你使用其他代理，请通过 `-p` 参数指定。

## 常见问题

### Connection refused 错误

如果遇到 `Connection refused` 错误，通常意味着代理地址或端口不正确，请尝试：

1. 确认你的 VPN 软件正在运行
2. 验证输入的代理地址和端口是否正确
3. 使用"自动探测本地代理"功能找到可用代理
4. 如果使用 SOCKS5 代理，请确保已安装 PySocks 库：`pip install PySocks`

### SSL 错误：EOF occurred in violation of protocol

如果遇到 `<urlopen error EOF occurred in violation of protocol (_ssl.c:1129)>` 错误，这是由于 SSL/TLS 握手问题导致的，请尝试以下解决方法：

1. **使用代理服务器**（最有效的方法）：
   - 点击主界面上的"设置代理"按钮
   - 选择正确的代理类型（HTTP/HTTPS 或 SOCKS5）
   - 输入有效的代理地址
   - 使用"测试代理"按钮确认代理可用

2. **网络相关修复**：
   - 检查网络连接是否稳定
   - 确保你的系统时间和日期正确（SSL 证书验证依赖于此）
   - 尝试重启路由器或更换网络

3. **其他解决方法**：
   - 更新到最新版本的 Python
   - 更新 OpenSSL 库
   - 重启应用程序或电脑

程序已内置自动重试机制，遇到临时性的 SSL 错误时会自动重试连接。

### ffmpeg 相关错误

如果遇到 `ERROR: You have requested merging of multiple formats but ffmpeg is not installed` 错误：

1. 可以在主界面点击"安装 ffmpeg"按钮
2. 或者使用简化版下载器 `simple_downloader.py`，它不需要 ffmpeg
3. 或者使用带进度条的下载器 `progress_downloader.py`，它会自动适应是否安装了 ffmpeg
4. 或者手动安装 ffmpeg 后再使用主程序

### 下载进度显示为 0%

如果下载进度一直显示为 0%，可以尝试以下解决方法：

1. 使用我们提供的带进度条的下载器 `progress_downloader.py`，它有更好的进度显示功能
2. 确保你下载的视频格式支持进度显示（某些格式可能不报告总大小）
3. 尝试不同的分辨率或格式

### HTTP Error 400: Bad Request 错误

如果遇到 HTTP Error 400 错误，这通常是因为 YouTube API 变更导致的，可以通过以下方法解决：

1. 确保使用最新版本的 pytubefix 库：

```bash
pip install pytubefix --upgrade
```

2. 尝试切换到 yt-dlp 引擎：
   - 在添加视频对话框中选择"仅使用 yt-dlp"
   - 或者使用命令行下载器 `simple_downloader.py` 或 `progress_downloader.py`

### 视频无法下载或速度慢

- 检查网络连接
- 确认视频是否在你的地区可用
- 某些高清视频可能需要更长的下载时间
- 尝试使用代理服务器加速下载
- 尝试切换下载引擎（pytubefix 或 yt-dlp）

### 下载速度慢

如果遇到下载速度慢的问题，可以尝试以下解决方法：

1. **使用高速多线程下载器**（最有效的方法）：
   ```bash
   ./fast_downloader.py "https://www.youtube.com/watch?v=视频ID"
   ```
   
2. **安装并使用 aria2c 加速器**：
   ```bash
   ./fast_downloader.py -a  # 安装 aria2c
   ./fast_downloader.py "https://www.youtube.com/watch?v=视频ID"  # aria2c 会自动被使用
   ```

3. **检查网络和代理设置**：
   - 确保使用的代理速度足够快
   - 尝试更换不同的代理服务器
   - 检查网络连接是否稳定

4. **尝试不同的格式**：
   - 使用 `-l` 参数列出所有可用格式
   - 选择较小的文件大小或不同的编码格式
   - 使用 `-f` 参数指定特定的格式ID

## 开发者信息

如需修改或扩展此应用程序，主要代码结构如下：

- `main.py` - 主程序和 GUI 界面
- `simple_downloader.py` - 简化版命令行下载器（无需 ffmpeg）
- `progress_downloader.py` - 带进度条的命令行下载器
- `fast_downloader.py` - 高速多线程下载器（最新）
- `requirements.txt` - 依赖列表

## 许可证

MIT 许可证

## 解决 PyQt6 兼容性问题

如果您在运行 `main.py` 时遇到以下错误：

```
RuntimeError: This version of SIP is incompatible with this version of PyQt6. Try using the PyQt6 wheels from PyPI.
```

或者类似的 SIP 和 PyQt6 版本不匹配错误，您有两种解决方案：

### 方案一：使用虚拟环境（推荐）

使用提供的 `setup_env.py` 脚本来创建一个具有兼容版本的虚拟环境：

1. 运行设置脚本：
   ```bash
   python3 setup_env.py
   ```

2. 脚本将：
   - 创建名为 `downtube_venv` 的虚拟环境
   - 安装兼容版本的 PyQt6 和 PyQt6-sip
   - 安装所需的其他依赖项
   - 提供运行应用程序的命令

3. 按照脚本提示运行应用程序，或者使用以下命令：
   ```bash
   # macOS/Linux
   ./downtube_venv/bin/python main.py
   
   # Windows
   .\downtube_venv\Scripts\python main.py
   ```

### 方案二：使用修复版下载器

如果您遇到 `AttributeError: 'MainWindow' object has no attribute 'set_proxy'` 或其他类似错误，可以使用我们的修复版下载器：

```bash
python3 fixed_downloader.py
```

这个修复版下载器解决了原始代码中的重复类和方法问题，提供了一个简化但功能完整的界面，包括：

- 黑色主题界面
- 代理设置支持
- 分辨率选择
- 下载进度显示
- yt-dlp 和 ffmpeg 安装管理

## 使用命令行版本

如果您仍然遇到 GUI 问题，可以使用我们的命令行版本下载器：

1. `progress_downloader.py` - 带进度条的下载器
   ```bash
   python3 progress_downloader.py "https://www.youtube.com/watch?v=视频ID"
   ```

2. `simple_downloader.py` - 简化版下载器
   ```bash
   python3 simple_downloader.py "https://www.youtube.com/watch?v=视频ID"
   ```

3. `dark_downloader.py` - 黑色主题命令行下载器
   ```bash
   python3 dark_downloader.py "https://www.youtube.com/watch?v=视频ID"
   ``` 