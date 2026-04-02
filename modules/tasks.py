import asyncio
import traceback

from playwright.async_api import Page
from pygetwindow import Win32Window
from modules.configs import Config
from modules.utils import get_video_attr, display_window, hide_window
from playwright._impl._errors import TargetClosedError
from modules.logger import Logger
from modules.djym import click_verify
from typing import Callable, Optional

logger = Logger()

_progress_callback: Optional[Callable[[str, float], None]] = None

def set_progress_callback(callback: Callable[[str, str, int], None]):
    global _progress_callback
    _progress_callback = callback

def _report_progress(class_name: str, progress: float):
    pass  # 不再使用此函数，直接在 engine.py 中调用回调


async def task_monitor(tasks: list[asyncio.Task]) -> None:
    checked_tasks = set()
    logger.info("任务监控已启动.")
    while any(not task.done() for task in tasks):
        for i, task in enumerate(tasks):
            if task.done() and task not in checked_tasks:
                checked_tasks.add(task)
                exc = task.exception()
                func_name = task.get_coro().__name__
                logger.error(f"任务函数{func_name} 出现异常.", shift=True)
                logger.write_log(exc)
        await asyncio.sleep(1)
    logger.info("任务监控已退出.", shift=True)


async def activate_window(window: Win32Window) -> None:
    while True:
        try:
            await asyncio.sleep(2)
            if window and window.isMinimized:
                window.moveTo(-3200, -3200)
                await asyncio.sleep(0.3)
                window.restore()
                logger.info("检测到播放窗口最小化,已自动恢复.")
        except TargetClosedError:
            logger.write_log("浏览器已关闭,窗口激活模块已下线.\n")
            return
        except Exception as e:
            continue


async def video_optimize(page: Page, config: Config) -> None:
    from modules.progress import close_pre_study_popup
    await page.wait_for_load_state("networkidle")
    await close_pre_study_popup(page)
    
    if config.soundOff:
        await page.wait_for_selector("video", state="attached", timeout=5000)
        await page.evaluate(config.volume_none)
        await page.evaluate(config.set_none_icon)
    
    while True:
        try:
            if page.is_closed():
                logger.write_log("浏览器已关闭,视频调节模块已下线.\n")
                return
            await asyncio.sleep(0.5)
            await close_pre_study_popup(page)
            await page.wait_for_selector("video", state="attached", timeout=3000)
            volume = await get_video_attr(page, "volume")
            muted = await get_video_attr(page, "muted")
            rate = await get_video_attr(page, "playbackRate")
            if config.soundOff:
                if volume != 0 or not muted:
                    await page.evaluate(config.volume_none)
                    await page.evaluate(config.set_none_icon)
                    await page.evaluate("document.querySelector('video').muted = true;")
                    logger.info("已将音量设置为静音")
            if rate != config.limitSpeed:
                await page.evaluate(config.revise_speed)
                await page.evaluate(config.revise_speed_name)
        except TargetClosedError:
            logger.write_log("浏览器已关闭,视频调节模块已下线.\n")
            return
        except Exception as e:
            continue


async def play_video(page: Page) -> None:
    await page.wait_for_load_state("networkidle")
    while True:
        try:
            if page.is_closed():
                logger.write_log("浏览器已关闭,视频播放模块已下线.\n")
                return
            await asyncio.sleep(2)
            await page.wait_for_selector("video", state="attached", timeout=1000)
            paused = await page.evaluate("document.querySelector('video').paused")
            if paused:
                await page.wait_for_selector(".videoArea", timeout=1000)
                await page.evaluate('document.querySelector("video").play();')
                logger.write_log("视频已恢复播放.\n")
        except TargetClosedError:
            logger.write_log("浏览器已关闭,视频播放模块已下线.\n")
            return
        except Exception as e:
            continue


