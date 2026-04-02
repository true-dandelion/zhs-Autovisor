# encoding=utf-8
import configparser
import re


class Config:
    def __init__(self, config_path=None, skip_course_urls=False):
        if config_path:
            self.config_path = config_path
            self._config = configparser.ConfigParser()
            # 用户常量
            self._read_config()
            self.driver = self.get_driver()
            self.username = self._config.get('user-account', 'username', raw=True)
            self.password = self._config.get('user-account', 'password', raw=True)
            # 浏览器选项
            self.exe_path = self._config.get('browser-option', 'EXE_PATH', raw=True)
            # 脚本选项
            self.enableAutoCaptcha = self.get_bool_field('script-option', 'enableAutoCaptcha')
            self.enableAutoClickCaptcha = self.get_bool_field('script-option', 'enableAutoClickCaptcha')
            self.enableHideWindow = self.get_bool_field('script-option', 'enableHideWindow')
            self.keepBrowserOpen = self.get_bool_field('script-option', 'keepBrowserOpen')
            # 课程选项
            self.soundOff = self.get_bool_field('course-option', 'soundOff', default=True)
        # 登录
        self.login_url = "https://passport.zhihuishu.com/login"
        self.block_js = '''return document.getElementsByClassName("yidun_jigsaw")[0].src'''
        self.bg_js = '''return document.getElementsByClassName("yidun_bg-img")[0].src'''
        # 弹窗
        self.pop_js = '''document.getElementsByClassName("iconfont iconguanbi")[0].click();'''
        self.close_ques = '''document.dispatchEvent(new KeyboardEvent('keydown', {bubbles: true, keyCode: 27 }));'''

        # 视频元素修改
        self.remove_pause = "document.querySelector('video').pause = ()=>{}"
        self.play_video = '''const video = document.querySelector('video');video.play();'''
        self.volume_none = "document.querySelector('video').volume=0;"
        self.set_none_icon = '''document.querySelector(".volumeBox").classList.add("volumeNone")'''
        self.reset_curtime = '''document.querySelector('video').currentTime=0;'''
        # 夜间模式
        self.night_js = '''document.getElementsByClassName("Patternbtn-div")[0].click()'''
        # 镜像源
        self.mirrors = {
            "华为": "https://mirrors.huaweicloud.com/repository/pypi",
            "阿里": "https://mirrors.aliyun.com/pypi",
            "清华": "https://pypi.tuna.tsinghua.edu.cn",
            "官方": "https://pypi.org"
        }
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0"
        }

    def _read_config(self) -> None:
        try:
            self._config.read(self.config_path, encoding='utf-8')
        except UnicodeDecodeError:
            self._config.read(self.config_path, encoding='gbk')

    def get_driver(self) -> str:
        driver = self._config.get('browser-option', 'driver', raw=True)
        if not driver:
            driver = "edge"
        return driver.lower()

    def get_bool_field(self, section: str, option: str, default: bool = False) -> bool:
        try:
            field = self._config.get(section, option, raw=True).lower()
            if field == "true":
                return True
            elif field == "false":
                return False
            else:
                return default
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default

    # @property修饰器可设置属性
    # 这样写可实时响应配置变化
    @property
    def limitSpeed(self) -> float:
        self._read_config()
        return float(self._config.get('course-option', 'limitSpeed', raw=True))

    @property
    def revise_speed(self) -> str:
        return f"document.querySelector('video').playbackRate={self.limitSpeed};"

    @property
    def revise_speed_name(self) -> str:
        return f'''document.querySelector(".speedBox span").innerText = "X {self.limitSpeed}";'''
