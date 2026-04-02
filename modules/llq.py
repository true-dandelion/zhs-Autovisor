import asyncio
from typing import Callable, Optional
from playwright.async_api import Browser, BrowserContext, Page


class BrowserMonitor:
    def __init__(
        self,
        get_browser: Callable[[], Optional[Browser]],
        get_page: Callable[[], Optional[Page]],
        get_is_running: Callable[[], bool],
        get_ui_running: Optional[Callable[[], bool]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ):
        self._get_browser = get_browser
        self._get_page = get_page
        self._get_is_running = get_is_running
        self._get_ui_running = get_ui_running
        self._log_callback = log_callback
        self._on_close_callback: Optional[Callable[[], None]] = None
        self._on_login_detected_callback: Optional[Callable[[], None]] = None
        self._on_logout_detected_callback: Optional[Callable[[], None]] = None
        self._on_course_list_ready_callback: Optional[Callable[[], None]] = None
        self._on_close_by_ui_callback: Optional[Callable[[], None]] = None
        self._ui_requested_close = False

    def set_on_close_callback(self, callback: Callable[[], None]):
        self._on_close_callback = callback

    def set_on_login_detected_callback(self, callback: Callable[[], None]):
        self._on_login_detected_callback = callback

    def set_on_logout_detected_callback(self, callback: Callable[[], None]):
        self._on_logout_detected_callback = callback

    def set_on_course_list_ready_callback(self, callback: Callable[[], None]):
        self._on_course_list_ready_callback = callback

    def set_on_close_by_ui_callback(self, callback: Callable[[], None]):
        self._on_close_by_ui_callback = callback

    def request_close_by_ui(self):
        self._ui_requested_close = True
        if self._on_close_by_ui_callback:
            self._on_close_by_ui_callback()

    def _log(self, message: str):
        if self._log_callback:
            self._log_callback(message)
        print(message)

    async def _monitor_browser(self, is_entering_course, is_loading_courses, is_waiting_login, is_page_navigating, is_brushing_course=None):
        self._log("[监控] 浏览器监控任务已启动")
        last_title = ""
        last_loaded_title = ""

        while self._get_is_running():
            if self._get_ui_running and not self._get_ui_running():
                self._log("[监控] UI已停止，关闭浏览器监控")
                self._on_browser_close()
                break

            await asyncio.sleep(2)
            page = self._get_page()
            browser = self._get_browser()

            try:
                if page and page.is_closed():
                    self._log("[监控] 检测到页面已关闭")
                    self._on_browser_close()
                    break
            except Exception:
                pass

            try:
                if browser and not browser.is_connected():
                    self._log("[监控] 检测到浏览器已断开连接")
                    self._on_browser_close()
                    break
            except Exception:
                pass

            if page and not page.is_closed():
                try:
                    await page.wait_for_load_state("networkidle", timeout=5000)
                    title = await page.title()
                except Exception:
                    await asyncio.sleep(1)
                    try:
                        title = await page.title()
                    except Exception:
                        continue

                if title != last_title:
                    last_title = title

                    if not is_entering_course() and not is_page_navigating():
                        self._log(f"当前页面: {title}")

                    if is_entering_course() or is_page_navigating() or (is_brushing_course and is_brushing_course()):
                        pass
                    elif "智慧树在线教育" in title:
                        if not is_loading_courses() and not is_waiting_login():
                            self._log(f"检测到未登录: {title}")
                            if self._on_logout_detected_callback:
                                self._on_logout_detected_callback()
                    elif "学生首页_在线学堂_智慧树" in title:
                        if last_loaded_title != title and not is_entering_course() and not is_page_navigating() and not (is_brushing_course and is_brushing_course()):
                            self._log(f"检测到已登录: {title}")
                            self._log("正在获取课程列表...")
                            last_loaded_title = title
                            if self._on_course_list_ready_callback:
                                self._on_course_list_ready_callback()

    def _on_browser_close(self):
        if self._on_close_callback:
            self._on_close_callback()