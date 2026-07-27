import binascii
from concurrent.futures import ThreadPoolExecutor
import os
import random
import sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from flask import Flask, jsonify, request
import requests

# ---------- Fixed Import Path for Vercel Serverless ----------
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    import my_pb2
    import output_pb2
except ImportError:
    from .. import my_pb2, output_pb2

app = Flask(__name__)

# ---------- Constants ----------
MAJOR_LOGIN_URL = "https://loginbp.ggpolarbear.com/MajorLogin"
OAUTH_URL = "https://100067.connect.garena.com/oauth/guest/token/grant"
GARENA_GOOGLE_LOGIN_URL = "https://100067.connect.garena.com/oauth/login"
FREEFIRE_VERSION = "OB54"

KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

http_session = requests.Session()
http_session.verify = False

# ---------- Device Database ----------
DEVICES = [
    {
        "model": "SM-G998B",
        "android": "13",
        "api": "33",
        "cpu": "ARMv8 | 2800 | 8",
        "gpu": "Mali-G78",
        "res": ["1440", "1080"],
        "dpi": "480",
        "ram": "8192",
    },
    {
        "model": "realme C31",
        "android": "12",
        "api": "31",
        "cpu": "ARMv8 | 2000 | 8",
        "gpu": "Mali-G52",
        "res": ["720", "1600"],
        "dpi": "320",
        "ram": "4096",
    },
    {
        "model": "Mi 11",
        "android": "12",
        "api": "32",
        "cpu": "ARMv8 | 2500 | 8",
        "gpu": "Adreno 650",
        "res": ["1080", "2400"],
        "dpi": "395",
        "ram": "6144",
    },
]


def get_random_device():
    device = random.choice(DEVICES)
    android_versions = ["11", "12", "13", "14"]
    api_levels = {"11": "30", "12": "31", "13": "33", "14": "34"}
    android = random.choice(android_versions)
    api = api_levels[android]
    return {
        "model": device["model"],
        "android": android,
        "api": api,
        "cpu": device["cpu"],
        "gpu": device["gpu"],
        "width": device["res"][0],
        "height": device["res"][1],
        "dpi": device["dpi"],
        "ram": device["ram"],
        "build": f"TP1A.220624.{random.randint(100,999)}",
    }


def encrypt_data(data_bytes):
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    padded = pad(data_bytes, AES.block_size)
    return cipher.encrypt(padded)


def get_name_region_from_reward(access_token):
    try:
        url = "https://prod-api.reward.ff.garena.com/redemption/api/auth/inspect_token/"
        headers = {
            "accept": "application/json, text/plain, */*",
            "access-token": access_token,
            "user-agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36",
        }
        resp = http_session.get(url, headers=headers, timeout=4)
        data = resp.json()
        return data.get("uid"), data.get("name"), data.get("region")
    except:
        return None, None, None


def get_openid_from_shop2game(uid):
    if not uid:
        return None
    try:
        url = "https://topup.pk/api/auth/player_id_login"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36",
        }
        payload = {"app_id": 100067, "login_id": str(uid)}
        resp = http_session.post(url, headers=headers, json=payload, timeout=4)
        return resp.json().get("open_id")
    except:
        return None


# Google OAuth -> Garena Access Token Convert
def perform_google_login(google_access_token):
    payload = {
        "app_id": 100067,
        "login_type": "google",
        "access_token": google_access_token,
    }
    headers = {
        "User-Agent": "FreeFire/1.108.1 (Android)",
        "Content-Type": "application/json",
    }
    try:
        resp = http_session.post(
            GARENA_GOOGLE_LOGIN_URL, json=payload, headers=headers, timeout=5
        )
        data = resp.json()
        if "access_token" in data:
            return data["access_token"], data.get("open_id")
    except:
        pass
    return None, None