async def skip_questions(page: Page, event_loop) -> None:
    await page.wait_for_load_state("networkidle")
    while True:
        try:
            if page.is_closed():
                logger.write_log("浏览器已关闭,答题模块已下线.\n")
                return
            if "hike.zhihuishu.com" in page.url:
                logger.warn("当前课程为新版本,不支持自动答题.", shift=True)
                return
            await asyncio.sleep(2)
            ques_element = await page.wait_for_selector(".el-scrollbar__view", state="attached", timeout=1000)
            total_ques = await ques_element.query_selector_all(".number")
            if total_ques:
                logger.write_log(f"检测到{len(total_ques)}道题目.\n")
            for ques in total_ques:
                await ques.click(timeout=500)
                if not await page.query_selector(".answer"):
                    choices = await page.query_selector_all(".topic-item")
                    for each in choices[:2]:
                        await each.click(timeout=500)
                        await page.wait_for_timeout(100)
            await page.press(".el-dialog", "Escape", timeout=1000)
            event_loop.set()
        except TargetClosedError:
            logger.write_log("浏览器已关闭,答题模块已下线.\n")
            return
        except Exception as e:
            if "fusioncourseh5" in page.url:
                not_finish_close = await page.query_selector(".el-dialog")
                if not_finish_close:
                    await page.press(".el-dialog", "Escape", timeout=1000)
            elif "hike.zhihuishu.com" in page.url:
                logger.warn("当前课程为新版本,不支持自动答题.", shift=True)
                return
            else:
                not_finish_close = await page.query_selector(".el-message-box__headerbtn")
                if not_finish_close:
                    await not_finish_close.click()
            continue


async def handle_ai_exercise(page: Page) -> None:
    """处理AI随堂练习弹窗，自动选择选项A并关闭弹窗"""
    await page.wait_for_load_state("networkidle")
    while True:
        try:
            if page.is_closed():
                logger.write_log("浏览器已关闭,AI随堂练习处理模块已下线.\n")
                return
            await asyncio.sleep(2)
            # 检查是否存在AI随堂练习弹窗
            ai_exercise_header = await page.query_selector(".header-box")
            if ai_exercise_header:
                # 验证是否包含"AI随堂练习"文本
                header_text = await ai_exercise_header.inner_text()
                if "AI随堂练习" in header_text:
                    logger.info("检测到AI随堂练习弹窗,正在自动答题...")
                    
                    # 查找题目区域
                    question_body = await page.query_selector(".question-body")
                    if question_body:
                        # 查找选项A并点击
                        option_a = await page.query_selector(".option:has(.class-question-select:has-text('A'))")
                        if option_a:
                            await option_a.click(timeout=1000)
                            logger.info("已选择选项A")
                        
                        # 查找并点击提交按钮
                        submit_button = await page.query_selector(".submit-btn")
                        if submit_button:
                            await submit_button.click(timeout=1000)
                            logger.info("已提交答案")
                            await asyncio.sleep(1)  # 等待提交完成
                    
                    # 点击关闭按钮关闭弹窗
                    close_button = await page.query_selector(".close-box")
                    if close_button:
                        await close_button.click(timeout=1000)
                        logger.info("已关闭AI随堂练习弹窗")
                    
                    # 短暂暂停以避免重复处理同一弹窗
                    await asyncio.sleep(3)
        except TargetClosedError:
            logger.write_log("浏览器已关闭,AI随堂练习处理模块已下线.\n")
            return
        except Exception as e:
            continue


