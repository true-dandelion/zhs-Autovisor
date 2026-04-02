from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QScrollArea, QFrame)
from PyQt6.QtCore import Qt

class SettingsPage(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

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

        setting_content = QWidget()
        layout = QVBoxLayout(setting_content)
        layout.setContentsMargins(50, 35, 50, 35)
        layout.setSpacing(25)

        lbl_setting = QLabel("设置")
        lbl_setting.setStyleSheet("font-size: 28px; color: #1a1a1a; font-weight: bold;")
        layout.addWidget(lbl_setting)

        settings_container = QWidget()
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setContentsMargins(0, 10, 0, 0)
        settings_layout.setSpacing(2)

        update_group = self.create_setting_item("更新设置", "")
        settings_layout.addWidget(update_group)

        version_item = self.create_info_row("当前版本", "v1.0.1")
        settings_layout.addWidget(version_item)

        update_btn_container = QWidget()
        update_btn_layout = QHBoxLayout(update_btn_container)
        update_btn_layout.setContentsMargins(25, 18, 25, 18)
        update_btn_container.setStyleSheet("background-color: white;")
        self.check_update_btn = QPushButton("检查更新")
        self.check_update_btn.setFixedSize(120, 38)
        self.check_update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.check_update_btn.setStyleSheet("""
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
        update_btn_layout.addWidget(self.check_update_btn)
        update_btn_layout.addStretch()
        settings_layout.addWidget(update_btn_container)

        settings_layout.addSpacing(20)

        log_group = self.create_setting_item("日志设置", "")
        settings_layout.addWidget(log_group)

        log_path_item = self.create_info_row("保存路径", "./logs/")
        settings_layout.addWidget(log_path_item)

        log_btn_container = QWidget()
        log_btn_layout = QHBoxLayout(log_btn_container)
        log_btn_layout.setContentsMargins(25, 18, 25, 18)
        log_btn_container.setStyleSheet("background-color: white;")
        self.clear_log_btn = QPushButton("清空日志")
        self.clear_log_btn.setFixedSize(120, 38)
        self.clear_log_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_log_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b6b;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #ee5a5a; }
            QPushButton:pressed { background-color: #dd4a4a; }
        """)
        log_btn_layout.addWidget(self.clear_log_btn)
        log_btn_layout.addStretch()
        settings_layout.addWidget(log_btn_container)

        settings_layout.addSpacing(20)

        layout.addWidget(settings_container)
        layout.addStretch()

        self.setWidget(setting_content)

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

    def create_info_row(self, label_text, value_text):
        item = QWidget()
        layout = QHBoxLayout(item)
        layout.setContentsMargins(25, 18, 25, 18)
        item.setStyleSheet("background-color: white;")

        label = QLabel(label_text)
        label.setStyleSheet("font-size: 15px; color: #333;")

        value = QLabel(value_text)
        value.setStyleSheet("font-size: 15px; color: #00A9BF; font-weight: bold;")

        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(value)

        return item
