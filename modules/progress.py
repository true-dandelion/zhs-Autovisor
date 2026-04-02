# encoding=utf-8
import random
from playwright.async_api import Page, TimeoutError
from modules.logger import Logger

logger = Logger()


# 视频区域内移动鼠标
async def move_mouse(page: Page):
    try:
        await page.wait_for_selector(".videoArea", state="attached", timeout=5000)
        elem = page.locator(".videoArea")
        await elem.hover(timeout=4000)
        pos = await elem.bounding_box()
        if not pos:
            return
        # Calculate the target position to move the mouse
        target_x = pos['x'] + random.uniform(-10, 10)
        target_y = pos['y'] + random.uniform(-10, 10)
        await page.mouse.move(target_x, target_y)
    except TimeoutError:
        return


# 获取课程进度
async def get_course_progress(page: Page, is_new_version=False, is_hike_class=False):
    curtime = "0%"
    await move_mouse(page)
    if is_hike_class:
        cur_play = await page.query_selector(".file-item.active")
        progress = await cur_play.query_selector(".rate")
    else:
        cur_play = await page.query_selector(".current_play")
        progress = await cur_play.query_selector(".progress-num")
    if not progress:
        if not is_hike_class:
            if is_new_version:
                progress_ele = await cur_play.query_selector(".progress-num")
                if progress_ele:
                    progress = await progress_ele.text_content()
                    finish = progress == "100%"
                else:
                    finish = False
            else:
                finish = await cur_play.query_selector(".time_icofinish")
        else:
            finish = await cur_play.query_selector(".icon-finish")
        if finish:
            curtime = "100%"
    else:
        curtime = await progress.text_content()

    return curtime


