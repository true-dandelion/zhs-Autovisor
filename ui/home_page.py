from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, 
                             QListWidget, QListWidgetItem, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from modules.engine import Course


class EngineThread(QThread):
    log_signal = pyqtSignal(str)
    
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.engine.set_log_callback(lambda msg: self.log_signal.emit(msg))
    
    def run(self):
        self.engine.start()
    
    def stop(self):
        self.engine.stop()


class HomePage(QWidget):
    log_signal = pyqtSignal(str)
    browser_closed_signal = pyqtSignal()
    course_list_loaded_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    progress_update_signal = pyqtSignal(str, str, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False
        self.engine_thread = None
        self.engine = None
        self.courses = []
        self.selected_course = None
        self.setup_ui()
        self.log_signal.connect(self._append_log)
        self.browser_closed_signal.connect(self._on_browser_closed)
        self.course_list_loaded_signal.connect(self._on_course_list_loaded)
        self.error_signal.connect(self._on_error)
        self.progress_update_signal.connect(self._on_progress_update)

    def set_engine(self, engine):
        self.engine = engine
        self.engine.set_log_callback(lambda msg: self.log_signal.emit(msg))
        self.engine.set_course_list_callback(self.course_list_loaded_signal.emit)
        self.engine.set_browser_closed_callback(self.browser_closed_signal.emit)
        self.engine.set_error_callback(self.error_signal.emit)
        self.engine.set_progress_callback(self.progress_update_signal.emit)
        self.engine.set_ui_running_callback(lambda: self.is_running)

    def _on_progress_update(self, course_name: str, video_name: str, progress: int):
        self.update_progress_bar(progress, course_name, video_name)

    def _on_error(self, error_msg):
        self.log_message(error_msg)
        self.is_running = False
        self.start_btn.setText("启动刷课")
        self.start_btn.setProperty("stopped", False)
        self.start_btn.style().unpolish(self.start_btn)
        self.start_btn.style().polish(self.start_btn)
        self.status_label.setText("已停止")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #ff6b6b;
                color: white;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
        """)

    def _on_course_list_loaded(self, courses):
        self.on_course_list_loaded(courses)

    def _on_browser_closed(self):
        self.log_message("浏览器已关闭")
        self.is_running = False
        self.start_btn.setText("启动刷课")
        self.start_btn.setProperty("stopped", False)
        self.start_btn.style().unpolish(self.start_btn)
        self.start_btn.style().polish(self.start_btn)
        self.status_label.setText("已停止")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #ff6b6b;
                color: white;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
        """)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 20, 40, 40)
        layout.setSpacing(15)

        lbl_home = QLabel("首页")
        lbl_home.setStyleSheet("font-size: 24px; color: #333; font-weight: bold;")
        layout.addWidget(lbl_home)

        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(15)

        self.status_label = QLabel("未运行")
        self.status_label.setFixedSize(100, 38)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #e0e0e0;
                color: #666;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        status_layout.addWidget(self.status_label)

        self.start_btn = QPushButton("启动刷课")
        self.start_btn.setFixedSize(120, 38)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #00A9BF;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #008C9E; }
            QPushButton:pressed { background-color: #007A8A; }
            QPushButton[stopped="true"] {
                background-color: #ff6b6b;
            }
            QPushButton[stopped="true"]:hover { background-color: #ee5a5a; }
        """)
        status_layout.addWidget(self.start_btn)

        status_layout.addStretch()

        layout.addWidget(status_container)

        course_container = QWidget()
        course_layout = QHBoxLayout(course_container)
        course_layout.setContentsMargins(0, 0, 0, 0)
        course_layout.setSpacing(15)

        course_list_label = QLabel("课程列表")
        course_list_label.setStyleSheet("font-size: 14px; color: #666;")
        course_layout.addWidget(course_list_label)

        self.course_list_widget = QListWidget()
        self.course_list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.course_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.course_list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: #f9f9f9;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #00A9BF;
                color: white;
            }
        """)
        self.course_list_widget.itemClicked.connect(self.on_course_selected)
        course_layout.addWidget(self.course_list_widget)

        layout.addWidget(course_container)

        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)

        progress_label = QLabel("学习进度")
        progress_label.setStyleSheet("font-size: 14px; color: #666;")
        progress_layout.addWidget(progress_label)

        self.progress_bar = QWidget()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet("background-color: #e0e0e0; border-radius: 10px;")
        self.progress_inner = QWidget()
        self.progress_inner.setFixedWidth(0)
        self.progress_inner.setFixedHeight(20)
        self.progress_inner.setStyleSheet("background-color: #00A9BF; border-radius: 10px;")
        self.progress_inner.setObjectName("progressInner")

        progress_bar_layout = QVBoxLayout(self.progress_bar)
        progress_bar_layout.setContentsMargins(0, 0, 0, 0)
        progress_bar_layout.addWidget(self.progress_inner)

        self.progress_text = QLabel("0 / 0 (0%)")
        self.progress_text.setStyleSheet("font-size: 13px; color: #888;")
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_text)

        layout.addWidget(progress_container)

        log_container = QWidget()
        log_container.setMinimumHeight(200)
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(8)

        log_label = QLabel("运行日志")
        log_label.setStyleSheet("font-size: 14px; color: #666;")
        log_layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: none;
                border-radius: 6px;
                font-family: Consolas, monospace;
                font-size: 12px;
                padding: 10px;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 0px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: transparent;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_container)
        layout.addStretch()

    def _append_log(self, message: str):
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def log_message(self, message: str):
        self.log_signal.emit(message)

    def on_course_list_loaded(self, courses):
        self.courses = courses
        self.course_list_widget.clear()
        for course in courses:
            item = QListWidgetItem()
            course_info = QFrame()
            course_layout = QVBoxLayout(course_info)
            
            name_label = QLabel(f"{course.name}")
            name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
            course_layout.addWidget(name_label)
            
            info_label = QLabel(f"{course.teacher} | {course.school}")
            info_label.setStyleSheet("font-size: 12px; color: #666;")
            course_layout.addWidget(info_label)
            
            progress_label = QLabel(f"进度: {course.progress}%")
            progress_label.setStyleSheet("font-size: 12px; color: #00A9BF;")
            course_layout.addWidget(progress_label)
            
            if course.current_lesson:
                lesson_label = QLabel(f"当前: {course.current_lesson}")
                lesson_label.setStyleSheet("font-size: 11px; color: #888;")
                course_layout.addWidget(lesson_label)
            
            item.setSizeHint(course_info.sizeHint())
            self.course_list_widget.addItem(item)
            self.course_list_widget.setItemWidget(item, course_info)
        
        self.log_message(f"已加载 {len(courses)} 门课程")
        for i, course in enumerate(courses, 1):
            self.log_message(f"  {i}. {course.name} - 进度: {course.progress}%")

    def on_course_selected(self, item):
        index = self.course_list_widget.row(item)
        if index < len(self.courses):
            self.selected_course = self.courses[index]
            self.log_message(f"已选择课程: {self.selected_course.name}")

    def toggle_start(self):
        if not self.is_running:
            if not self.engine:
                self.log_message("错误: 引擎未初始化")
                return
            
            self.is_running = True
            self.start_btn.setText("停止")
            self.start_btn.setProperty("stopped", True)
            self.start_btn.style().unpolish(self.start_btn)
            self.start_btn.style().polish(self.start_btn)
            self.status_label.setText("运行中")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #00A9BF;
                    color: white;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
            self.log_message("正在启动浏览器...")
            self.engine.load_config()
            self.engine.start()
            
            QTimer.singleShot(3000, self.load_courses)
            
            if self.selected_course:
                QTimer.singleShot(5000, self.start_selected_course)
        else:
            if self.engine:
                self.engine.stop()
            self.is_running = False
            self.start_btn.setText("启动刷课")
            self.start_btn.setProperty("stopped", False)
            self.start_btn.style().unpolish(self.start_btn)
            self.start_btn.style().polish(self.start_btn)
            self.status_label.setText("已停止")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #ff6b6b;
                    color: white;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
            self.log_message("刷课程序已停止")

    def load_courses(self):
        if self.engine and self.engine.page:
            self.log_message("正在加载课程列表...")
            self.engine.load_courses()
        else:
            QTimer.singleShot(1000, self.load_courses)

    def start_selected_course(self):
        if self.selected_course and self.engine and self.engine.page:
            self.log_message(f"正在开始刷课: {self.selected_course.name}")
            self.engine.start_course(self.selected_course)
        else:
            QTimer.singleShot(1000, self.start_selected_course)

    def update_progress_bar(self, progress: int, course_name: str = "", video_name: str = ""):
        max_width = self.progress_bar.width()
        new_width = int(max_width * min(progress, 100) / 100)
        self.progress_inner.setFixedWidth(new_width)
        
        # 显示课程名称-视频名称和进度
        if course_name and video_name:
            display_text = f"{course_name} - {video_name}: {progress}%"
        elif course_name:
            display_text = f"{course_name}: {progress}%"
        else:
            display_text = f"进度: {progress}%"
        
        self.progress_text.setText(display_text)
        self.progress_text.setStyleSheet("font-size: 13px; color: #00A9BF; font-weight: bold;")
