from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QPoint

class TitleBarButtons(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.drag_pos = QPoint()
        self.setup_ui()

    def setup_ui(self):
        self.setFixedHeight(35)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 5, 0)
        layout.setSpacing(0)
        layout.addStretch()

        self.min_btn = QPushButton("—")
        self.min_btn.setFixedSize(40, 30)
        self.min_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover { background-color: rgba(0,0,0,0.05); }
        """)
        self.min_btn.clicked.connect(self.parent_window.showMinimized)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(40, 30)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #ff4757; color: white; }
        """)
        self.close_btn.clicked.connect(self.parent_window.close)

        layout.addWidget(self.min_btn)
        layout.addWidget(self.close_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.parent_window.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()
