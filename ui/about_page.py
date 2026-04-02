from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from modules.version import VERSION


class AboutPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(15)

        lbl_title = QLabel("Automated Course Brushing")
        lbl_title.setStyleSheet("font-size: 28px; color: #333; font-weight: bold;")
        layout.addWidget(lbl_title)

        lbl_version = QLabel(f"版本号: {VERSION}")
        lbl_version.setStyleSheet("font-size: 16px; color: #666;")
        layout.addWidget(lbl_version)

        lbl_developer = QLabel("开发者: delion,sh-delion")
        lbl_developer.setStyleSheet("font-size: 16px; color: #666;")
        layout.addWidget(lbl_developer)

        lbl_email = QLabel("联系邮箱: delion@shaoxin.top")
        lbl_email.setStyleSheet("font-size: 16px; color: #666;")
        layout.addWidget(lbl_email)

        lbl_docs = QLabel("使用说明: ")
        lbl_docs.setStyleSheet("font-size: 16px; color: #666;")
        layout.addWidget(lbl_docs)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #ddd;")
        layout.addWidget(separator)

        lbl_disclaimer = QLabel(
            "免责声明:\n\n"
            "本软件仅供学习交流使用，请勿用于任何商业用途或非法目的。\n"
            "使用本软件所产生的一切后果由使用者自行承担，开发者不承担任何责任。\n"
            "请遵守相关法律法规和平台使用条款。"
        )
        lbl_disclaimer.setStyleSheet("font-size: 14px; color: #888; line-height: 1.6;")
        lbl_disclaimer.setWordWrap(True)
        layout.addWidget(lbl_disclaimer)

        layout.addStretch()
