import asyncio
import base64
import hashlib
import hmac
import io
import json
import os
from urllib.parse import parse_qs

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, Request, Response
from omnivoice import OmniVoice

app = FastAPI()

_omni_model = None


def _load_model():
    global _omni_model
    if _omni_model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32
        print(f"Loading OmniVoice on {device}...")
        _omni_model = OmniVoice.from_pretrained(
            "k2-fsa/OmniVoice",
            device_map=device,
            dtype=dtype,
        )
        print("OmniVoice loaded.")
    return _omni_model


AUTH_USERNAME = os.getenv("TTS_AUTH_USERNAME", "")
AUTH_PASSWORD = os.getenv("TTS_AUTH_PASSWORD", "")
SESSION_SECRET = os.getenv("TTS_SESSION_SECRET", "")
SESSION_COOKIE_NAME = "tts_session"
VOICE_ALIASES = {
    "en": "default_en",
    "english": "default_en",
    "default_en": "default_en",
    "mimo_en": "default_en",
    "zh": "default_zh",
    "chinese": "default_zh",
    "default_zh": "default_zh",
    "mimo_zh": "default_zh",
    "default": "mimo_default",
    "mimo_default": "mimo_default",
}


def auth_enabled() -> bool:
    return bool(AUTH_USERNAME and AUTH_PASSWORD and SESSION_SECRET)


def create_session_token(username: str) -> str:
    signature = hmac.new(
        SESSION_SECRET.encode("utf-8"),
        username.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{username}:{signature}"


def validate_session_token(token: str) -> bool:
    if not token or ":" not in token:
        return False
    username, signature = token.split(":", 1)
    if username != AUTH_USERNAME:
        return False

    expected_signature = hmac.new(
        SESSION_SECRET.encode("utf-8"),
        username.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)


def validate_basic_auth(request: Request) -> bool:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        return False

    b64_value = auth_header[6:].strip()
    try:
        decoded = base64.b64decode(b64_value).decode("utf-8")
    except Exception:
        return False

    if ":" not in decoded:
        return False
    username, password = decoded.split(":", 1)
    return username == AUTH_USERNAME and password == AUTH_PASSWORD


def is_authorized(request: Request) -> bool:
    if not auth_enabled():
        return True

    session_token = request.cookies.get(SESSION_COOKIE_NAME, "")
    if validate_session_token(session_token):
        return True

    return validate_basic_auth(request)


def unauthorized_response() -> Response:
    response = Response(status_code=401, content="Unauthorized")
    response.headers["WWW-Authenticate"] = 'Basic realm="TTS Login"'
    return response


VOICE_INSTRUCTS = {
    "default_en": "female, american accent",
    "mimo_en": "female, american accent",
    "default_zh": "female",
    "mimo_zh": "female",
    "mimo_default": "female",
}

LANG_MAP = {
    "en": "en", "english": "en", "default_en": "en", "mimo_en": "en",
    "zh": "zh", "chinese": "zh", "default_zh": "zh", "mimo_zh": "zh",
}


def resolve_instruct(lang: str) -> str:
    voice = resolve_voice(lang)
    return VOICE_INSTRUCTS.get(voice, "female")


def resolve_language(lang: str) -> str | None:
    if not lang:
        return None
    return LANG_MAP.get(lang.strip().lower())


def resolve_voice(lang: str) -> str:
    if not lang:
        return "mimo_default"
    return VOICE_ALIASES.get(lang.strip().lower(), "mimo_default")


def resolve_speed(lang: str, speed: str) -> float:
    if isinstance(speed, str) and speed.strip():
        try:
            return float(speed)
        except ValueError:
            pass
    if isinstance(lang, str) and lang.strip().lower() in {"zh", "chinese", "default_zh", "mimo_zh"}:
        return 1.05
    return 1.0


async def parse_request_payload(request: Request):
    # Prefer JSON body; if client sends plain text or query params, fallback gracefully.
    raw = await request.body()
    if raw:
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            text_body = raw.decode("utf-8", errors="ignore").strip()
            if text_body:
                return {"text": text_body}

    return dict(request.query_params)


def extract_lang(data: dict) -> str:
    lang = data.get("lang") or data.get("locale") or data.get("voice")
    if isinstance(lang, str):
        return lang
    return ""


@app.get("/auth/login")
async def login_page():
    html = """
    <!doctype html>
    <html lang=\"en\">
    <head>
      <meta charset=\"utf-8\" />
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
      <title>TTS Login</title>
      <style>
        body { font-family: sans-serif; max-width: 420px; margin: 36px auto; padding: 0 12px; }
        label { display: block; margin-top: 12px; }
        input { width: 100%; padding: 8px; box-sizing: border-box; }
        button { margin-top: 14px; padding: 8px 14px; }
      </style>
    </head>
    <body>
      <h2>TTS Login</h2>
      <form method=\"post\" action=\"/auth/login\">
        <label>Username</label>
        <input type=\"text\" name=\"username\" required />
        <label>Password</label>
        <input type=\"password\" name=\"password\" required />
        <button type=\"submit\">Login</button>
      </form>
    </body>
    </html>
    """
    return Response(content=html, media_type="text/html")


@app.post("/auth/login")
async def login_submit(request: Request):
    if not auth_enabled():
        return Response(status_code=200, content="Auth disabled")

    raw_body = await request.body()
    form = parse_qs(raw_body.decode("utf-8", errors="ignore"))
    username = (form.get("username") or [""])[0]
    password = (form.get("password") or [""])[0]

    if username != AUTH_USERNAME or password != AUTH_PASSWORD:
        return Response(status_code=401, content="Invalid username or password")

    redirect_to = request.query_params.get("redirect", "/auth/check")
    response = Response(status_code=302)
    response.headers["Location"] = redirect_to
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(username),
        httponly=True,
        secure=(request.url.scheme == "https"),
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )
    return response


@app.get("/auth/check")
async def auth_check(request: Request):
    if is_authorized(request):
        return Response(status_code=200, content="OK")
    return unauthorized_response()


@app.get("/auth/logout")
async def auth_logout():
    response = Response(status_code=200, content="Logged out")
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response


@app.api_route("/tts", methods=["GET", "POST"])
async def mimo_tts(request: Request):
    try:
        # if not is_authorized(request):
        #     return unauthorized_response()

        data = await parse_request_payload(request)
        text = data.get("text", "")

        if not text:
            return Response(status_code=400, content="No text provided")

        lang = extract_lang(data)
        speed_val = resolve_speed(lang, data.get("speed", ""))
        instruct = resolve_instruct(lang)
        language = resolve_language(lang)

        omni_model = await asyncio.to_thread(_load_model)
        audios = await asyncio.to_thread(
            omni_model.generate,
            text=text, language=language,
            instruct=instruct, speed=speed_val,
        )

        buf = io.BytesIO()
        sf.write(buf, audios[0], omni_model.sampling_rate, format="wav")
        wav_bytes = buf.getvalue()

        return Response(content=wav_bytes, media_type="audio/wav")

    except Exception as e:
        print(f"Error: {e}")
        return Response(status_code=500, content=str(e))
