# encoding=utf-8
import json
import os
import sys
import subprocess
import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes


def is_packaged():
    return getattr(sys, 'frozen', False)


def get_disk_serial_number():
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-PhysicalDisk | Select-Object -ExpandProperty SerialNumber'],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        output = result.stdout.strip()
        if output:
            return output
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-Disk | Select-Object -ExpandProperty SerialNumber'],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        output = result.stdout.strip()
        if output:
            return output
        return "Unknown"
    except Exception:
        return "Unknown"


def get_motherboard_uuid():
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             '(Get-CimInstance -ClassName Win32_ComputerSystemProduct).UUID'],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        output = result.stdout.strip()
        if output and output != "NULL":
            return output
        return "Unknown"
    except Exception:
        return "Unknown"


def get_system_info():
    return {
        'disk_serial': get_disk_serial_number(),
        'motherboard_uuid': get_motherboard_uuid()
    }


def encrypt_data(data: str, key: bytes) -> str:
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(data.encode('utf-8'))
    return base64.b64encode(cipher.nonce + ciphertext + tag).decode('utf-8')


def decrypt_data(encrypted_data: str, key: bytes) -> str:
    data = base64.b64decode(encrypted_data.encode('utf-8'))
    nonce = data[:16]
    ciphertext = data[16:-16]
    tag = data[-16:]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')


def get_encryption_key() -> bytes:
    machine_id = get_disk_serial_number() + get_motherboard_uuid()
    machine_id = machine_id.replace("Unknown", "").strip()
    if not machine_id:
        machine_id = "default_key"
    return (machine_id * 16)[:32].encode('utf-8')


def save_hardware_info():
    if not is_packaged():
        return

    info = get_system_info()
    key = get_encryption_key()

    encrypted = encrypt_data(json.dumps(info), key)

    base_dir = os.path.dirname(sys.executable)
    save_path = os.path.join(base_dir, 'internal', 'id.json')

    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump({'data': encrypted}, f, ensure_ascii=False)


def load_hardware_info():
    if not is_packaged():
        return None

    base_dir = os.path.dirname(sys.executable)
    save_path = os.path.join(base_dir, 'internal', 'id.json')

    if not os.path.exists(save_path):
        return None

    try:
        with open(save_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        encrypted_data = data.get('data')
        if not encrypted_data:
            return None
        
        key = get_encryption_key()
        decrypted = decrypt_data(encrypted_data, key)
        return json.loads(decrypted)
    except Exception:
        return None


def compare_hardware_info():
    current_info = get_system_info()
    saved_info = load_hardware_info()

    if saved_info is None:
        return "no_id"

    if (current_info.get('disk_serial') != saved_info.get('disk_serial') or
        current_info.get('motherboard_uuid') != saved_info.get('motherboard_uuid')):
        return "mismatch"

    return "match"


if __name__ == "__main__":
    info = get_system_info()
    print(f"硬盘序列号: {info['disk_serial']}")
    print(f"主板UUID: {info['motherboard_uuid']}")
