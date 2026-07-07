import os
import requests

BASE_URL = "http://127.0.0.1:8002"
LOGIN_URL = f"{BASE_URL}/auth/login"
TTS_URL = f"{BASE_URL}/tts"
USERNAME = os.getenv("TTS_AUTH_USERNAME", "")
PASSWORD = os.getenv("TTS_AUTH_PASSWORD", "")


def _login(session: requests.Session):
    if not USERNAME or not PASSWORD:
        return
    r = session.post(LOGIN_URL, data={"username": USERNAME, "password": PASSWORD}, timeout=30)
    if r.status_code not in (200, 302):
        raise RuntimeError(f"Login failed: {r.status_code} {r.text}")
    print("  auth: ok")


def _test_case(session: requests.Session, label: str, payload: dict, filename: str):
    print(f"\n[{label}] {payload}")
    r = session.post(TTS_URL, json=payload, timeout=120)
    if r.status_code == 200:
        path = os.path.join(os.path.dirname(__file__) or ".", filename)
        with open(path, "wb") as f:
            f.write(r.content)
        print(f"  -> {filename} ({len(r.content)} bytes, {r.headers.get('Content-Type')})")
    else:
        print(f"  FAIL {r.status_code}: {r.text}")


session = requests.Session()
_login(session)

# 中文（lang 自动识别 → instruct="female", language="zh"）
_test_case(session, "zh", {"text": "你好，世界！这是一个本地 TTS 测试。"}, "result_zh.wav")

# 英文（显式 lang="en" → instruct="female, american accent", language="en"）
_test_case(session, "en", {"text": "Hello world, this is a local TTS test.", "lang": "en"}, "result_en.wav")

# 无 lang（fallback → instruct="female", language=None → auto voice）
_test_case(session, "default", {"text": "This is the default voice without specifying language."}, "result_default.wav")

# 自定义 speed（speed=1.2）
_test_case(session, "speed", {"text": "This sentence is spoken at a slightly faster speed.", "speed": "1.2"}, "result_speed.wav")

# GET 请求（查询参数方式，兼容 Legado）
_test_case(session, "get", {"text": "GET request test from query parameters.", "lang": "en"}, "result_get.wav")
