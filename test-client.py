import os
import requests

# 1. 配置你的环境参数
BASE_URL = "http://127.0.0.1:8080"
LOGIN_URL = f"{BASE_URL}/auth/login"
CHECK_URL = f"{BASE_URL}/auth/check"
TTS_URL = f"{BASE_URL}/tts"
USERNAME = os.getenv("TTS_AUTH_USERNAME", "")
PASSWORD = os.getenv("TTS_AUTH_PASSWORD", "")

# 2. 模拟 Legado 传过去的文本
payload = {
    "text": "你好，世界！这是一个测试。"
}

print("正在请求中转服务器...")

try:
    # if not USERNAME or not PASSWORD:
    #     raise RuntimeError("请先设置 TTS_AUTH_USERNAME 和 TTS_AUTH_PASSWORD 环境变量")

    session = requests.Session()

    # 先访问登录页，拿到初始 cookie / csrf 等信息（如果后续需要）
    login_page = session.get(LOGIN_URL, timeout=30)
    if login_page.status_code != 200:
        raise RuntimeError(f"登录页访问失败: {login_page.status_code}")

    # 用表单方式提交用户名和密码，服务端会写入会话 Cookie
    login_response = session.post(
        LOGIN_URL,
        data={"username": USERNAME, "password": PASSWORD},
        timeout=30,
        allow_redirects=False,
    )
    if login_response.status_code not in (200, 302):
        raise RuntimeError(f"登录失败: {login_response.status_code} {login_response.text}")

    # 验证会话是否建立成功
    check_response = session.get(CHECK_URL, timeout=30)
    if check_response.status_code != 200:
        raise RuntimeError(f"会话校验失败: {check_response.status_code} {check_response.text}")

    # 登录成功后，再用同一个 session 调用 TTS
    response = session.post(TTS_URL, json=payload, timeout=60)
    
    # 检查 HTTP 状态码
    if response.status_code == 200:
        # 如果成功，把拿到的二进制流写成 wav
        with open("result.wav", "wb") as f:
            f.write(response.content)
        print("✅ 测试成功！音频已保存为 result.wav，快去听听吧。")
        print("Content-Type:", response.headers.get("Content-Type"))
    elif response.status_code == 401:
        print("❌ 401 认证失败：请检查 Nginx 密码是否正确。")
    else:
        print(f"❌ 失败，状态码：{response.status_code}")
        print("服务器返回的错误信息：", response.text)

except Exception as e:
    print(f"❌ 请求发生异常：{e}")