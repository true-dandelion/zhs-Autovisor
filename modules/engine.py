import asyncio
import os
import threading
from typing import Callable, Optional, List, Dict
from dataclasses import dataclass

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from modules.configs import Config
from modules.logger import Logger
from modules.llq import BrowserMonitor
from modules.tasks import (
    video_optimize, play_video, skip_questions, 
    handle_ai_exercise, auto_next_video, task_monitor,
    check_progress_and_skip, set_progress_callback, wait_for_verify
)
from modules.utils import load_cookies
from modules.slider import slider_verify
# from modules.djym import click_verify


@dataclass
class Course:
    name: str
    teacher: str
    school: str
    progress: float
    current_lesson: str
    course_id: str
    recruit_id: str


class Engine:
    COURSE_LIST_URL = "https://onlineweb.zhihuishu.com/onlinestuh5"
    
    def __init__(self):
        self.config: Optional[Config] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._is_running = False
        self._is_loading_courses = False
        self._tasks: list = []
        self.event_loop_answer = asyncio.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._log_callback: Optional[Callable[[str], None]] = None
        self._course_list_callback: Optional[Callable[[List[Course]], None]] = None
        self._progress_callback: Optional[Callable[[str, str, int], None]] = None
        self._browser_closed_callback: Optional[Callable[[], None]] = None
        self._error_callback: Optional[Callable[[str], None]] = None
        
        self._state_lock = threading.Lock()
        self._reload_lock = threading.Lock()
        self._action_event = threading.Event()
        self._pending_actions: asyncio.Queue = None
        
        self._browser_close_registered = False
        self._page_close_registered = False
        
        self._is_entering_course = False
        self._is_reloading_courses = False
        self._is_waiting_login = False
        self._is_page_navigating = False
        self._is_brushing_course = False

        self._browser_monitor = BrowserMonitor(
            get_browser=lambda: self.browser,
            get_page=lambda: self.page,
            get_is_running=lambda: self.is_running,
            get_ui_running=lambda: self._ui_running if hasattr(self, '_ui_running') else None,
            log_callback=self._log
        )

    def set_ui_running_callback(self, get_ui_running: Callable[[], bool]):
        self._ui_running = get_ui_running

    def _get_is_running(self) -> bool:
        with self._state_lock:
            return self._is_running
    
    def _set_is_running(self, value: bool):
        with self._state_lock:
            self._is_running = value

    is_running = property(_get_is_running, _set_is_running)

    def _get_is_loading_courses(self) -> bool:
        with self._state_lock:
            return self._is_loading_courses
    
    def _set_is_loading_courses(self, value: bool):
        with self._state_lock:
            self._is_loading_courses = value

    is_loading_courses = property(_get_is_loading_courses, _set_is_loading_courses)

    def _get_is_entering_course(self) -> bool:
        with self._state_lock:
            return self._is_entering_course
    
    def _set_is_entering_course(self, value: bool):
        with self._state_lock:
            self._is_entering_course = value

    is_entering_course = property(_get_is_entering_course, _set_is_entering_course)

    def _get_is_reloading_courses(self) -> bool:
        with self._state_lock:
            return self._is_reloading_courses
    
    def _set_is_reloading_courses(self, value: bool):
        with self._state_lock:
            self._is_reloading_courses = value

    is_reloading_courses = property(_get_is_reloading_courses, _set_is_reloading_courses)

    def _get_is_waiting_login(self) -> bool:
        with self._state_lock:
            return self._is_waiting_login
    
    def _set_is_waiting_login(self, value: bool):
        with self._state_lock:
            self._is_waiting_login = value

    is_waiting_login = property(_get_is_waiting_login, _set_is_waiting_login)

    def _get_is_page_navigating(self) -> bool:
        with self._state_lock:
            return self._is_page_navigating
    
    def _set_is_page_navigating(self, value: bool):
        with self._state_lock:
            self._is_page_navigating = value

    is_page_navigating = property(_get_is_page_navigating, _set_is_page_navigating)

    def _get_is_brushing_course(self) -> bool:
        with self._state_lock:
            return self._is_brushing_course
    
    def _set_is_brushing_course(self, value: bool):
        with self._state_lock:
            self._is_brushing_course = value

    is_brushing_course = property(_get_is_brushing_course, _set_is_brushing_course)

    def set_log_callback(self, callback: Callable[[str], None]):
        self._log_callback = callback

    def set_course_list_callback(self, callback: Callable[[List[Course]], None]):
        self._course_list_callback = callback

    def set_progress_callback(self, callback: Callable[[str, str, int], None]):
        self._progress_callback = callback

    def set_browser_closed_callback(self, callback: Callable[[], None]):
        self._browser_closed_callback = callback
        self._browser_monitor.set_on_close_callback(callback)

    def set_error_callback(self, callback: Callable[[str], None]):
        self._error_callback = callback

    def _log(self, message: str):
        if self._log_callback:
            self._log_callback(message)
        print(message)

    def _on_browser_close(self):
        self.is_running = False
        self._log("浏览器已关闭")
        if self._browser_closed_callback:
            self._browser_closed_callback()

    def _on_logout_detected(self):
        if self.config and self.config.username and self.config.password:
            self._log("正在自动登录...")
            asyncio.create_task(self._auto_login())
        else:
            self._log("请登录后等待自动获取课程...")

    def _on_course_list_ready(self):
        asyncio.create_task(self._reload_courses())

    async def _reload_courses(self):
        if self.is_reloading_courses:
            return
        
        if self.is_entering_course:
            self._log("正在进入课程，暂不加载课程")
            return
        
        if self.is_page_navigating:
            self._log("页面正在导航中，暂不加载课程")
            return
        
        self.is_reloading_courses = True
        try:
            with self._reload_lock:
                self._log("开始加载课程...")
                courses = await self._async_load_courses()
                
                if self.is_waiting_login:
                    self._log("正在等待登录，暂不加载课程")
                    return
                
                if self._course_list_callback:
                    self._course_list_callback(courses)
                
                if not courses:
                    self._log("课程列表为空")
                    return
                
                self._log(f"加载到 {len(courses)} 门课程")
                
                unfinished_courses = [c for c in courses if c.progress < 100]
                
                if not unfinished_courses:
                    self._log("=" * 30)
                    self._log("课程已经全部刷满!")
                    self._log("=" * 30)
                    return
                
                target_course = unfinished_courses[0]
                self._log(f"自动选择课程: {target_course.name} (进度: {target_course.progress}%)")
                await self._async_start_course(target_course, courses)
        except Exception as e:
            self._log(f"_reload_courses 出错: {str(e)}")
        finally:
            self.is_reloading_courses = False

    def load_config(self, config_path: str = "configs.ini"):
        self.config = Config(config_path)
        self._log(f"配置已加载: {config_path}")

    async def _wait_for_login(self):
        self.is_waiting_login = True
        self._log("等待用户登录...")
        while self.is_running and self.page and not self.page.is_closed():
            try:
                await asyncio.sleep(3)
                if not self.is_running or not self.page:
                    self._log("浏览器已关闭，停止等待登录")
                    break
                
                if self.is_page_navigating:
                    self._log("页面正在导航中，跳过登录检查")
                    continue
                
                await self.page.wait_for_load_state("networkidle", timeout=5000)
                title = await self.page.title()
                if "学生首页" in title or "在线学堂" in title:
                    self._log(f"检测到已登录: {title}")
                    self._log("正在重新获取课程列表...")
                    courses = await self._async_load_courses()
                    if self._course_list_callback:
                        self._course_list_callback(courses)
                    
                    if not self.is_running or not self.page:
                        break
                    unfinished = [c for c in courses if c.progress < 100]
                    if unfinished:
                        target_course = unfinished[0]
                        self._log(f"自动开始刷课: {target_course.name} (进度: {target_course.progress}%)")
                        await self._async_start_course(target_course, courses)
                    return
                if "智慧树在线教育" in title:
                    if self.config and self.config.username and self.config.password:
                        self._log("正在自动登录...")
                        await self._auto_login()
                    continue
            except Exception:
                break
        self.is_waiting_login = False
        self._log("登录等待已退出")

    async def _auto_login(self):
        if not self.is_running or not self.page:
            self._log("浏览器已关闭，跳过自动登录")
            return
        
        try:
            await self.page.wait_for_load_state("networkidle", timeout=10000)
            await asyncio.sleep(1)
            
            username_selectors = [
                'input[name="username"]',
                'input[id="lUsername"]',
                'input[id="username"]',
                'input[type="text"]',
                'input[placeholder*="手机"]',
                'input[placeholder*="账号"]',
                '#account'
            ]
            
            password_selectors = [
                'input[name="password"]',
                'input[id="lPassword"]',
                'input[id="password"]',
                'input[type="password"]',
                '#password'
            ]
            
            btn_selectors = [
                'span.wall-sub-btn',
                '.wall-sub-btn',
                'button[type="submit"]',
                '.login-button',
                '.btn-login',
                '.login-btn',
                'button.login-btn',
                '#loginBtn',
                '.loginBtn',
                'a[id*="login"]',
                'button[id*="login"]',
                '.tab-item',
                '.btn.btn-primary',
                'input[type="submit"]',
                'button.submit',
                '.userLogin-btn'
            ]
            
            username_input = None
            for selector in username_selectors:
                username_input = await self.page.query_selector(selector)
                if username_input:
                    self._log(f"正在输入用户名")
                    await username_input.fill(self.config.username)
                    await asyncio.sleep(0.5)
                    break
            
            if not username_input:
                self._log("未找到输入用户名的地方")
                return
            
            password_input = None
            for selector in password_selectors:
                password_input = await self.page.query_selector(selector)
                if password_input:
                    self._log(f"正在输入密码")
                    await password_input.fill(self.config.password)
                    await asyncio.sleep(0.5)
                    break
            
            if not password_input:
                self._log("未找到输入密码的地方")
                return
            
            login_btn = None
            for selector in btn_selectors:
                login_btn = await self.page.query_selector(selector)
                if login_btn:
                    self._log(f"正在点击登录按钮")
                    await login_btn.click()
                    self._log("已点击登录按钮")
                    await asyncio.sleep(3)
                    return
            
            self._log("未找到点击登录按钮的地方")
                
        except Exception as e:
            self._log(f"自动登录失败: {str(e)}")

    async def _async_start(self):
        if not self.config:
            self.load_config()

        self._log("正在启动浏览器...")
        self.is_running = True
        
        playwright = await async_playwright().start()
        
        try:
            if self.config.driver == "edge":
                self.browser = await playwright.chromium.launch(
                    headless=self.config.enableHideWindow,
                    channel="msedge",
                    executable_path=self.config.exe_path if self.config.exe_path else None
                )
            elif self.config.driver == "chrome":
                self.browser = await playwright.chromium.launch(
                    headless=self.config.enableHideWindow,
                    channel="chrome",
                    executable_path=self.config.exe_path if self.config.exe_path else None
                )
            else:
                self.browser = await playwright.chromium.launch(
                    headless=self.config.enableHideWindow
                )
        except Exception as e:
            error_msg = str(e)
            self.is_running = False
            
            browser_name = "Edge" if self.config.driver == "edge" else "Chrome" if self.config.driver == "chrome" else "浏览器"
            
            if "not found" in error_msg.lower() or "chromium" in error_msg.lower():
                error_text = f"请检查{browser_name}是否已安装，或在配置中更换浏览器设置"
            else:
                error_text = f"浏览器启动失败: {error_msg}"
            
            if self._error_callback:
                self._error_callback(error_text)
            else:
                self._log(error_text)
            return

        if not self._browser_close_registered:
            self.browser.on("close", self._on_browser_close)
            self._browser_close_registered = True

        if not self.is_running:
            if self.browser:
                await self.browser.close()
            self._log("任务已停止，关闭浏览器")
            return

        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=self.config.headers["User-Agent"]
        )

        if self.config.soundOff:
            await self.context.add_init_script('''
                () => {
                    const originalCreate = document.createElement;
                    document.createElement = function(...args) {
                        const element = originalCreate.apply(document, args);
                        if (element.tagName === 'VIDEO') {
                            element.volume = 0;
                            element.muted = true;
                            
                            const observer = new MutationObserver(() => {
                                if (element.volume !== 0) {
                                    element.volume = 0;
                                }
                                if (!element.muted) {
                                    element.muted = true;
                                }
                            });
                            observer.observe(element, { attributes: true, attributeFilter: ['volume', 'muted'] });
                            
                            element.addEventListener('play', () => {
                                element.volume = 0;
                                element.muted = true;
                            });
                            
                            element.addEventListener('volumechange', () => {
                                if (element.volume !== 0) {
                                    element.volume = 0;
                                }
                                if (!element.muted) {
                                    element.muted = true;
                                }
                            });
                        }
                        return element;
                    };
                    
                    const observer = new MutationObserver((mutations) => {
                        mutations.forEach((mutation) => {
                            mutation.addedNodes.forEach((node) => {
                                if (node.nodeName === 'VIDEO' || (node.querySelectorAll && node.querySelectorAll('video').length > 0)) {
                                    const videos = node.nodeName === 'VIDEO' ? [node] : node.querySelectorAll('video');
                                    videos.forEach((video) => {
                                        video.volume = 0;
                                        video.muted = true;
                                    });
                                }
                            });
                        });
                    });
                    observer.observe(document.body, { childList: true, subtree: true });
                    
                    setInterval(() => {
                        const videos = document.querySelectorAll('video');
                        videos.forEach((video) => {
                            if (video.volume !== 0) {
                                video.volume = 0;
                            }
                            if (!video.muted) {
                                video.muted = true;
                            }
                        });
                    }, 1000);
                }
            ''')

        if not self.is_running:
            await self._cleanup_browser()
            self._log("任务已停止，关闭浏览器")
            return

        cookies = load_cookies()
        if cookies:
            await self.context.add_cookies(cookies)
            self._log("已加载保存的Cookies")

        self.page = await self.context.new_page()

        if not self.is_running:
            await self._cleanup_browser()
            self._log("任务已停止，关闭浏览器")
            return
        
        if not self._page_close_registered:
            self.page.on("close", self._on_browser_close)
            self._page_close_registered = True

        self._browser_monitor.set_on_logout_detected_callback(self._on_logout_detected)
        self._browser_monitor.set_on_course_list_ready_callback(self._on_course_list_ready)
        asyncio.create_task(self._browser_monitor._monitor_browser(
            lambda: self.is_entering_course,
            lambda: self.is_loading_courses,
            lambda: self.is_waiting_login,
            lambda: self.is_page_navigating,
            lambda: self.is_brushing_course
        ))
        self._log("[主流程] 浏览器监控任务已创建")
        
        self._log("正在打开课程列表页面...")
        try:
            await self.page.goto(self.COURSE_LIST_URL, wait_until="load", timeout=60000)
        except Exception as e:
            if not self.is_running:
                await self._cleanup_browser()
                self._log("任务已停止，关闭浏览器")
                return
            self._log(f"页面加载超时，正在重试...")
            await asyncio.sleep(5)
            if not self.is_running:
                await self._cleanup_browser()
                self._log("任务已停止，关闭浏览器")
                return
            try:
                await self.page.goto(self.COURSE_LIST_URL, wait_until="load", timeout=90000)
            except Exception as e2:
                if not self.is_running:
                    await self._cleanup_browser()
                    self._log("任务已停止，关闭浏览器")
                    return
                self._log(f"页面加载失败: {str(e2)}")
        
        if self.config.enableAutoCaptcha:
            if not self.is_running or not self.page:
                self._log("浏览器已关闭，跳过滑块验证")
            else:
                try:
                    import cv2
                    import numpy as np
                    await slider_verify(self.page, [np, cv2], self._log)
                except Exception as e:
                    self._log(f"滑块验证失败: {str(e)}")
        
        if not self.is_running or not self.page:
            self._log("浏览器已关闭，停止加载课程")
            return
        
        self._log("正在加载课程列表...")
        await asyncio.sleep(3)
        courses = await self._async_load_courses()
        self._log(f"[主流程] 课程加载完成，返回 {len(courses)} 门课程")
        if self._course_list_callback:
            self._course_list_callback(courses)

        unfinished = [c for c in courses if c.progress < 100]
        if unfinished:
            target_course = unfinished[0]
            self._log(f"[主流程] 自动开始刷课: {target_course.name} (进度: {target_course.progress}%)")
            await self._async_start_course(target_course, courses)
        else:
            self._log("[主流程] 没有未完成的课程")

    async def _async_load_courses(self):
        if not self.page:
            self._log("浏览器未启动")
            return []
        
        if not self.page or not self.is_running:
            self._log("浏览器未启动或已关闭")
            return []
        
        if self.is_page_navigating:
            self._log("页面正在导航中，暂不加载课程")
            return []
        
        if self.is_brushing_course:
            self._log("正在刷课中，暂不加载课程")
            return []
        
        self.is_loading_courses = True
        self._log("正在获取课程列表...")
        
        courses = []
        try:
            if not self.page or not self.is_running:
                self._log("浏览器已关闭，停止获取课程")
                return []
            await asyncio.sleep(2)
            await self.page.wait_for_load_state("networkidle", timeout=30000)
            
            # 检测是否在课程详情页
            current_video_count = await self.page.locator('.current_play').count()
            if current_video_count > 0:
                self._log("检测到当前在课程详情页，跳过课程列表获取")
                self.is_loading_courses = False
                return []
            
            title = await self.page.title()
            if "智慧树在线教育" in title:
                self._log(f"检测到未登录: {title}")
                self._log("等待页面自动跳转...")
                self.is_loading_courses = False
                asyncio.create_task(self._wait_for_login())
                return []
            else:
                self._log(f"检测到已登录: {title}")
            
            await self.page.wait_for_load_state("networkidle", timeout=10000)
            await asyncio.sleep(2)
            
            course_elements = await self.page.query_selector_all(".hoverList.interestingHoverList")
            self._log(f"找到 {len(course_elements)} 个课程元素")
            
            for element in course_elements:
                try:
                    name_elem = await element.query_selector(".courseName")
                    name = await name_elem.inner_text() if name_elem else ""
                    
                    teacher_elem = await element.query_selector(".teacherName span:first-child")
                    teacher = await teacher_elem.inner_text() if teacher_elem else ""
                    
                    school_elems = await element.query_selector_all(".teacherName span")
                    school = ""
                    if len(school_elems) >= 3:
                        school = await school_elems[2].inner_text()
                    
                    progress_elem = await element.query_selector(".processNum")
                    progress_text = await progress_elem.inner_text() if progress_elem else "0%"
                    progress = float(progress_text.replace("%", ""))
                    
                    current_elem = await element.query_selector(".nowCourse .name")
                    current_lesson = await current_elem.inner_text() if current_elem else ""
                    
                    link_elem = await element.query_selector(".right-item-course a[href*='recruitId']")
                    href = await link_elem.get_attribute("href") if link_elem else ""
                    
                    recruit_id = ""
                    course_id = ""
                    if "recruitId=" in href:
                        import re
                        match = re.search(r'recruitId=(\d+)', href)
                        if match:
                            recruit_id = match.group(1)
                    if "courseId=" in href:
                        match = re.search(r'courseId=(\d+)', href)
                        if match:
                            course_id = match.group(1)
                    
                    self._log(f"解析课程: {name}, 进度: {progress}%, recruitId: {recruit_id}, courseId: {course_id}")
                    
                    course = Course(
                        name=name.strip(),
                        teacher=teacher.strip(),
                        school=school.strip(),
                        progress=progress,
                        current_lesson=current_lesson.strip(),
                        course_id=course_id,
                        recruit_id=recruit_id
                    )
                    courses.append(course)
                    
                except Exception as e:
                    self._log(f"解析课程信息失败: {str(e)}")
                    continue
            
            self._log(f"共获取到 {len(courses)} 门课程")
            self._log("课程获取结束")
            
        except Exception as e:
            self._log(f"获取课程列表失败: {str(e)}")
        
        self.is_loading_courses = False
        return courses

    def _schedule_coroutine(self, coro):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, self._loop)
        else:
            self._log("事件循环未运行")

    def load_courses(self):
        if not self.page:
            self._log("浏览器未启动，请先启动浏览器")
            return []
        
        if self.is_loading_courses:
            self._log("正在加载课程中...")
            return []

        async def run():
            courses = await self._async_load_courses()
            if self._course_list_callback:
                self._course_list_callback(courses)
            return courses
        
        self._schedule_coroutine(run())
        return []

    async def _wait_for_video_completion(self):
        """等待当前视频完成"""
        from modules.progress import get_course_progress, show_course_progress
        
        # 获取课程名称和视频名称
        course_name = ""
        video_name = ""
        try:
            current_video = await self.page.query_selector(".current_play")
            if current_video:
                title_elem = await current_video.query_selector(".catalogue_title")
                chapter_elem = await current_video.query_selector(".hour")
                if title_elem:
                    video_name = await title_elem.inner_text()
                if chapter_elem:
                    video_chapter = await chapter_elem.inner_text()
                course_name = f"[{video_chapter}] {video_name}" if video_name and video_chapter else "未知课程"
        except Exception as e:
            self._log(f"获取课程名称失败: {str(e)}")
            course_name = "未知课程"
        
        # 检测页面类型
        has_progress_num = await self.page.locator(".progress-num").count() > 0
        is_new_version = has_progress_num
        
        # 等待视频完成
        while True:
            try:
                # 检查浏览器是否已关闭
                if self.page.is_closed():
                    self._log("浏览器已关闭，停止等待视频完成")
                    return
                
                cur_time = await get_course_progress(self.page, is_new_version, False)
                show_course_progress(desc="完成进度:", cur_time=cur_time, is_new_version=is_new_version, course_name=course_name)
                
                # 调用UI进度回调
                if self._progress_callback:
                    progress_percent = 0
                    if cur_time and cur_time != '':
                        try:
                            progress_percent = int(cur_time.replace('%', ''))
                        except:
                            progress_percent = 0
                    self._progress_callback(course_name, video_name, progress_percent)
                
                if cur_time == "100%":
                    self._log(f"视频 {course_name} 已完成")
                    break
                    
                await asyncio.sleep(0.5)
                
            except Exception as e:
                # 检查是否是浏览器关闭错误
                if "closed" in str(e).lower():
                    self._log(f"浏览器已关闭，停止等待视频完成: {str(e)}")
                    return
                self._log(f"等待视频完成时出错: {str(e)}")
                await asyncio.sleep(1)

    async def _start_brushing(self, course: Course):
        try:
            await self.page.wait_for_selector(".clearfix.video", state="attached", timeout=10000)
            from modules.utils import get_filtered_class
            
            # 检测页面类型：是否存在.progress-num元素
            has_progress_num = await self.page.locator(".progress-num").count() > 0
            is_new_version = has_progress_num
            
            unfinished_videos = await get_filtered_class(self.page, is_new_version=is_new_version, is_hike_class=False, include_all=False)
            
            if not unfinished_videos:
                self._log("当前课程所有视频都已完成，返回课程列表...")
                self.is_page_navigating = True
                await self.page.goto(self.COURSE_LIST_URL, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(3)
                
                self._log("正在重新加载课程列表...")
                self.is_page_navigating = False
                current_courses = await self._async_load_courses()
                
                if current_courses:
                    current_course_index = -1
                    for i, c in enumerate(current_courses):
                        if c.course_id == course.course_id:
                            current_course_index = i
                            break
                    
                    if current_course_index >= 0 and current_course_index + 1 < len(current_courses):
                        next_course = current_courses[current_course_index + 1]
                        self._log(f"继续刷下一门课程（第{current_course_index + 2}个）: {next_course.name} (进度: {next_course.progress}%)")
                        await self._async_start_course(next_course, current_courses)
                    else:
                        self._log("=" * 30)
                        self._log("所有课程已经全部刷满!")
                        self._log("=" * 30)
                        self.is_running = False
                        self.is_entering_course = False
                return
            else:
                self._log(f"找到 {len(unfinished_videos)} 个未完成视频，开始刷课...")
                
                # 启动后台任务
                self._tasks = [
                    asyncio.create_task(video_optimize(self.page, self.config)),
                    asyncio.create_task(play_video(self.page)),
                    asyncio.create_task(skip_questions(self.page, self.event_loop_answer)),
                    asyncio.create_task(handle_ai_exercise(self.page)),
                    asyncio.create_task(wait_for_verify(self.page, self.config, self.event_loop_answer)),
                ]
                
                self.is_running = True
                self._log("刷课任务已启动!")
                
                # 使用索引递增的方式处理视频
                cur_index = 0
                while True:
                    # 每次循环重新获取未完成视频列表，因为DOM会变化
                    from modules.utils import get_filtered_class
                    current_unfinished = await get_filtered_class(self.page, is_new_version=is_new_version, is_hike_class=False, include_all=False)
                    
                    if not current_unfinished:
                        self._log("所有视频都已完成")
                        break
                    
                    if cur_index >= len(current_unfinished):
                        self._log("已处理完所有未完成视频")
                        break
                    
                    self._log(f"正在处理第 {cur_index+1}/{len(current_unfinished)} 个未完成视频")
                    
                    # 检查浏览器是否已关闭
                    if self.page.is_closed():
                        self._log("浏览器已关闭，停止刷课")
                        break
                    
                    # 检查并关闭弹题对话框
                    try:
                        dialog = await self.page.query_selector("#playTopic-dialog")
                        if dialog:
                            self._log("检测到弹题对话框，正在关闭...")
                            # 尝试点击关闭按钮
                            close_btn = await self.page.query_selector(".el-dialog__headerbtn")
                            if close_btn:
                                await close_btn.click(timeout=3000)
                                self._log("已通过关闭按钮关闭弹题对话框")
                                await asyncio.sleep(1)
                            else:
                                # 如果关闭按钮不可用，尝试按ESC键
                                await self.page.keyboard.press("Escape")
                                self._log("已通过ESC键关闭弹题对话框")
                                await asyncio.sleep(1)
                    except Exception as e:
                        self._log(f"关闭弹题对话框时出错: {str(e)}")
                    
                    # 点击当前视频
                    await current_unfinished[cur_index].click()
                    await self.page.wait_for_selector(".current_play", state="attached", timeout=10000)
                    await asyncio.sleep(1)
                    
                    # 再次检查浏览器是否已关闭
                    if self.page.is_closed():
                        self._log("浏览器已关闭，停止刷课")
                        break
                    
                    # 切换视频后重新设置静音
                    if self.config.soundOff:
                        await self.page.wait_for_selector("video", state="attached", timeout=5000)
                        await self.page.evaluate(self.config.volume_none)
                        await self.page.evaluate(self.config.set_none_icon)
                        self._log("已将音量设置为静音")
                    
                    # 检查浏览器是否已关闭
                    if self.page.is_closed():
                        self._log("浏览器已关闭，停止刷课")
                        break
                    
                    # 检查是否存在验证码弹窗
                    modal_count = await self.page.locator('.yidun_modal').count()
                    if modal_count > 0:
                        self._log("检测到验证码弹窗")
                        
                        # 检测验证码类型
                        bg_exists = await self.page.locator('.yidun_bg-img').count() > 0
                        inference_exists = await self.page.locator('.yidun_inference').count() > 0
                        
                        # if self.config.enableAutoClickCaptcha and inference_exists:
                        #     self._log("检测到点击验证，正在自动处理...")
                        #     if self.config.enableHideWindow:
                        #         from modules.tasks import display_window
                        #         await display_window(self.page)
                        #     try:
                        #         import cv2
                        #         import numpy as np
                        #         await click_verify(self.page, [np, cv2], lambda msg: self._log(msg))
                        #         if self.config.enableHideWindow:
                        #             from modules.tasks import hide_window
                        #             await hide_window(self.page)
                        #         self._log("点击验证已完成")
                        #     except Exception as e:
                        #         self._log(f"自动点击验证失败: {str(e)},请手动完成验证...")
                        #         if self.config.enableHideWindow:
                        #             from modules.tasks import display_window
                        #             await display_window(self.page)
                        #         await self.page.wait_for_selector(".yidun_modal", state="hidden", timeout=24 * 3600 * 1000)
                        #         if self.config.enableHideWindow:
                        #             from modules.tasks import hide_window
                        #             await hide_window(self.page)
                        #         self._log("安全验证已完成")
                        # else:
                        self._log("检测到安全验证，等待手动完成...")
                        if self.config.enableHideWindow:
                            from modules.tasks import display_window
                            await display_window(self.page)
                        await self.page.wait_for_selector(".yidun_modal", state="hidden", timeout=24 * 3600 * 1000)
                        if self.config.enableHideWindow:
                            from modules.tasks import hide_window
                            await hide_window(self.page)
                        self._log("安全验证已完成")
                        
                        await asyncio.sleep(2)
                    
                    # 获取视频信息
                    current_video = await self.page.query_selector(".current_play")
                    if current_video:
                        title_elem = await current_video.query_selector(".catalogue_title")
                        time_elem = await current_video.query_selector(".time")
                        chapter_elem = await current_video.query_selector(".hour")
                        finish_icon = await current_video.query_selector(".time_icofinish")

                        video_title = await title_elem.inner_text() if title_elem else "未知"
                        video_time = await time_elem.inner_text() if time_elem else "未知"
                        video_chapter = await chapter_elem.inner_text() if chapter_elem else "未知"
                        is_finished = "已完成" if finish_icon else "未完成"

                        self._log(f"当前视频: [{video_chapter}] {video_title} | 时长: {video_time} | 状态: {is_finished}")
                    
                    # 等待视频完成
                    await self._wait_for_video_completion()
                    
                    # 检查浏览器是否已关闭
                    if self.page.is_closed():
                        self._log("浏览器已关闭，停止刷课")
                        break
                    
                    # 检查当前视频是否有 "current_play" 类，如果有则索引+1
                    try:
                        if cur_index < len(current_unfinished):
                            if "current_play" in await current_unfinished[cur_index].get_attribute('class'):
                                cur_index += 1
                                self._log(f"第 {cur_index}/{len(current_unfinished)} 个视频已完成，跳转到下一个视频")
                    except Exception as e:
                        if "closed" in str(e).lower():
                            self._log("浏览器已关闭，停止刷课")
                            break
                        raise
                
                # 停止后台任务
                for task in self._tasks:
                    if not task.done():
                        task.cancel()
                
                self._log("所有未完成视频已处理完毕")
        except Exception as e:
            self._log(f"刷课过程中出错: {str(e)}")
            self.is_brushing_course = False

    async def _async_start_course(self, course: Course, all_courses: List[Course] = None):
        if not self.page:
            self._log("浏览器未启动")
            return
        
        self.is_entering_course = True
        self.is_page_navigating = True
        self._log(f"正在进入课程: {course.name}")
        
        try:
            await self.page.wait_for_load_state("networkidle", timeout=60000)
            
            # 检查当前页面URL，如果已经在课程详情页，直接开始刷课
            current_url = self.page.url
            if "courseDetail" in current_url or "recruitdetail" in current_url:
                self._log("检测到已在课程详情页，直接开始刷课")
                self.is_entering_course = False
                self.is_page_navigating = False
                self.is_brushing_course = True
                if self._progress_callback:
                    set_progress_callback(self._progress_callback)
                self._log("正在检查课程中的未完成视频...")
                await self._start_brushing(course)
                return
            
            self._log("正在点击课程元素...")
            
            course_items = await self.page.query_selector_all(".item-left-course")
            self._log(f"找到 {len(course_items)} 个课程项")
            
            target_element = None
            
            for i, item in enumerate(course_items):
                try:
                    self._log(f"  正在检查第{i+1}个课程项...")
                    name_elem = await item.query_selector(".courseName")
                    if name_elem:
                        text = await name_elem.inner_text()
                        self._log(f"  第{i+1}个课程: {text}")
                        if course.name in text:
                            target_element = item
                            self._log(f"匹配到目标课程: {text}")
                            break
                    else:
                        self._log(f"  第{i+1}个课程未找到课程名称元素")
                except Exception as e:
                    self._log(f"  第{i+1}个课程解析失败: {str(e)}")
                    self._log(f"  错误类型: {type(e).__name__}")
                    continue
            
            if target_element:
                self._log(f"匹配到目标课程，准备点击")
                await asyncio.sleep(1)
                self._log(f"点击课程: {course.name}")
                await asyncio.sleep(1)
                await target_element.click()
                self._log("等待页面跳转...")
                
                try:
                    await asyncio.sleep(3)
                    await self.page.wait_for_load_state("networkidle", timeout=60000)
                    self._log("页面跳转完成")
                except Exception as e:
                    self._log(f"等待页面跳转超时: {str(e)}")
                
                self.is_page_navigating = False
                
                # 检查浏览器是否已关闭
                if self.page.is_closed():
                    self._log("浏览器已关闭，停止进入课程")
                    self.is_entering_course = False
                    return
                
                # 检查是否存在验证码弹窗
                await asyncio.sleep(2)
                modal_count = await self.page.locator('.yidun_modal').count()
                if modal_count > 0:
                    self._log("检测到验证码弹窗")
                    
                    # 检测验证码类型
                    bg_exists = await self.page.locator('.yidun_bg-img').count() > 0
                    inference_exists = await self.page.locator('.yidun_inference').count() > 0
                    
                    # if self.config.enableAutoClickCaptcha and inference_exists:
                    #     self._log("检测到点击验证，正在自动处理...")
                    #     if self.config.enableHideWindow:
                    #         from modules.tasks import display_window
                    #         await display_window(self.page)
                    #     try:
                    #         import cv2
                    #         import numpy as np
                    #         await click_verify(self.page, [np, cv2], lambda msg: self._log(msg))
                    #         if self.config.enableHideWindow:
                    #             from modules.tasks import hide_window
                    #             await hide_window(self.page)
                    #         self._log("点击验证已完成")
                    #     except Exception as e:
                    #         self._log(f"自动点击验证失败: {str(e)},请手动完成验证...")
                    #         if self.config.enableHideWindow:
                    #             from modules.tasks import display_window
                    #             await display_window(self.page)
                    #         await self.page.wait_for_selector(".yidun_modal", state="hidden", timeout=24 * 3600 * 1000)
                    #         if self.config.enableHideWindow:
                    #             from modules.tasks import hide_window
                    #             await hide_window(self.page)
                    #         self._log("安全验证已完成")
                    # else:
                    self._log("检测到安全验证，等待手动完成...")
                    if self.config.enableHideWindow:
                        from modules.tasks import display_window
                        await display_window(self.page)
                    await self.page.wait_for_selector(".yidun_modal", state="hidden", timeout=24 * 3600 * 1000)
                    if self.config.enableHideWindow:
                        from modules.tasks import hide_window
                        await hide_window(self.page)
                    self._log("安全验证已完成")
                    
                    await asyncio.sleep(2)
                
                # 页面已跳转，开始刷课
                self._log("页面已跳转，准备获取视频信息")
                self.is_entering_course = False
                self.is_brushing_course = True
                if self._progress_callback:
                    set_progress_callback(self._progress_callback)
                self._log("正在检查课程中的未完成视频...")
                await self._start_brushing(course)
                return
            else:
                self._log("未找到课程元素，无法进入课程")
                self.is_entering_course = False
                return

        except Exception as e:
            self._log(f"进入课程失败: {str(e)}")
            self.is_entering_course = False
            self.is_page_navigating = False

    def start_course(self, course: Course, all_courses: List[Course] = None):
        if self.is_running:
            self._log("任务已在运行中")
            return

        self.is_entering_course = True

        async def run():
            await self._async_start_course(course, all_courses)
        
        self._schedule_coroutine(run())

    def _run_async(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        async def main():
            await self._async_start()
        
        self._loop.run_until_complete(main())
        self._loop = None

    def start(self):
        if self.is_running:
            self._log("任务已在运行中")
            return
        
        if self._thread and self._thread.is_alive():
            self._log("任务启动中，请稍后...")
            return

        self._thread = threading.Thread(target=self._run_async, daemon=True)
        self._thread.start()

    async def _cleanup_browser(self):
        if self.page:
            try:
                await self.page.close()
            except Exception:
                pass
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass

    async def _async_stop(self):
        self.is_running = False
        
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        if self.page:
            try:
                await self.page.close()
            except Exception:
                pass
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
        
        self._log("浏览器已关闭")

    def stop(self):
        if not self.is_running:
            return

        self._log("正在停止任务...")
        self.is_running = False

        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_stop(), self._loop)

    def save_cookies(self):
        if self.context:
            try:
                async def get_cookies():
                    return await self.context.cookies()
                
                if self._loop and self._loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(get_cookies(), self._loop)
                    cookies = future.result(timeout=10)
                else:
                    cookies = asyncio.run(get_cookies())
                
                import json
                with open("cookies.json", "w") as f:
                    json.dump(cookies, f)
                self._log("Cookies已保存")
            except Exception as e:
                self._log(f"保存Cookies失败: {str(e)}")