async def find_next_chapter_by_number(page: Page, current_chapter: str) -> bool:
    """
    根据当前章节号（如"4.3.1"）在目录中找到下一个可点击的章节并跳转
    
    Args:
        page: Playwright页面对象
        current_chapter: 当前章节号，如"4.3.1"
    
    Returns:
        bool: 是否成功找到并跳转到下一个章节
    """
    try:
        # 解析当前章节号，获取数字部分
        import re
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', current_chapter)
        if not match:
            logger.info(f"无法解析章节号格式: {current_chapter}")
            return False
            
        major, minor, patch = map(int, match.groups())
        
        # 获取所有可点击的章节项
        all_items = page.locator(".child-info.hasvideo")
        items_count = await all_items.count()
        
        logger.info(f"📋 查找章节项，共找到 {items_count} 个可点击的章节")
        
        if items_count == 0:
            logger.info("❌ 未找到任何可点击的章节")
            return False
            
        # 遍历所有章节，查找当前章节和下一个章节
        current_item_index = -1
        next_item_index = -1
        current_item_text = ""
        next_item_text = ""
        
        # 收集所有章节信息
        chapter_info = []
        logger.info("📖 开始收集章节信息...")
        
        for i in range(items_count):
            item = all_items.nth(i)
            name_el = item.locator(".child-name").first
            if await name_el.count() > 0:
                try:
                    text = await name_el.text_content()
                except Exception:
                    text = None
                if text:
                    # 提取章节号
                    chapter_match = re.search(r'(\d+\.\d+\.\d+)', text)
                    chapter_num = None
                    
                    # 如果从文本中提取不到章节号，尝试从span元素中提取
                    if not chapter_match:
                        try:
                            # 尝试在当前项中查找带有data-v-0f2d8e04属性的span元素
                            span_el = item.locator("span[data-v-0f2d8e04]").first
                            if await span_el.count() > 0:
                                span_text = await span_el.text_content()
                                if span_text:
                                    span_match = re.search(r'(\d+\.\d+\.\d+)', span_text)
                                    if span_match:
                                        chapter_num = span_match.group(1)
                        except Exception:
                            pass
                    
                    # 如果从span元素中也提取不到，使用文本中的章节号
                    if not chapter_num and chapter_match:
                        chapter_num = chapter_match.group(1)
                    
                    # 如果成功提取到章节号，添加到章节信息列表
                    if chapter_num:
                        chapter_info.append({
                            'index': i,
                            'text': text,
                            'chapter_num': chapter_num,
                            'item': item
                        })
                        logger.info(f"  📝 找到章节 {chapter_num}: {text}")
        
        logger.info(f"📊 共收集到 {len(chapter_info)} 个有效章节")
        
        # 查找当前章节
        for info in chapter_info:
            if info['chapter_num'] == current_chapter:
                current_item_index = info['index']
                current_item_text = info['text']
                logger.info(f"📍 定位到当前章节: {info['chapter_num']} - {info['text']}")
                break
                
        # 如果没有找到当前章节，尝试查找最接近的章节
        if current_item_index == -1:
            logger.info(f"未找到当前章节 {current_chapter}，尝试查找最接近的章节")
            # 查找最接近的章节
            closest_diff = float('inf')
            closest_index = -1
            
            for info in chapter_info:
                chapter_match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', info['chapter_num'])
                if chapter_match:
                    item_major, item_minor, item_patch = map(int, chapter_match.groups())
                    # 计算与当前章节的差值
                    diff = abs((item_major - major) * 100 + (item_minor - minor) * 10 + (item_patch - patch))
                    if diff < closest_diff:
                        closest_diff = diff
                        closest_index = info['index']
                        current_item_text = info['text']
            
            if closest_index >= 0:
                current_item_index = closest_index
                logger.info(f"找到最接近的章节: {chapter_info[closest_index]['text']}")
        
        # 查找下一个章节
        if current_item_index >= 0:
            # 首先尝试找到章节号比当前大的下一个章节
            for info in chapter_info:
                if info['index'] > current_item_index:
                    chapter_match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', info['chapter_num'])
                    if chapter_match:
                        item_major, item_minor, item_patch = map(int, chapter_match.groups())
                        # 如果章节号比当前大，则选择为下一个章节
                        if (item_major > major or 
                            (item_major == major and item_minor > minor) or
                            (item_major == major and item_minor == minor and item_patch > patch)):
                            next_item_index = info['index']
                            next_item_text = info['text']
                            break
            
            # 如果没有找到章节号更大的，则选择列表中的下一个
            if next_item_index == -1:
                for i, info in enumerate(chapter_info):
                    if info['index'] > current_item_index:
                        next_item_index = info['index']
                        next_item_text = info['text']
                        break
        
        # 如果找到了下一个章节，则点击跳转
        if next_item_index >= 0:
            # 打印当前章节和下一章节的详细信息
            logger.info(f"当前章节: {current_chapter} - {current_item_text}")
            logger.info(f"下一章节: {chapter_info[next_item_index]['chapter_num']} - {next_item_text}")
            
            next_item = chapter_info[next_item_index]['item']
            await next_item.scroll_into_view_if_needed()
            name_span = next_item.locator(".child-name").first
            
            if await name_span.count() > 0:
                await name_span.click(timeout=2000)
                logger.info(f"✅ 成功跳转到下一个章节: {chapter_info[next_item_index]['chapter_num']} - {next_item_text}")
            else:
                await next_item.click(timeout=2000)
                logger.info(f"✅ 成功跳转到下一个章节: {chapter_info[next_item_index]['chapter_num']} - {next_item_text}")
            
            return True
        else:
            logger.info(f"❌ 未找到章节 {current_chapter} 的下一个章节")
            return False
            
    except Exception as e:
        logger.error(f"查找下一个章节时出错: {str(e)}")
        return False