def perform_major_login(access_token, open_id):
    platforms = [8, 3, 4, 6]
    for platform_type in platforms:
        try:
            device = get_random_device()
            game_data = my_pb2.GameData()
            game_data.timestamp = "2025-01-15 10:30:45"
            game_data.game_name = "free fire"
            game_data.game_version = 1
            game_data.version_code = "1.121.0"
            game_data.os_info = f"Android OS {device['android']} / API-{device['api']} ({device['build']})"
            game_data.device_type = "Handheld"
            game_data.network_provider = "Verizon Wireless"
            game_data.connection_type = "WIFI"
            game_data.screen_width = int(device["width"])
            game_data.screen_height = int(device["height"])
            game_data.dpi = device["dpi"]
            game_data.cpu_info = device["cpu"]
            game_data.total_ram = int(device["ram"])
            game_data.gpu_name = device["gpu"]
            game_data.gpu_version = "OpenGL ES 3.2"
            game_data.user_id = (
                f"Google|{random.randint(1000000000000, 9999999999999)}"
            )
            game_data.ip_address = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
            game_data.language = "en"
            game_data.open_id = open_id
            game_data.access_token = access_token
            game_data.platform_type = platform_type
            game_data.field_99 = str(platform_type)
            game_data.field_100 = str(platform_type)
            game_data.device_form_factor = "Phone"
            game_data.device_model = device["model"]

            serialized = game_data.SerializeToString()
            encrypted = encrypt_data(serialized)
            hex_encrypted = binascii.hexlify(encrypted).decode()
            edata = bytes.fromhex(hex_encrypted)

            headers = {
                "User-Agent": f"Dalvik/2.1.0 (Linux; U; Android {device['android']}; {device['model']})",
                "Connection": "Keep-Alive",
                "Accept-Encoding": "gzip",
                "Content-Type": "application/octet-stream",
                "X-Unity-Version": "2018.4.11f1",
                "X-GA": "v1 1",
                "ReleaseVersion": FREEFIRE_VERSION,
            }

            resp = http_session.post(
                MAJOR_LOGIN_URL, data=edata, headers=headers, timeout=4
            )
            if resp.status_code == 200:
                try:
                    msg = output_pb2.Garena_420()
                    msg.ParseFromString(resp.content)
                    for field in msg.DESCRIPTOR.fields:
                        if field.name == "token":
                            return getattr(msg, field.name)
                except:
                    pass
        except:
            continue
    return None


def perform_guest_login(uid, password):
    payload = {
        "uid": uid,
        "password": password,
        "response_type": "token",
        "client_type": "2",
        "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        "client_id": "100067",
    }
    headers = {
        "User-Agent": f"GarenaMSDK/4.0.19P9({random.choice(['SM-G998B','realme C31','Mi 11'])} ;Android {random.choice(['11','12','13'])};pt;BR;)",
        "Connection": "Keep-Alive",
    }
    try:
        resp = http_session.post(
            OAUTH_URL, data=payload, headers=headers, timeout=4
        )
        data = resp.json()
        if "access_token" in data:
            return data["access_token"], data.get("open_id")
    except:
        pass
    return None, None


def process_single_item(item):
    access_token = item.get("access_token")
    google_access_token = item.get("google_token") or item.get(
        "google_access_token"
    )
    uid = item.get("uid")
    password = item.get("password")

    # জিমেইল আইডির জন্য প্রসেস
    if google_access_token:
        acc_token, open_id = perform_google_login(google_access_token)
        if not acc_token or not open_id:
            return {"status": "error", "message": "Google Login failed"}

        jwt_token = perform_major_login(acc_token, open_id)
        if jwt_token:
            return {"token": jwt_token}
        return {"status": "error", "message": "JWT generation failed"}

    # ডাইরেক্ট Garena Token এর জন্য প্রসেস
    elif access_token:
        uid_found, name, region = get_name_region_from_reward(access_token)
        if not uid_found:
            return {"status": "error", "message": "Invalid access_token"}

        open_id = get_openid_from_shop2game(uid_found)
        jwt_token = (
            perform_major_login(access_token, open_id) if open_id else None
        )

        if jwt_token:
            return {"token": jwt_token}
        return {"status": "error", "message": "JWT generation failed"}

    # গেস্ট আইডির জন্য প্রসেস
    elif uid and password:
        acc_token, open_id = perform_guest_login(uid, password)
        if not acc_token or not open_id:
            return {"status": "error", "message": "Guest login failed"}

        jwt_token = perform_major_login(acc_token, open_id)
        if jwt_token:
            return {"token": jwt_token}
        return {"status": "error", "message": "JWT generation failed"}

    else:
        return {"status": "error", "message": "Missing required fields"}


# ---------- Routes ----------
@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "api": "Universal JWT Generator API (Guest + Gmail)",
        "credit": "NABIL x7",
        "status": "running ✅",
    })


@app.route("/token", methods=["GET"])
def token_endpoint():
    access_token = request.args.get("access_token")
    google_token = request.args.get("google_token")
    uid = request.args.get("uid")
    password = request.args.get("password")

    res = process_single_item({
        "access_token": access_token,
        "google_token": google_token,
        "uid": uid,
        "password": password,
    })
    if "token" in res:
        return jsonify(res)
    return jsonify(res), 400


@app.route("/process", methods=["POST"])
def process_json():
    data = request.get_json(silent=True)
    if not data:
        return (
            jsonify({"status": "error", "message": "Invalid JSON body"}),
            400,
        )

    if not isinstance(data, list):
        res = process_single_item(data)
        if "token" in res:
            return jsonify(res)
        return jsonify(res), 400

    max_workers = min(len(data), 30)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_single_item, data))

    return jsonify(results)


app = app


def handler(request, context):
    return app(request, context)
