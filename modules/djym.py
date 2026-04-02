from types import ModuleType
import requests
import re
import asyncio
from playwright.async_api import Page
from playwright._impl._errors import TimeoutError
from modules.logger import Logger

cv2: ModuleType
np: ModuleType
logger = Logger()


async def download_image(url, screenshot=None):
    try:
        if screenshot is not None:
            logger.info(f"使用截图数据...")
            image_array = np.frombuffer(screenshot, dtype=np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            if img is None:
                logger.warn("截图解码失败")
                return None
            logger.info(f"截图解码成功，尺寸: {img.shape}")
            return img
        
        logger.info(f"开始下载图片: {url[:80]}...")
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            logger.warn(f"图片下载失败，状态码: {response.status_code}")
            return None
        image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if img is None:
            logger.warn("图片解码失败")
            return None
        logger.info(f"图片下载成功，尺寸: {img.shape}")
        return img
    except Exception as e:
        logger.warn(f"下载图片异常: {str(e)}")
        import traceback
        logger.warn(traceback.format_exc())
        return None


async def get_captcha_instruction(page: Page):
    try:
        tips_element = page.locator('.yidun_tips__text')
        if await tips_element.count() > 0:
            instruction = await tips_element.text_content()
            return instruction.strip()
    except Exception as e:
        logger.warn(f"获取验证码提示失败: {str(e)}")
    return None


async def get_target_images(page: Page):
    try:
        logger.info("开始获取目标图片...")
        
        bg_img_element = page.locator('.yidun_bg-img')
        bg_img_count = await bg_img_element.count()
        logger.info(f"找到 {bg_img_count} 个背景图片元素")
        
        bg_img_url = None
        if bg_img_count > 0:
            bg_img_url = await bg_img_element.get_attribute('src')
            logger.info(f"背景图片URL: {bg_img_url}")
        
        target_elements = page.locator('.yidun_inference')
        count = await target_elements.count()
        logger.info(f"找到 {count} 个 yidun_inference 元素")
        target_images = []
        
        for i in range(count):
            element = target_elements.nth(i)
            img_element = element.locator('.yidun_inference__img')
            img_count = await img_element.count()
            logger.info(f"  目标 {i}: 图片元素数量 = {img_count}")
            
            src = None
            background_position = None
            
            if img_count > 0:
                src = await img_element.get_attribute('src')
                logger.info(f"  目标 {i}: src = {src}")
                
                if not src:
                    src = await img_element.get_attribute('data-src')
                    logger.info(f"  目标 {i}: data-src = {src}")
                
                if not src:
                    style = await img_element.get_attribute('style')
                    logger.info(f"  目标 {i}: style = {style}")
                    if style:
                        import re
                        match = re.search(r'url\(["\']?([^"\'\)]+)["\']?\)', style)
                        if match:
                            src = match.group(1)
                            logger.info(f"  目标 {i}: 从 style 提取的 src = {src}")
                        
                        bg_pos_match = re.search(r'background-position:\s*([^;]+)', style)
                        if bg_pos_match:
                            background_position = bg_pos_match.group(1)
                            logger.info(f"  目标 {i}: background-position = {background_position}")
                
                if not src:
                    src = await img_element.evaluate('el => el.src')
                    logger.info(f"  目标 {i}: 通过 JS 获取的 src = {src}")
            
            if not src and bg_img_url:
                logger.info(f"  目标 {i}: 尝试从背景图片裁剪")
                try:
                    bounding_box = await element.bounding_box()
                    if bounding_box:
                        logger.info(f"  目标 {i}: 位置 = {bounding_box}")
                        
                        bg_img = await download_image(bg_img_url)
                        if bg_img is not None:
                            logger.info(f"  目标 {i}: 背景图片尺寸 = {bg_img.shape}")
                            
                            bg_box = await bg_img_element.bounding_box()
                            if bg_box:
                                logger.info(f"  目标 {i}: 背景图片位置 = {bg_box}")
                                
                                rel_x = int(bounding_box['x'] - bg_box['x'])
                                rel_y = int(bounding_box['y'] - bg_box['y'])
                                width = int(bounding_box['width'])
                                height = int(bounding_box['height'])
                                
                                logger.info(f"  目标 {i}: 相对位置 = ({rel_x}, {rel_y}), 尺寸 = {width}x{height}")
                                
                                if (rel_x >= 0 and rel_y >= 0 and 
                                    rel_x + width <= bg_img.shape[1] and 
                                    rel_y + height <= bg_img.shape[0]):
                                    
                                    cropped_img = bg_img[rel_y:rel_y+height, rel_x:rel_x+width]
                                    logger.info(f"  目标 {i}: 裁剪图片尺寸 = {cropped_img.shape}")
                                    
                                    _, buffer = cv2.imencode('.png', cropped_img)
                                    screenshot = buffer.tobytes()
                                    
                                    target_images.append({
                                        'index': i,
                                        'src': bg_img_url,
                                        'element': element,
                                        'screenshot': screenshot,
                                        'bounding_box': bounding_box,
                                        'cropped': True
                                    })
                                    logger.info(f"  目标 {i}: 成功从背景图片裁剪")
                                    continue
                except Exception as e:
                    logger.warn(f"  目标 {i}: 从背景图片裁剪失败: {str(e)}")
            
            if not src:
                logger.info(f"  目标 {i}: 尝试通过截图获取图片")
                try:
                    bounding_box = await element.bounding_box()
                    if bounding_box:
                        screenshot = await element.screenshot()
                        if screenshot:
                            target_images.append({
                                'index': i,
                                'src': None,
                                'element': element,
                                'screenshot': screenshot,
                                'bounding_box': bounding_box
                            })
                            logger.info(f"  目标 {i}: 成功获取截图")
                            continue
                except Exception as e:
                    logger.warn(f"  目标 {i}: 截图失败: {str(e)}")
            
            if src:
                target_images.append({
                    'index': i,
                    'src': src,
                    'element': element
                })
        
        logger.info(f"总共获取到 {len(target_images)} 个有效目标图片")
        return target_images
    except Exception as e:
        logger.warn(f"获取目标图片失败: {str(e)}")
        import traceback
        logger.warn(traceback.format_exc())
        return []


async def process_target_image(image):
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    except Exception as e:
        logger.warn(f"处理目标图片失败: {str(e)}")
        return None


async def detect_color(image):
    try:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        color_ranges = {
            'red': [
                ((0, 50, 50), (10, 255, 255)),
                ((170, 50, 50), (180, 255, 255))
            ],
            'green': [((40, 50, 50), (80, 255, 255))],
            'blue': [((100, 50, 50), (130, 255, 255))],
            'yellow': [((20, 50, 50), (35, 255, 255))],
            'purple': [((130, 50, 50), (160, 255, 255))],
            'orange': [((10, 50, 50), (20, 255, 255))],
            'black': [((0, 0, 0), (180, 255, 50))],
            'white': [((0, 0, 200), (180, 30, 255))],
            'gray': [((0, 0, 50), (180, 30, 200))]
        }
        
        color_scores = {}
        for color_name, ranges in color_ranges.items():
            total_pixels = 0
            for lower, upper in ranges:
                lower = np.array(lower)
                upper = np.array(upper)
                mask = cv2.inRange(hsv, lower, upper)
                total_pixels += cv2.countNonZero(mask)
            color_scores[color_name] = total_pixels
        
        dominant_color = max(color_scores, key=color_scores.get)
        logger.info(f"检测到主要颜色: {dominant_color} (像素数: {color_scores[dominant_color]})")
        
        return dominant_color, color_scores
    except Exception as e:
        logger.warn(f"颜色检测失败: {str(e)}")
        return None, {}


async def parse_captcha_instruction(instruction):
    try:
        logger.info(f"开始解析验证码指令: {instruction}")
        
        parsed_info = {
            'color': None,
            'letters': [],
            'direction': None,
            'case': None,
            'type': None
        }
        
        instruction_lower = instruction.lower()
        
        color_keywords = {
            '红色': 'red', '红': 'red',
            '绿色': 'green', '绿': 'green',
            '蓝色': 'blue', '蓝': 'blue',
            '黄色': 'yellow', '黄': 'yellow',
            '紫色': 'purple', '紫': 'purple',
            '橙色': 'orange', '橙': 'orange',
            '黑色': 'black', '黑': 'black',
            '白色': 'white', '白': 'white',
            '灰色': 'gray', '灰': 'gray'
        }
        
        for cn_color, en_color in color_keywords.items():
            if cn_color in instruction:
                parsed_info['color'] = en_color
                logger.info(f"识别到颜色: {en_color}")
                break
        
        letter_pattern = r'[a-zA-Z]'
        letters = re.findall(letter_pattern, instruction)
        if letters:
            parsed_info['letters'] = [letter.lower() for letter in letters]
            logger.info(f"识别到字母: {parsed_info['letters']}")
        
        if '小写' in instruction:
            parsed_info['case'] = 'lowercase'
            logger.info("识别到大小写: 小写")
        elif '大写' in instruction:
            parsed_info['case'] = 'uppercase'
            logger.info("识别到大小写: 大写")
        
        direction_keywords = {
            '朝向一样': 'same_direction',
            '朝向相同': 'same_direction',
            '方向一致': 'same_direction',
            '朝向相反': 'opposite_direction',
            '方向相反': 'opposite_direction',
            '向上': 'up',
            '向下': 'down',
            '向左': 'left',
            '向右': 'right',
            '顺时针': 'clockwise',
            '逆时针': 'counterclockwise'
        }
        
        for cn_direction, en_direction in direction_keywords.items():
            if cn_direction in instruction:
                parsed_info['direction'] = en_direction
                logger.info(f"识别到方向: {en_direction}")
                break
        
        type_keywords = {
            '点击': 'click',
            '选择': 'select',
            '拖动': 'drag',
            '旋转': 'rotate'
        }
        
        for cn_type, en_type in type_keywords.items():
            if cn_type in instruction:
                parsed_info['type'] = en_type
                logger.info(f"识别到操作类型: {en_type}")
                break
        
        logger.info(f"解析结果: {parsed_info}")
        return parsed_info
    except Exception as e:
        logger.warn(f"解析验证码指令失败: {str(e)}")
        import traceback
        logger.warn(traceback.format_exc())
        return {}


async def recognize_character(image):
    try:
        logger.info("开始识别字符...")
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            logger.warn("未找到字符轮廓")
            return None
        
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        roi = binary[y:y+h, x:x+w]
        
        if roi.size == 0:
            logger.warn("字符区域为空")
            return None
        
        features = extract_character_features(roi, largest_contour)
        
        character = classify_character(features)
        
        logger.info(f"识别到字符: {character}")
        return character
    except Exception as e:
        logger.warn(f"字符识别失败: {str(e)}")
        import traceback
        logger.warn(traceback.format_exc())
        return None


def extract_character_features(roi, contour):
    try:
        features = {}
        
        moments = cv2.moments(contour)
        features['area'] = moments['m00']
        features['perimeter'] = cv2.arcLength(contour, True)
        
        hull = cv2.convexHull(contour)
        features['hull_area'] = cv2.contourArea(hull)
        features['solidity'] = features['area'] / features['hull_area'] if features['hull_area'] > 0 else 0
        
        x, y, w, h = cv2.boundingRect(contour)
        features['aspect_ratio'] = float(w) / h if h > 0 else 0
        features['extent'] = features['area'] / (w * h) if w * h > 0 else 0
        
        features['circularity'] = (4 * np.pi * features['area']) / (features['perimeter'] ** 2) if features['perimeter'] > 0 else 0
        
        features['euler_number'] = len(contour) - len(hull)
        
        white_pixels = cv2.countNonZero(roi)
        total_pixels = roi.shape[0] * roi.shape[1]
        features['density'] = white_pixels / total_pixels if total_pixels > 0 else 0
        
        features['center_x'] = moments['m10'] / moments['m00'] if moments['m00'] > 0 else 0
        features['center_y'] = moments['m01'] / moments['m00'] if moments['m00'] > 0 else 0
        
        return features
    except Exception as e:
        logger.warn(f"提取字符特征失败: {str(e)}")
        return {}


def classify_character(features):
    try:
        if not features:
            return None
        
        area = features.get('area', 0)
        aspect_ratio = features.get('aspect_ratio', 0)
        solidity = features.get('solidity', 0)
        circularity = features.get('circularity', 0)
        density = features.get('density', 0)
        
        if circularity > 0.7:
            return 'o'
        
        if aspect_ratio > 1.5 and solidity > 0.8:
            return 'l' or 'i'
        
        if aspect_ratio < 0.7 and solidity > 0.7:
            return 'i'
        
        if aspect_ratio > 0.8 and aspect_ratio < 1.2 and solidity > 0.6:
            if density > 0.4:
                return 'a' or 'e' or 'o'
            else:
                return 'c' or 's' or 'u'
        
        if aspect_ratio > 1.0 and aspect_ratio < 1.5:
            if solidity > 0.7:
                return 'b' or 'd' or 'p' or 'q'
            else:
                return 'g' or 'j' or 'y'
        
        if density > 0.5:
            return 'm' or 'n' or 'w' or 'e'
        
        if density < 0.3:
            return 'i' or 'j' or 'l' or 't'
        
        return 'a'
    except Exception as e:
        logger.warn(f"字符分类失败: {str(e)}")
        return None


async def detect_character_direction(image):
    try:
        logger.info("开始检测字符方向...")
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            logger.warn("未找到字符轮廓")
            return None
        
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        moments = cv2.moments(largest_contour)
        cx = int(moments['m10'] / moments['m00']) if moments['m00'] > 0 else x + w // 2
        cy = int(moments['m01'] / moments['m00']) if moments['m00'] > 0 else y + h // 2
        
        roi = binary[y:y+h, x:x+w]
        
        top_pixels = cv2.countNonZero(roi[0:roi.shape[0]//3, :])
        middle_pixels = cv2.countNonZero(roi[roi.shape[0]//3:2*roi.shape[0]//3, :])
        bottom_pixels = cv2.countNonZero(roi[2*roi.shape[0]//3:, :])
        
        left_pixels = cv2.countNonZero(roi[:, 0:roi.shape[1]//3])
        center_pixels = cv2.countNonZero(roi[:, roi.shape[1]//3:2*roi.shape[1]//3])
        right_pixels = cv2.countNonZero(roi[:, 2*roi.shape[1]//3:])
        
        direction = 'up'
        max_pixels = top_pixels
        
        if bottom_pixels > max_pixels:
            direction = 'down'
            max_pixels = bottom_pixels
        if left_pixels > max_pixels:
            direction = 'left'
            max_pixels = left_pixels
        if right_pixels > max_pixels:
            direction = 'right'
            max_pixels = right_pixels
        
        logger.info(f"检测到字符方向: {direction}")
        return direction
    except Exception as e:
        logger.warn(f"检测字符方向失败: {str(e)}")
        import traceback
        logger.warn(traceback.format_exc())
        return None


async def find_matching_targets(instruction, target_images):
    try:
        logger.info(f"开始匹配目标，提示: {instruction}")
        
        parsed_info = await parse_captcha_instruction(instruction)
        logger.info(f"解析结果: {parsed_info}")
        
        matching_indices = []
        target_analysis = []
        
        for target in target_images:
            try:
                logger.info(f"  分析目标 {target['index']}...")
                
                screenshot = target.get('screenshot')
                src = target.get('src')
                
                if not src and not screenshot:
                    logger.warn(f"    目标 {target['index']} 没有有效的图片数据")
                    continue
                
                img = await download_image(src, screenshot)
                if img is None:
                    logger.warn(f"    下载目标 {target['index']} 图片失败")
                    continue
                
                logger.info(f"    目标 {target['index']} 图片尺寸: {img.shape}")
                
                analysis = {
                    'index': target['index'],
                    'color': None,
                    'character': None,
                    'direction': None,
                    'color_scores': {}
                }
                
                dominant_color, color_scores = await detect_color(img)
                analysis['color'] = dominant_color
                analysis['color_scores'] = color_scores
                logger.info(f"    目标 {target['index']} 颜色: {dominant_color}")
                
                character = await recognize_character(img)
                analysis['character'] = character
                logger.info(f"    目标 {target['index']} 字符: {character}")
                
                direction = await detect_character_direction(img)
                analysis['direction'] = direction
                logger.info(f"    目标 {target['index']} 方向: {direction}")
                
                target_analysis.append(analysis)
                
            except Exception as e:
                logger.warn(f"分析目标 {target['index']} 失败: {str(e)}")
                import traceback
                logger.warn(traceback.format_exc())
                continue
        
        logger.info(f"总共分析了 {len(target_analysis)} 个目标")
        
        for analysis in target_analysis:
            try:
                is_match = True
                match_reasons = []
                
                if parsed_info.get('color'):
                    if analysis['color'] == parsed_info['color']:
                        match_reasons.append(f"颜色匹配: {analysis['color']}")
                    else:
                        is_match = False
                        logger.info(f"    目标 {analysis['index']} 颜色不匹配: 期望 {parsed_info['color']}, 实际 {analysis['color']}")
                
                if parsed_info.get('letters') and analysis['character']:
                    if analysis['character'] in parsed_info['letters']:
                        match_reasons.append(f"字符匹配: {analysis['character']}")
                    else:
                        is_match = False
                        logger.info(f"    目标 {analysis['index']} 字符不匹配: 期望 {parsed_info['letters']}, 实际 {analysis['character']}")
                
                if parsed_info.get('direction') == 'same_direction':
                    if len(target_analysis) >= 2:
                        first_direction = target_analysis[0]['direction']
                        if analysis['direction'] == first_direction:
                            match_reasons.append(f"方向相同: {analysis['direction']}")
                        else:
                            is_match = False
                            logger.info(f"    目标 {analysis['index']} 方向不匹配: 期望 {first_direction}, 实际 {analysis['direction']}")
                
                if parsed_info.get('direction') == 'opposite_direction':
                    if len(target_analysis) >= 2:
                        first_direction = target_analysis[0]['direction']
                        if analysis['direction'] != first_direction:
                            match_reasons.append(f"方向相反: {analysis['direction']}")
                        else:
                            is_match = False
                            logger.info(f"    目标 {analysis['index']} 方向不匹配: 期望与 {first_direction} 相反, 实际 {analysis['direction']}")
                
                if is_match:
                    logger.info(f"    目标 {analysis['index']} 匹配成功: {', '.join(match_reasons)}")
                    matching_indices.append(analysis['index'])
                else:
                    logger.info(f"    目标 {analysis['index']} 不匹配")
                    
            except Exception as e:
                logger.warn(f"匹配目标 {analysis['index']} 失败: {str(e)}")
                continue
        
        if not matching_indices:
            logger.warn("未找到匹配目标，使用所有目标")
            matching_indices = list(range(len(target_images)))
        else:
            logger.info(f"匹配到 {len(matching_indices)} 个目标: {matching_indices}")
        
        return matching_indices
    except Exception as e:
        logger.warn(f"查找匹配目标失败: {str(e)}")
        import traceback
        logger.warn(traceback.format_exc())
        return []


async def click_targets(page: Page, target_elements, indices):
    try:
        for idx in indices:
            if idx < len(target_elements):
                try:
                    element = target_elements[idx]['element']
                    
                    if await element.count() == 0:
                        logger.warn(f"目标 {idx + 1} 元素已不存在")
                        continue
                    
                    await element.click(timeout=2000)
                    await asyncio.sleep(0.3)
                    logger.info(f"已点击目标 {idx + 1}")
                except Exception as e:
                    if "context" in str(e).lower() or "closed" in str(e).lower():
                        logger.info(f"验证码已关闭，停止点击")
                        return
                    logger.warn(f"点击目标 {idx + 1} 失败: {str(e)}")
    except Exception as e:
        if "context" in str(e).lower() or "closed" in str(e).lower():
            logger.info(f"验证码已关闭")
        else:
            logger.warn(f"点击目标失败: {str(e)}")


async def wait_for_captcha(page: Page):
    try:
        modal_exists = await page.locator('.yidun_modal').count() > 0
        if modal_exists:
            bg_exists = await page.locator('.yidun_bg-img').count() > 0
            inference_exists = await page.locator('.yidun_inference').count() > 0
            if bg_exists and inference_exists:
                return True
        
        await page.wait_for_selector('.yidun_modal', state='attached', timeout=2000)
        await page.wait_for_selector('.yidun_bg-img', state='attached', timeout=2000)
        await page.wait_for_selector('.yidun_inference', state='attached', timeout=2000)
        return True
    except TimeoutError:
        return False


async def click_verify(page: Page, modules: list[ModuleType], log_callback=None):
    global cv2, np
    np, cv2 = modules
    
    def log(msg, level="info"):
        if log_callback:
            log_callback(msg)
        if level == "warn":
            logger.warn(msg)
        else:
            logger.info(msg)
    
    if not cv2 or not np:
        log("OpenCV或Numpy导入失败,无法开启自动点击验证.", "warn")
        return
    
    async def is_page_alive():
        try:
            return page.is_closed() is False
        except Exception:
            return False
    
    if await is_page_alive() is False:
        log("浏览器已关闭，跳过点击验证", "warn")
        return
    
    log("开始处理点击验证...")
    
    captcha_ready = await wait_for_captcha(page)
    if not captcha_ready:
        log("未检测到点击验证码", "warn")
        return
    
    isPassed = 0
    for attempt in range(0, 3):
        try:
            if await is_page_alive() is False:
                log("浏览器已关闭，跳过点击验证", "warn")
                return
            
            log(f"第{attempt + 1}次尝试过点击验证...")
            
            instruction = await get_captcha_instruction(page)
            if instruction:
                log(f"验证码提示: {instruction}")
            
            target_images = await get_target_images(page)
            if not target_images:
                log("未找到目标图片", "warn")
                continue
            
            log(f"找到 {len(target_images)} 个目标")
            
            matching_indices = await find_matching_targets(instruction, target_images)
            if not matching_indices:
                log("未找到匹配的目标", "warn")
                continue
            
            log(f"准备点击 {len(matching_indices)} 个目标")
            
            await click_targets(page, target_images, matching_indices)
            
            await asyncio.sleep(1)
            
            try:
                modal_count = await page.locator('.yidun_modal').count()
                if modal_count == 0:
                    isPassed = 1
                    log("点击验证已成功通过.")
                    break
                
                await page.wait_for_selector('.yidun_modal', state='hidden', timeout=3000)
                isPassed = 1
                log("点击验证已成功通过.")
                break
            except TimeoutError:
                modal_count = await page.locator('.yidun_modal').count()
                if modal_count == 0:
                    isPassed = 1
                    log("点击验证已成功通过.")
                    break
                log("验证未通过，准备重试...")
                await asyncio.sleep(2)
                
        except Exception as e:
            if "closed" in str(e).lower():
                log("浏览器已关闭，跳过点击验证", "warn")
                return
            log(f"点击验证出错: {str(e)}", "warn")
            await asyncio.sleep(2)
    
    if not isPassed:
        log("自动过点击验证失败,请手动验证!", "warn")
