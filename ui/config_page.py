from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QComboBox, QCheckBox, QScrollArea, QGroupBox,
                             QMessageBox)
from PyQt6.QtCore import Qt


class ConfigPage(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_file = "configs.ini"
        self.load_config()
        self.setup_ui()

    def load_config(self):
        import configparser
        import os
        self.config = configparser.ConfigParser()
        if os.path.exists(self.config_file):
            try:
                self.config.read(self.config_file, encoding="utf-8")
            except:
                self.config.read(self.config_file, encoding="gbk")

    def save_config(self):
        import configparser
        if not hasattr(self, 'config'):
            self.config = configparser.ConfigParser()
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)

    def setup_ui(self):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QScrollArea {
                background-color: #fafbfc;
                border: none;
            }
        """)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(50, 35, 50, 35)
        layout.setSpacing(25)

        lbl_title = QLabel("配置")
        lbl_title.setStyleSheet("font-size: 28px; color: #1a1a1a; font-weight: bold;")
        layout.addWidget(lbl_title)

        config_container = QWidget()
        config_layout = QVBoxLayout(config_container)
        config_layout.setContentsMargins(0, 10, 0, 0)
        config_layout.setSpacing(2)

        account_group = self.create_setting_item("账号设置", "")
        config_layout.addWidget(account_group)

        username_row = self.create_input_row("用户名:", self.config.get('user-account', 'username', fallback=''), "留空则手动登录")
        config_layout.addWidget(username_row)

        password_row = self.create_input_row("密码:", self.config.get('user-account', 'password', fallback=''), "留空则手动登录", is_password=True)
        config_layout.addWidget(password_row)

        config_layout.addSpacing(20)

        browser_group = self.create_setting_item("浏览器设置", "")
        config_layout.addWidget(browser_group)

        driver_row = self.create_combo_row("浏览器:", ["Edge", "Chrome"], self.config.get('browser-option', 'driver', fallback='edge'))
        config_layout.addWidget(driver_row)

        exe_path_row = self.create_input_row("浏览器路径:", self.config.get('browser-option', 'EXE_PATH', fallback=''), "留空使用默认路径")
        config_layout.addWidget(exe_path_row)

        config_layout.addSpacing(20)

        course_group = self.create_setting_item("课程选项", "")
        config_layout.addWidget(course_group)

        speed_row = self.create_combo_row("播放倍速:", ["1.0", "1.5", "2.0"], self.config.get('course-option', 'limitSpeed', fallback='1.0'), "speed_combo")
        config_layout.addWidget(speed_row)

        mute_row = self.create_checkbox_row("静音播放", self.config.get('course-option', 'soundOff', fallback='True').lower() == 'true')
        config_layout.addWidget(mute_row)

        config_layout.addSpacing(20)

        script_group = self.create_setting_item("脚本选项", "")
        config_layout.addWidget(script_group)

        auto_captcha_row = self.create_checkbox_row("自动跳过滑块验证", self.config.get('script-option', 'enableAutoCaptcha', fallback='True').lower() == 'true')
        config_layout.addWidget(auto_captcha_row)

        auto_click_captcha_row = self.create_checkbox_row("自动点击验证", self.config.get('script-option', 'enableAutoClickCaptcha', fallback='False').lower() == 'true')
        config_layout.addWidget(auto_click_captcha_row)

        hide_window_row = self.create_checkbox_row("隐藏浏览器窗口", self.config.get('script-option', 'enableHideWindow', fallback='False').lower() == 'true')
        config_layout.addWidget(hide_window_row)

        keep_open_row = self.create_checkbox_row("完成后保持浏览器打开", self.config.get('script-option', 'keepBrowserOpen', fallback='True').lower() == 'true')
        config_layout.addWidget(keep_open_row)

        config_layout.addSpacing(20)

        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(25, 18, 25, 18)
        btn_container.setStyleSheet("background-color: white;")

        save_btn = QPushButton("保存配置")
        save_btn.setFixedSize(120, 38)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #00A9BF;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #008C9E; }
            QPushButton:pressed { background-color: #007A8A; }
        """)
        save_btn.clicked.connect(self.on_save)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        config_layout.addWidget(btn_container)

        layout.addWidget(config_container)
        layout.addStretch()

        self.setWidget(content)

    def create_setting_item(self, title, subtitle):
        item = QWidget()
        layout = QVBoxLayout(item)
        layout.setContentsMargins(25, 15, 25, 15)
        layout.setSpacing(3)
        item.setStyleSheet("background-color: white; border-bottom: 1px solid #f0f0f0;")

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px; color: #1a1a1a; font-weight: bold;")
        layout.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setStyleSheet("font-size: 13px; color: #999;")
            layout.addWidget(subtitle_label)

        return item

    def create_input_row(self, label_text, default_value, placeholder, is_password=False):
        item = QWidget()
        layout = QHBoxLayout(item)
        layout.setContentsMargins(25, 18, 25, 18)
        item.setStyleSheet("background-color: white;")

        label = QLabel(label_text)
        label.setStyleSheet("font-size: 15px; color: #333;")
        layout.addWidget(label)

        line_edit = QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        line_edit.setText(default_value)
        line_edit.setStyleSheet("""
            QLineEdit {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                color: #333;
            }
            QLineEdit:focus {
                border: 1px solid #00A9BF;
                background-color: white;
            }
            QLineEdit::placeholder {
                color: #999;
            }
        """)
        if is_password:
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(line_edit)

        if label_text == "用户名:":
            self.username_edit = line_edit
        elif label_text == "密码:":
            self.password_edit = line_edit
        elif label_text == "浏览器路径:":
            self.exe_path_edit = line_edit
        elif label_text == "播放倍速:":
            self.speed_edit = line_edit

        return item

    def create_combo_row(self, label_text, items, current_value, var_name="driver_combo"):
        item = QWidget()
        layout = QHBoxLayout(item)
        layout.setContentsMargins(25, 18, 25, 18)
        item.setStyleSheet("background-color: white;")

        label = QLabel(label_text)
        label.setStyleSheet("font-size: 15px; color: #333;")
        layout.addWidget(label)

        combo = QComboBox()
        combo.addItems(items)
        combo.setCurrentText(current_value.capitalize() if current_value else items[0].capitalize())
        combo.setStyleSheet("""
            QComboBox {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                color: #333;
                min-width: 120px;
            }
            QComboBox:focus {
                border: 1px solid #00A9BF;
                background-color: white;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                width: 0px;
                height: 0px;
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                selection-background-color: #00A9BF;
                selection-color: white;
            }
        """)
        layout.addWidget(combo)
        layout.addStretch()

        setattr(self, var_name, combo)

        return item

    def create_checkbox_row(self, text, checked):
        item = QWidget()
        layout = QHBoxLayout(item)
        layout.setContentsMargins(25, 18, 25, 18)
        item.setStyleSheet("background-color: white;")

        checkbox = QCheckBox(text)
        checkbox.setChecked(checked)
        checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 15px;
                color: #333;
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid #d0d0d0;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #00A9BF;
                border-color: #00A9BF;
            }
        """)
        layout.addWidget(checkbox)
        layout.addStretch()

        if text == "自动跳过滑块验证":
            self.auto_captcha_cb = checkbox
        elif text == "自动点击验证":
            self.auto_click_captcha_cb = checkbox
        elif text == "隐藏浏览器窗口":
            self.hide_window_cb = checkbox
        elif text == "完成后保持浏览器打开":
            self.keep_open_cb = checkbox
        elif text == "静音播放":
            self.mute_cb = checkbox

        return item

    def on_save(self):
        import configparser
        if not hasattr(self, 'config'):
            self.config = configparser.ConfigParser()

        if not self.config.has_section('course-option'):
            self.config.add_section('course-option')
        if not self.config.has_section('script-option'):
            self.config.add_section('script-option')
        if not self.config.has_section('browser-option'):
            self.config.add_section('browser-option')
        if not self.config.has_section('user-account'):
            self.config.add_section('user-account')

        self.config.set('course-option', 'limitSpeed', self.speed_combo.currentText())
        self.config.set('course-option', 'soundOff', str(self.mute_cb.isChecked()))
        self.config.set('script-option', 'enableAutoCaptcha', str(self.auto_captcha_cb.isChecked()))
        self.config.set('script-option', 'enableAutoClickCaptcha', str(self.auto_click_captcha_cb.isChecked()))
        self.config.set('script-option', 'enableHideWindow', str(self.hide_window_cb.isChecked()))
        self.config.set('script-option', 'keepBrowserOpen', str(self.keep_open_cb.isChecked()))
        self.config.set('browser-option', 'driver', self.driver_combo.currentText().lower())
        self.config.set('browser-option', 'EXE_PATH', self.exe_path_edit.text())
        self.config.set('user-account', 'username', self.username_edit.text())
        self.config.set('user-account', 'password', self.password_edit.text())

        self.save_config()
        
        self.show_save_success_dialog()

    def show_save_success_dialog(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QWidget
        dialog = QDialog(self)
        dialog.setWindowTitle("提示")
        dialog.setFixedSize(200, 180)
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #EBEFF3;
                border-radius: 10px;
            }
        """)
        
        main_widget = QWidget()
        main_widget.setObjectName("dialogMain")
        main_widget.setStyleSheet("""
            QWidget#dialogMain {
                background-color: #EBEFF3;
                border-radius: 10px;
            }
        """)
        
        content_widget = QWidget()
        content_widget.setObjectName("contentWidget")
        content_widget.setStyleSheet("""
            QWidget#contentWidget {
                background-color: #EBEFF3;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)
        
        title_bar = QWidget()
        title_bar.setFixedHeight(35)
        title_bar.setObjectName("titleBar")
        title_bar.setStyleSheet("""
            QWidget#titleBar {
                background-color: #EBEFF3;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(10, 0, 5, 0)
        title_bar_layout.setSpacing(0)
        
        title_label = QLabel("提示")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; border: none; background-color: transparent;")
        title_bar_layout.addWidget(title_label)
        title_bar_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(25, 25)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #ff4757; color: white; border-radius: 12px; }
        """)
        close_btn.clicked.connect(dialog.close)
        title_bar_layout.addWidget(close_btn)
        
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(title_bar)
        
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 0, 20, 20)
        content_layout.setSpacing(15)
        
        msg_label = QLabel("保存成功")
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_label.setStyleSheet("font-size: 16px; color: #00A9BF; background-color: #EBEFF3;")
        content_layout.addWidget(msg_label)
        
        btn_container = QWidget()
        btn_container.setStyleSheet("background-color: #EBEFF3;")
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(0)
        
        btn_layout.addStretch()
        
        ok_btn = QPushButton("确定")
        ok_btn.setFixedSize(80, 32)
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #00A9BF;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #008C9E; }
        """)
        ok_btn.clicked.connect(dialog.close)
        btn_layout.addWidget(ok_btn)
        
        content_layout.addWidget(btn_container)
        
        layout.addWidget(content_widget)
        
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(main_widget)
        
        dialog.exec()
