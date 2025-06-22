    def check_ytdlp_installed(self):
        """检查是否安装了yt-dlp"""
        if YTDLP_AVAILABLE:
            self.ytdlp_label.setText("yt-dlp: 已安装")
            self.ytdlp_label.setStyleSheet("background-color: #2a5a2a; padding: 5px; border-radius: 4px;")
            self.install_ytdlp_btn.setText("更新 yt-dlp")
        else:
            self.ytdlp_label.setText("yt-dlp: 未安装")
            self.ytdlp_label.setStyleSheet("background-color: #5a2a2a; padding: 5px; border-radius: 4px;")
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