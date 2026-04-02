# encoding=utf-8
import json
import os
import hashlib
import requests
import shutil
import sys
import platform
from modules import version


VERSION_URL = "http://www.shaoxin.top/m/y/version.json"
BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def clear_screen():
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')


def get_local_version():
    return {
        "version": version.VERSION,
        "force_update": version.FORCE_UPDATE
    }


def get_file_md5(file_path):
    if not os.path.exists(file_path):
        return None
    md5_hash = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def check_update():
    try:
        response = requests.get(VERSION_URL, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"检查更新失败: {e}")
        return None


def download_file(url, save_path):
    try:
        response = requests.get(url, stream=True, timeout=30)
        if response.status_code == 200:
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = int(downloaded * 100 / total_size)
                            print(f"\r下载进度: {percent}%", end="")
            print()
            return True
        return False
    except Exception as e:
        print(f"下载失败: {e}")
        return False


def update_files(server_files):
    IGNORE_PATTERNS = ['res/', 'logs/', 'internal/id.json']

    def should_ignore(filename):
        for pattern in IGNORE_PATTERNS:
            if filename == pattern or filename.startswith(pattern):
                return True
        return False

    local_version = get_local_version()
    local_files = {f['name']: f for f in local_version.get('files', [])}

    update_list = []
    for file_info in server_files:
        file_name = file_info.get('name')
        server_md5 = file_info.get('md5')

        if should_ignore(file_name):
            continue

        local_file_path = os.path.join(BASE_DIR, file_name)

        if file_name not in local_files:
            update_list.append((file_info, "new"))
            continue

        local_md5 = get_file_md5(local_file_path)
        if local_md5 != server_md5:
            update_list.append((file_info, "update"))

    return update_list


def perform_update(update_list):
    if not update_list:
        print("已是最新版本，无需更新。")
        return False

    temp_dir = os.path.join(BASE_DIR, 'temp_update')
    os.makedirs(temp_dir, exist_ok=True)

    try:
        print(f"发现 {len(update_list)} 个文件需要更新：")
        for file_info, action in update_list:
            print(f"  {'新增' if action == 'new' else '更新'}: {file_info['name']}")

        print("\n开始下载更新文件...")

        for file_info, action in update_list:
            file_name = file_info.get('name')
            file_url = file_info.get('url')

            temp_path = os.path.join(temp_dir, os.path.basename(file_name))
            target_path = os.path.join(BASE_DIR, file_name)

            print(f"正在下载: {file_name}...")
            if download_file(file_url, temp_path):
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.move(temp_path, target_path)
                print(f"  {file_name} 安装完成")

        shutil.rmtree(temp_dir, ignore_errors=True)
        print("\n更新完成！请重新启动程序。")
        return True
    except Exception as e:
        print(f"更新失败: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False


def start_update():
    print("正在检查更新，请稍候...")
    server_version = check_update()

    if not server_version:
        print("无法获取版本信息，请检查网络连接。")
        return False

    server_ver = server_version.get('version', '0.0.0')
    server_files = server_version.get('files', [])
    server_force = server_version.get('force_update', False)

    local_version = get_local_version()
    local_ver = local_version.get('version', '0.0.0')
    local_force = local_version.get('force_update', False)

    print(f"当前版本: {local_ver}")
    print(f"最新版本: {server_ver}")

    if server_ver <= local_ver and not server_force:
        print("已是最新版本。")
        clear_screen()
        return False

    update_list = update_files(server_files)

    if not update_list:
        print("已是最新版本，无需更新。")
        clear_screen()
        return False

    is_force = server_force or local_force

    if is_force:
        print("已检测到新版本，正在强制更新...")
    else:
        print("已检测到新版本，为提升软件稳定性与使用体验，建议立即更新。")
        print("是否现在更新？(y/n)")

        choice = input("请输入: ").strip().lower()
        if choice != 'y':
            print("已跳过更新。")
            clear_screen()
            return False

    print(f"开始更新至版本 {server_ver}...")

    if perform_update(update_list):
        print("更新完成，程序将重启...")
        sys.exit(0)


if __name__ == "__main__":
    start_update()
