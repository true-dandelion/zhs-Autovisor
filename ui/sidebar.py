from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
from PyQt6.QtCore import Qt

class CollapsibleSidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        self.setFixedWidth(150)
        self.setStyleSheet("QFrame { background-color: #E4B9D5; border: none; border-top-left-radius: 10px; border-bottom-left-radius: 10px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(70)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        header_layout.addStretch()

        self.title_label = QLabel("DELION")
        self.title_label.setStyleSheet("color: #4a4a4a; font-size: 16px; font-weight: bold;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        layout.addWidget(header)

        self.nav_container = QWidget()
        nav_layout = QVBoxLayout(self.nav_container)
        nav_layout.setContentsMargins(0, 10, 0, 0)
        nav_layout.setSpacing(5)

        self.btn_home = self.create_nav_button("首页")
        self.btn_config = self.create_nav_button("配置")
        self.btn_setting = self.create_nav_button("设置")
        self.btn_about = self.create_nav_button("关于")

        nav_layout.addWidget(self.btn_home)
        nav_layout.addWidget(self.btn_config)
        nav_layout.addWidget(self.btn_setting)
        nav_layout.addWidget(self.btn_about)
        nav_layout.addStretch()
        layout.addWidget(self.nav_container)

    def create_nav_button(self, text):
        btn = QPushButton(text)
        btn.setFixedHeight(50)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #4a4a4a;
                border: none;
                text-align: left;
                padding-left: 25px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: rgba(255,255,255,0.2); }
            QPushButton[active="true"] {
                background-color: #00A9BF;
                color: white;
                border-top-left-radius: 25px;
                border-bottom-left-radius: 25px;
                margin-left: 10px;
            }
        """)
        return btn