# 打印课程播放进度
def show_course_progress(desc, cur_time=None, limit_time=0, is_new_version=False, course_name=""):
    assert limit_time >= 0, "limit_time 必须为非负数!"
    
    if is_new_version:
        # 新版本进度条格式
        cur_time = "0%" if cur_time == '' else cur_time
        percent = int(cur_time.split("%")[0]) + 1  # Handles a 1% rendering error
        if percent >= 80:  # In learning mode, 80% progress is considered complete
            percent = 100
        length = int(percent * 30 // 100)
        progress = ("█" * length).ljust(30, " ")
        # 新版本进度条格式
    else:
        # 旧版本进度条格式（保持不变）
        if limit_time == 0:
            cur_time = "0%" if cur_time == '' else cur_time
            percent = int(cur_time.split("%")[0]) + 1  # Handles a 1% rendering error
            if percent >= 80:  # In learning mode, 80% progress is considered complete
                percent = 100
            length = int(percent * 30 // 100)
            progress = ("█" * length).ljust(30, " ")
            # 保留原始的进度打印，并在同一行添加新进度信息
            # print(f"\r{desc} |{progress}| {percent}%\t新进度为: {percent}%".ljust(70), end="", flush=True)
        else:
            cur_time = 0 if cur_time == '' else cur_time
            left_time = round(limit_time - cur_time, 1)
            percent = int(cur_time / limit_time * 100)
            if left_time <= 0:
                percent = 100
            length = int(percent * 20 // 100)
            progress = ("█" * length).ljust(20, " ")
            # 保留原始的进度打印，并在同一行添加新进度信息
            # print(f"\r{desc} |{progress}| {percent}%\t剩余 {left_time} min\t新进度为: {percent}%".ljust(70), end="", flush=True)


# 打印通用版进度条
def show_progress(desc, current, total, suffix="", width=30):
    percent = int(current / total * 100)
    length = int(percent * width // 100)
    progress = ("█" * length).ljust(width, " ")
    # print(f"\r{desc} |{progress}| {percent}%\t{suffix}".ljust(50), end="", flush=True)


# 关闭学前必读弹窗和知识掌握度弹窗
async def close_pre_study_popup(page: Page):
    try:
        if page.is_closed():
            return False
        # 检测并关闭知识掌握度弹窗
        try:
            knowledge_popup = await page.query_selector(".header-box .right-box .tit")
            if knowledge_popup:
                try:
                    popup_text = await knowledge_popup.text_content()
                except Exception:
                    popup_text = None
                if popup_text and "知识掌握度" in popup_text:
                    # print("发现知识掌握度弹窗，正在关闭...")
                    # 尝试找到关闭按钮
                    close_button = await page.query_selector(".header-box .close-box .icon-close")
                    if close_button:
                        await close_button.click()
                        await page.wait_for_timeout(1000)
                        return True
        except Exception as e:
            logger.info(f"关闭知识掌握度弹窗时出错: {str(e)}")
        
        # 检测并关闭学前必读弹窗
        popup_selectors = [
            ".dialog-read",
            ".el-dialog",
        ]
        
        popup_found = False
        for selector in popup_selectors:
            try:
                popup_element = await page.query_selector(selector)
                if popup_element:
                    try:
                        popup_text = await popup_element.text_content()
                    except Exception:
                        popup_text = None
                    if popup_text and "学前必读" in popup_text:
                        popup_found = True
                        break
            except Exception as e:
                continue
            
        # 尝试找到关闭按钮
        close_button_selectors = [
            ".el-dialog__header i.iconfont.iconguanbi",
            ".dialog-read .el-dialog__header i",
            "i.iconfont.iconguanbi",
            ".el-dialog__headerbtn",
        ]
        
        for selector in close_button_selectors:
            try:
                close_button = await page.query_selector(selector)
                if close_button:
                    await close_button.click()
                    # 等待弹窗关闭
                    await page.wait_for_timeout(1000)
                    return True
            except Exception as e:
                continue
                
        return False
    except Exception as e:
        logger.info(f"关闭弹窗时出错: {str(e)}")
        return False


# 获取当前课堂名称
async def get_current_class_name(page: Page):
    try:
        if page.is_closed():
            return None
        # 尝试多种可能的课堂名称选择器
        selectors = [
            ".video-study-wrapper-title span[title]",
            ".video-study-wrapper-title",
            ".video-study-title",
            ".source-name",
            ".course-name",
            ".catalog-title",
            ".catalog-content-title",
            ".lesson-title",
            ".chapter-title",
            ".current-lesson-name",
            ".lessonName",
            "#lessonName",
            ".video-title",
            ".player-title"
        ]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    # 尝试获取title属性或文本内容
                    title = await element.get_attribute('title')
                    if not title:
                        title = await element.text_content()
                    
                    if title and title.strip():
                        return title.strip()
            except Exception:
                continue
        
        return None
    except Exception as e:
        logger.info(f"获取课堂名称时出错: {str(e)}")
        return None


# 检查进度并在达到80%或以上时跳转到下一个视频
async def check_progress_and_next_video(page: Page):
    try:
        # 1. 获取当前进度信息
        progress_info = await get_progress_with_tooltip(page)
        
        # 2. 如果没有获取到进度信息，返回False
        if not progress_info:
            return False
            
        # 3. 提取进度数值
        progress_text = progress_info.get('数值进度', '0%')
        progress_value = int(progress_text.replace('%', ''))
        
        # 4. 检查进度是否达到79%或以上
        if progress_value >= 79:
            # print(f"进度达到{progress_value}%，正在跳转到下一个视频")
            
            # 如果进度达到79%但小于80%，等待10秒后跳转
            if progress_value == 79:
                logger.info(f"进度达到79%，前端不再显示进度条，等待10秒后跳转到下一个视频")
                await page.wait_for_timeout(10000)  # 等待10秒
            
            # 5. 首先尝试常见的下一个视频按钮
            next_video_selectors = [
                ".next-btn",
                ".next",
                ".btn-next",
                "[title*='下一个']",
                "[title*='下一节']",
                ".video-next"
            ]
            
            for selector in next_video_selectors:
                try:
                    next_button = await page.query_selector(selector)
                    if next_button:
                        await next_button.click()
                        # 等待页面加载
                        await page.wait_for_timeout(2000)
                        return True
                except Exception as e:
                    continue
            
            # 6. 如果没有找到常见的按钮，先尝试点击进度条下方的元素
            try:
                # 获取进度条元素的位置
                progress_bar = None
                progress_selectors = [
                    ".el-progress--circle",
                    ".el-progress",
                    ".progress-bar",
                    ".video-progress",
                    ".progress-circle"
                ]
                
                for selector in progress_selectors:
                    try:
                        progress_bar = await page.query_selector(selector)
                        if progress_bar:
                            break
                    except Exception as e:
                        continue
                
                if progress_bar:
                    # 获取进度条的边界框
                    progress_bounding_box = await progress_bar.bounding_box()
                    if progress_bounding_box:
                        # 在进度条下方查找可点击的元素
                        clickable_elements = await page.evaluate("""
                            () => {
                                const elements = [];
                                // 查找所有可点击的元素
                                const allElements = document.querySelectorAll('a, button, [onclick], [role="button"]');
                                
                                for (const elem of allElements) {
                                    const rect = elem.getBoundingClientRect();
                                    // 只考虑在进度条下方的元素
                                    if (rect.top > """ + str(progress_bounding_box['y'] + progress_bounding_box['height']) + """ && 
                                        rect.width > 10 && rect.height > 10) {
                                        elements.push({
                                            selector: elem.tagName.toLowerCase() + (elem.className ? '.' + elem.className.split(' ').join('.') : '') + (elem.id ? '#' + elem.id : ''),
                                            text: elem.innerText || elem.textContent || '',
                                            visible: window.getComputedStyle(elem).display !== 'none' && 
                                                    window.getComputedStyle(elem).visibility !== 'hidden'
                                        });
                                    }
                                }
                                return elements;
                            }
                        """)
                        
                        # 过滤出可见且可能相关的元素
                        relevant_elements = [
                            elem for elem in clickable_elements 
                            if elem['visible'] and (
                                '下一' in elem['text'] or 
                                'next' in elem['selector'].lower() or 
                                '继续' in elem['text'] or
                                '完成' in elem['text']
                            )
                        ]
                        
                        # 尝试点击找到的相关元素
                        for elem in relevant_elements:
                            try:
                                element = await page.query_selector(elem['selector'])
                                if element:
                                    await element.click()
                                    await page.wait_for_timeout(2000)
                                    return True
                            except Exception as e:
                                continue
                        
                        # 如果没有找到明显相关的元素，尝试点击进度条下方的第一个可见按钮或链接
                        visible_elements = [
                            elem for elem in clickable_elements 
                            if elem['visible']
                        ]
                        
                        if visible_elements:
                            try:
                                element = await page.query_selector(visible_elements[0]['selector'])
                                if element:
                                    await element.click()
                                    await page.wait_for_timeout(2000)
                                    return True
                            except Exception as e:
                                pass
            except Exception as e:
                logger.info(f"在进度条下方查找可点击按钮时出错: {str(e)}")
                
            # 7. 如果在进度条下方没有找到合适的元素，再尝试在整个视频区域下方查找
            try:
                # 获取当前视频区域的位置
                video_area = await page.query_selector(".video-study")
                if video_area:
                    # 获取视频区域的边界框
                    bounding_box = await video_area.bounding_box()
                    if bounding_box:
                        # 在视频区域下方查找可点击的元素
                        clickable_elements = await page.evaluate("""
                            () => {
                                const elements = [];
                                // 查找所有可点击的元素
                                const allElements = document.querySelectorAll('a, button, [onclick], [role="button"]');
                                
                                for (const elem of allElements) {
                                    const rect = elem.getBoundingClientRect();
                                    // 只考虑在视频区域下方的元素
                                    if (rect.top > """ + str(bounding_box['y'] + bounding_box['height']) + """ && 
                                        rect.width > 10 && rect.height > 10) {
                                        elements.push({
                                            selector: elem.tagName.toLowerCase() + (elem.className ? '.' + elem.className.split(' ').join('.') : '') + (elem.id ? '#' + elem.id : ''),
                                            text: elem.innerText || elem.textContent || '',
                                            visible: window.getComputedStyle(elem).display !== 'none' && 
                                                    window.getComputedStyle(elem).visibility !== 'hidden'
                                        });
                                    }
                                }
                                return elements;
                            }
                        """)
                        
                        # 过滤出可见且可能相关的元素
                        relevant_elements = [
                            elem for elem in clickable_elements 
                            if elem['visible'] and (
                                '下一' in elem['text'] or 
                                'next' in elem['selector'].lower() or 
                                '继续' in elem['text'] or
                                '完成' in elem['text']
                            )
                        ]
                        
                        # 尝试点击找到的相关元素
                        for elem in relevant_elements:
                            try:
                                element = await page.query_selector(elem['selector'])
                                if element:
                                    await element.click()
                                    await page.wait_for_timeout(2000)
                                    return True
                            except Exception as e:
                                continue
                        
                        # 如果没有找到明显相关的元素，尝试点击视频区域下方的第一个可见按钮或链接
                        visible_elements = [
                            elem for elem in clickable_elements 
                            if elem['visible']
                        ]
                        
                        if visible_elements:
                            try:
                                element = await page.query_selector(visible_elements[0]['selector'])
                                if element:
                                    await element.click()
                                    await page.wait_for_timeout(2000)
                                    return True
                            except Exception as e:
                                pass
            except Exception as e:
                logger.info(f"在视频区域下方查找可点击按钮时出错: {str(e)}")
                    
            # 8. 如果没有找到任何按钮，尝试点击视频列表中的下一个视频
            try:
                # 首先尝试找到当前播放的视频项（带有cur类的child-info）
                current_video = await page.query_selector(".child-info.cur")
                
                if current_video:
                    # 检查当前视频是否有完成图标
                    finish_icon = await current_video.query_selector("img.finish-icon")
                    
                    # 如果当前视频有完成图标，说明已经完成，需要找到下一个未完成的视频
                    if finish_icon:
                        # 查找所有带有hasvideo类的视频项
                        all_videos = await page.query_selector_all(".child-info.hasvideo")
                        
                        # 找到当前视频在列表中的位置
                        current_index = -1
                        for i, video in enumerate(all_videos):
                            if await video.evaluate("el => el.classList.contains('cur')"):
                                current_index = i
                                break
                        
                        # 从当前位置开始，查找下一个没有完成图标的视频
                        for i in range(current_index + 1, len(all_videos)):
                            video = all_videos[i]
                            video_finish_icon = await video.query_selector("img.finish-icon")
                            
                            # 如果这个视频没有完成图标，说明是下一个未完成的视频
                            if not video_finish_icon:
                                await video.click()
                                await page.wait_for_timeout(2000)
                                logger.info(f"已跳转到下一个未完成的视频")
                                return True
                        
                        # 如果所有视频都已完成，尝试点击第一个视频
                        if all_videos:
                            await all_videos[0].click()
                            await page.wait_for_timeout(2000)
                            logger.info(f"所有视频都已完成，跳转到第一个视频")
                            return True
                    else:
                        # 如果当前视频没有完成图标，说明还未完成，不需要跳转
                        logger.info(f"当前视频还未完成，不进行跳转")
                        return False
                else:
                    # 如果没有找到当前播放的视频，尝试点击第一个带有hasvideo类的视频
                    first_video = await page.query_selector(".child-info.hasvideo")
                    if first_video:
                        await first_video.click()
                        await page.wait_for_timeout(2000)
                        logger.info(f"未找到当前视频，跳转到第一个视频")
                        return True
            except Exception as e:
                logger.info(f"尝试点击视频列表中的下一个视频时出错: {str(e)}")
                
            return False
        else:
            return False
    except Exception as e:
        logger.info(f"检查进度并跳转下一个视频时出错: {str(e)}")
        return False


# 获取带tooltip的进度条信息
async def get_progress_with_tooltip(page: Page):
    try:
        if page.is_closed():
            return None
        # 0. 先尝试关闭学前必读弹窗
        await close_pre_study_popup(page)
        
        # 1. 先获取当前课堂名称
        class_name = await get_current_class_name(page)
        
        # 2. 获取当前正在播放的视频元素
        current_video = None
        current_video_selectors = [
            ".child-info.current.cur.hasvideo",
            ".child-info.current.hasvideo",
            ".child-info.cur.hasvideo"
        ]
        
        for selector in current_video_selectors:
            try:
                current_video = await page.query_selector(selector)
                if current_video:
                    break
            except Exception:
                continue
        
        # 如果没有找到当前播放的视频，尝试通过名称匹配
        if not current_video and class_name:
            def _norm(s):
                import re
                return re.sub(r'^\s*\d+(?:\.\d+)*\s*[．\. ]*', '', s).strip() if s else None
                
            items = page.locator(".child-info")
            items_count = await items.count()
            for i in range(items_count):
                it = items.nth(i)
                name_el = it.locator(".child-name").first
                if await name_el.count() > 0:
                    try:
                        text = await name_el.text_content()
                    except Exception:
                        text = None
                    if text and _norm(text) == _norm(class_name):
                        has_video = await it.evaluate("el => el.classList.contains('hasvideo')")
                        if has_video:
                            current_video = it
                            break
        
        # 如果仍然没有找到当前视频，返回None
        if not current_video:
            return None
        
        # 3. 从当前视频元素中获取进度条
        progress_element = await current_video.query_selector(".el-progress[role='progressbar']")
        if not progress_element:
            progress_element = await current_video.query_selector(".el-progress-circle__path")
        
        # 如果找到了进度条元素，直接从元素属性获取进度
        if progress_element:
            try:
                progress_value = await progress_element.get_attribute("aria-valuenow")
                if progress_value:
                    # 获取当前视频的名称
                    name_el = await current_video.query_selector(".child-name")
                    video_name = ""
                    if name_el:
                        try:
                            video_name = await name_el.text_content()
                        except Exception:
                            pass
                    
                    logger.info(f"从当前视频元素获取进度: {video_name} - {progress_value}%")
                    return {
                        '课堂名称': video_name if video_name else class_name if class_name else '未知',
                        '数值进度': f'{progress_value}%',
                        '文本进度': f'学习进度{progress_value}%'
                    }
            except Exception as e:
                logger.info(f"从进度条元素获取进度时出错: {str(e)}")
        
        # 4. 如果无法从进度条元素获取进度，尝试使用tooltip方法
        await move_mouse(page)
        
        # 尝试找到进度条元素并移动鼠标到上面
        progress_selectors = [
            ".el-progress--circle",
            ".el-progress",
            ".progress-bar",
            ".video-progress",
            ".progress-circle"
        ]
        
        progress_found = False
        for selector in progress_selectors:
            try:
                progress_element = await page.query_selector(selector)
                if progress_element:
                    # 移动鼠标到进度条元素上
                    await progress_element.hover()
                    progress_found = True
                    break
            except Exception as e:
                continue
        
        # 等待一小段时间让tooltip显示
        await page.wait_for_timeout(1000)
        
        # 直接查找包含学习进度的tooltip元素
        tooltip_ele = page.locator('.el-popper.is-customized')
        
        # 检查tooltip元素是否存在
        if await tooltip_ele.count() == 0:
            return None
            
        # 获取tooltip文本内容
        try:
            tooltip_text = await tooltip_ele.text_content()
        except Exception:
            return None
        
        # 检查tooltip文本是否存在且包含学习进度
        if not tooltip_text or '学习进度' not in tooltip_text:
            return None
        
        # 从文本中提取进度数值（从"学习进度54%"中提取54）
        import re
        progress_match = re.search(r'学习进度(\d+)%', tooltip_text)
        if not progress_match:
            return None
            
        progress_value = progress_match.group(1)  # 得到"54"
        
        # 获取当前视频的名称
        name_el = await current_video.query_selector(".child-name")
        video_name = ""
        if name_el:
            try:
                video_name = await name_el.text_content()
            except Exception:
                pass
        
        class_display = video_name if video_name else (class_name if class_name else "未知课堂")
        
        return {
            '课堂名称': class_display,
            '数值进度': f'{progress_value}%',
            '文本进度': f'学习进度{progress_value}%'
        }
    except Exception as e:
        logger.info(f"获取进度信息时出错: {str(e)}")
        return None