async def auto_next_video(page: Page) -> None:
    """当视频进度达到100%时自动跳转到下一个视频"""
    await page.wait_for_load_state("networkidle")
    
    while True:
        try:
            if page.is_closed():
                logger.write_log("浏览器已关闭,自动跳转视频模块已下线.\n")
                return
            
            await asyncio.sleep(3)
            
            if page.is_closed():
                logger.write_log("浏览器已关闭,自动跳转视频模块已下线.\n")
                return
            
            await page.wait_for_load_state("networkidle", timeout=5000)
            
            from modules.progress import get_current_class_name
            from modules.progress import get_progress_with_tooltip
            from modules.progress import close_pre_study_popup
            
            class_name = await get_current_class_name(page)
            
            if not class_name:
                title_elem = await page.query_selector(".video-study-title")
                if title_elem:
                    try:
                        class_name = await title_elem.text_content()
                    except Exception:
                        pass
            if not class_name:
                title_elem = await page.query_selector(".catalog-content-title")
                if title_elem:
                    try:
                        class_name = await title_elem.text_content()
                    except Exception:
                        pass
            if not class_name:
                title_elem = await page.query_selector(".chapter-title")
                if title_elem:
                    try:
                        class_name = await title_elem.text_content()
                    except Exception:
                        pass
            
            def _norm(s):
                import re
                return re.sub(r'^\s*\d+(?:\.\d+)*\s*[．\. ]*', '', s).strip() if s else None
            
            progress_info = await get_progress_with_tooltip(page)
            current_progress = 0
            if progress_info:
                progress_text = progress_info.get('数值进度', '0%')
                current_progress = int(progress_text.replace('%', ''))
            
            current_video = None
            items = page.locator(".child-info.hasvideo")
            items_count = await items.count()
            
            for i in range(items_count):
                it = items.nth(i)
                name_el = it.locator(".catalogue_title").first
                if await name_el.count() > 0:
                    try:
                        text = await name_el.text_content()
                    except Exception:
                        text = None
                    if text and class_name and _norm(text) == _norm(class_name):
                        has_video = await it.evaluate("el => el.classList.contains('hasvideo')")
                        if has_video:
                            current_video = it
                            break
            
            if not current_video:
                current_video = await page.query_selector(".current_play.hasvideo")
            
            if not current_video:
                continue
            
            finish_icon = await current_video.query_selector(".time_icofinish")
            has_finish_icon = finish_icon is not None
            
            should_jump = has_finish_icon or (current_progress >= 80)
            
            display_name = class_name if class_name else "未知视频"
            logger.info(f"当前视频: [{display_name}], 进度: {current_progress}%, 完成图标: {has_finish_icon}, 需要跳转: {should_jump}")
            
            if not should_jump:
                if current_progress > 0:
                    logger.info(f"视频 [{display_name}] 进度: {current_progress}%, 等待完成...")
                continue
            
            if has_finish_icon:
                logger.info(f"视频 [{display_name}] 已完成，准备跳转到下一个视频")
            
            await close_pre_study_popup(page)
            
            all_videos = await page.query_selector_all(".child-info.hasvideo")
            if not all_videos:
                continue
            
            current_index = -1
            for i, video in enumerate(all_videos):
                if await video.evaluate("el => el.classList.contains('current_play')"):
                    current_index = i
                    break
            
            next_video_found = False
            next_video_name = None
            for i in range(current_index + 1, len(all_videos)):
                video = all_videos[i]
                video_finish_icon = await video.query_selector(".time_icofinish")
                
                if not video_finish_icon:
                    video_name_el = await video.query_selector(".catalogue_title")
                    if video_name_el:
                        try:
                            next_video_name = await video_name_el.text_content()
                        except Exception:
                            next_video_name = None
                    next_video_display = next_video_name if next_video_name else f"第{i+1}个视频"
                    logger.info(f"正在跳转到下一个未完成的视频: [{next_video_display}]")
                    await video.click()
                    await page.wait_for_load_state("networkidle", timeout=10000)
                    await asyncio.sleep(2)
                    next_video_found = True
                    break
            
            if not next_video_found:
                logger.info("后面没有未完成的视频了，尝试从课程开头找...")
                for i, video in enumerate(all_videos):
                    if i == current_index:
                        continue
                    video_finish_icon = await video.query_selector(".time_icofinish")
                    if not video_finish_icon:
                        video_name_el = await video.query_selector(".catalogue_title")
                        if video_name_el:
                            try:
                                next_video_name = await video_name_el.text_content()
                            except Exception:
                                next_video_name = None
                        next_video_display = next_video_name if next_video_name else f"第{i+1}个视频"
                        logger.info(f"跳回前面未完成的视频: [{next_video_display}]")
                        await video.click()
                        await page.wait_for_load_state("networkidle", timeout=10000)
                        await asyncio.sleep(2)
                        next_video_found = True
                        break
            
            if next_video_found:
                next_video_display = next_video_name if next_video_name else "下一个视频"
                logger.info(f"已成功跳转到视频: [{next_video_display}]")
                continue
            else:
                logger.info("=" * 50)
                logger.info("当前章节所有视频都已完成!")
                logger.info("=" * 50)
                return
                
        except TargetClosedError:
            logger.write_log("浏览器已关闭,自动跳转视频模块已下线.\n")
            return
        except Exception as e:
            logger.error(f"自动跳转视频模块发生错误: {str(e)}")
            continue


