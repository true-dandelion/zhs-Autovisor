import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QFrame, QStackedWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt

from ui import HomePage, ConfigPage, SettingsPage, AboutPage, CollapsibleSidebar, TitleBarButtons
from modules.engine import Engine


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(1000, 600)
        self.engine = Engine()
        self.setup_ui()

    def setup_ui(self):
        main_frame = QFrame()
        main_frame.setObjectName("mainFrame")
        main_frame.setStyleSheet("QFrame#mainFrame { background-color: white; border: 1px solid #ddd; border-radius: 10px; }")
        self.setCentralWidget(main_frame)

        layout = QHBoxLayout(main_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = CollapsibleSidebar()
        layout.addWidget(self.sidebar)

        content_area = QFrame()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.ctrl_bar = TitleBarButtons(self)
        self.ctrl_bar.setStyleSheet("border-top-right-radius: 10px;")
        content_layout.addWidget(self.ctrl_bar)

        self.pages = QStackedWidget()
        self.pages.setStyleSheet("background-color: white; border-bottom-right-radius: 10px;")

        self.home_page = HomePage()
        self.home_page.set_engine(self.engine)
        self.pages.addWidget(self.home_page)

        self.config_page = ConfigPage()
        self.pages.addWidget(self.config_page)

        self.settings_page = SettingsPage()
        self.pages.addWidget(self.settings_page)

        self.about_page = AboutPage()
        self.pages.addWidget(self.about_page)

        content_layout.addWidget(self.pages)
        layout.addWidget(content_area)

        self.sidebar.btn_home.clicked.connect(lambda: self.switch_page(0, self.sidebar.btn_home))
        self.sidebar.btn_config.clicked.connect(lambda: self.switch_page(1, self.sidebar.btn_config))
        self.sidebar.btn_setting.clicked.connect(lambda: self.switch_page(2, self.sidebar.btn_setting))
        self.sidebar.btn_about.clicked.connect(lambda: self.switch_page(3, self.sidebar.btn_about))

        self.switch_page(0, self.sidebar.btn_home)

        self.home_page.start_btn.clicked.connect(self.home_page.toggle_start)
        self.settings_page.check_update_btn.clicked.connect(self.check_update)
        self.settings_page.clear_log_btn.clicked.connect(self.clear_logs)

    def switch_page(self, index, button):
        self.pages.setCurrentIndex(index)
        buttons = [self.sidebar.btn_home, self.sidebar.btn_config, 
                   self.sidebar.btn_setting, self.sidebar.btn_about]
        for btn in buttons:
            btn.setProperty("active", False)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        button.setProperty("active", True)
        button.style().unpolish(button)
        button.style().polish(button)

    def check_update(self):
        self.home_page.log_message("检查更新...")

    def clear_logs(self):
        self.home_page.log_text.clear()
        self.home_page.log_message("日志已清空")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