async def check_progress_and_skip(page: Page) -> None:
    """当数值进度达到80%以上时，自动跳转到下一个视频"""
    from modules.progress import check_progress_and_next_video
    
    await page.wait_for_load_state("networkidle")
    while True:
        try:
            if page.is_closed():
                logger.write_log("浏览器已关闭,进度检查跳转模块已下线.\n")
                return
            await asyncio.sleep(5)  # 默认每5秒检查一次进度
            
            # 获取当前进度
            from modules.progress import get_progress_with_tooltip
            progress_info = await get_progress_with_tooltip(page)
            
            if progress_info:
                # 提取进度数值
                progress_text = progress_info.get('数值进度', '0%')
                progress_value = int(progress_text.replace('%', ''))
                
                # 如果进度达到79%但小于80%，等待10秒后跳转
                if progress_value == 79:
                    logger.info(f"进度达到79%，前端不再显示进度条，等待10秒后跳转到下一个视频")
                    await page.wait_for_timeout(10000)  # 等待10秒
                
                # 如果进度达到70%以上，提高检查频率到每0.1秒一次
                if progress_value >= 70:
                    logger.info(f"进度达到{progress_value}%，提高检查频率到每0.1秒一次")
                    
                    # 初始化进度跟踪变量
                    previous_progress = progress_value
                    progress_history = [progress_value]  # 记录进度历史
                    consecutive_gap_2_count = 0  # 连续间隙差为2的计数
                    no_progress_count = 0  # 连续未获取到进度的计数
                    
                    # 高频检查模式
                    while True:
                        try:
                            await asyncio.sleep(0.1)  # 每0.1秒检查一次
                            
                            # 获取最新进度
                            new_progress_info = await get_progress_with_tooltip(page)
                            current_progress = None
                            
                            if new_progress_info:
                                new_progress_text = new_progress_info.get('数值进度', '0%')
                                current_progress = int(new_progress_text.replace('%', ''))
                                no_progress_count = 0  # 重置未获取到进度的计数
                                
                                # 检查进度间隙差
                                if current_progress > previous_progress:
                                    gap = current_progress - previous_progress
                                    logger.info(f"进度更新: {previous_progress}% → {current_progress}% (间隙差: {gap}%)")
                                    
                                    # 如果间隙差为2，增加计数
                                    if gap == 2:
                                        consecutive_gap_2_count += 1
                                        logger.info(f"检测到间隙差为2，连续次数: {consecutive_gap_2_count}")
                                    else:
                                        consecutive_gap_2_count = 0  # 重置计数
                                    
                                    # 更新进度历史
                                    progress_history.append(current_progress)
                                    if len(progress_history) > 3:  # 只保留最近3个进度值
                                        progress_history.pop(0)
                                else:
                                    # 进度没有增加
                                    consecutive_gap_2_count = 0
                                
                                previous_progress = current_progress
                            else:
                                # 没有获取到进度值
                                no_progress_count += 1
                                logger.info(f"未获取到进度值，连续次数: {no_progress_count}")
                                
                                # 如果连续3次未获取到进度值，且之前有连续间隙差为2的情况，则跳转
                                if no_progress_count >= 3 and consecutive_gap_2_count >= 2:
                                    logger.info("连续3次未获取到进度值，且之前有连续间隙差为2的情况，执行跳转")
                                    jumped = await check_progress_and_next_video(page)
                                    if jumped:
                                        logger.info("已成功跳转到下一个视频，退出高频检查模式")
                                        break
                                
                                # 如果连续10次未获取到进度值，可能是进度条已消失，直接跳转
                                if no_progress_count >= 10:
                                    logger.info("连续10次未获取到进度值，可能是进度条已消失，执行跳转")
                                    jumped = await check_progress_and_next_video(page)
                                    if jumped:
                                        logger.info("已成功跳转到下一个视频，退出高频检查模式")
                                        break
                            
                            # 检查进度并尝试跳转
                            jumped = await check_progress_and_next_video(page)
                            
                            # 如果成功跳转，退出高频检查模式
                            if jumped:
                                logger.info("已成功跳转到下一个视频，退出高频检查模式")
                                break
                            
                            # 如果进度低于70%，退出高频检查模式
                            if current_progress and current_progress < 70:
                                logger.info("进度低于70%，退出高频检查模式")
                                break
                            
                            # 最后一层判断：获取视频时长，将视频时长的85%作为跳转阈值
                            # 仅在前面所有逻辑失效时启用
                            if current_progress and current_progress >= 70:
                                try:
                                    # 获取视频总时长和当前播放时间
                                    from modules.utils import get_video_attr
                                    total_duration = await get_video_attr(page, "duration")
                                    current_time = await get_video_attr(page, "currentTime")
                                    
                                    if total_duration is not None and current_time is not None:
                                        # 计算85%的时长阈值
                                        threshold_time = total_duration * 0.85
                                        
                                        # 如果当前播放时间达到85%阈值，则跳转
                                        if current_time >= threshold_time:
                                            logger.info(f"视频播放时长达到85%阈值: {current_time:.1f}秒/{total_duration:.1f}秒，执行跳转")
                                            jumped = await check_progress_and_next_video(page)
                                            if jumped:
                                                logger.info("已成功跳转到下一个视频，退出高频检查模式")
                                                break
                                        else:
                                            logger.debug(f"视频播放时长未达到85%阈值: {current_time:.1f}秒/{threshold_time:.1f}秒")
                                    else:
                                        logger.debug("无法获取视频时长信息")
                                except Exception as e:
                                    logger.debug(f"获取视频时长信息时出错: {str(e)}")
                                
                        except TargetClosedError:
                            logger.write_log("浏览器已关闭,进度检查跳转模块已下线.\n")
                            return
                        except Exception as e:
                            logger.error(f"高频进度检查时发生错误: {str(e)}")
                            continue
                            
        except TargetClosedError:
            logger.write_log("浏览器已关闭,进度检查跳转模块已下线.\n")
            return
        except Exception as e:
            logger.error(f"进度检查跳转模块发生错误: {str(e)}")
            continue


async def task_monitor(page: Page) -> None:
    """定期获取并打印进度信息"""
    from modules.progress import get_progress_with_tooltip
    
    await page.wait_for_load_state("networkidle")
    while True:
        try:
            if page.is_closed():
                logger.write_log("浏览器已关闭,进度信息打印模块已下线.\n")
                return
            await asyncio.sleep(5)  # 每5秒获取一次进度信息
            progress_info = await get_progress_with_tooltip(page)
            # 进度信息已在get_progress_with_tooltip函数中打印，这里不需要重复打印
        except TargetClosedError:
            logger.write_log("浏览器已关闭,进度信息打印模块已下线.\n")
            return
        except Exception as e:
            continue


async def wait_for_verify(page: Page, config, event_loop) -> None:
    logger.info("=" * 30)
    logger.info("安全验证模块已启动.")
    logger.info("=" * 30)
    
    while True:
        try:
            if page.is_closed():
                logger.write_log("浏览器已关闭,安全验证模块已下线.\n")
                return
            
            await asyncio.sleep(1)
            
            modal_count = await page.locator('.yidun_modal').count()
            if modal_count > 0:
                logger.info("检测到验证码弹窗", shift=True)
                
                if config.enableAutoClickCaptcha:
                    logger.info("检测到点击验证,正在自动处理...", shift=True)
                    if config.enableHideWindow:
                        await display_window(page)
                    try:
                        import cv2
                        import numpy as np
                        await click_verify(page, [np, cv2], lambda msg: logger.info(msg))
                        event_loop.set()
                        if config.enableHideWindow:
                            await hide_window(page)
                        logger.info("点击验证已完成.", shift=True)
                    except Exception as e:
                        logger.warn(f"自动点击验证失败: {str(e)},请手动完成验证...", shift=True)
                        if config.enableHideWindow:
                            await display_window(page)
                        await page.wait_for_selector(".yidun_modal__title", state="hidden", timeout=24 * 3600 * 1000)
                        event_loop.set()
                        if config.enableHideWindow:
                            await hide_window(page)
                        logger.info("安全验证已完成.", shift=True)
                else:
                    logger.warn("检测到安全验证,请手动完成验证...", shift=True)
                    if config.enableHideWindow:
                        await display_window(page)
                    await page.wait_for_selector(".yidun_modal__title", state="hidden", timeout=24 * 3600 * 1000)
                    event_loop.set()
                    if config.enableHideWindow:
                        await hide_window(page)
                    logger.info("安全验证已完成.", shift=True)
                
                await asyncio.sleep(30)
        except TargetClosedError:
            logger.write_log("浏览器已关闭,安全验证模块已下线.\n")
            return
        except Exception as e:
            logger.warn(f"验证监控异常: {str(e)}")
            continue
