>基于 mimo-tts-server(https://github.com/xiangyuw1/mimo-tts-relay) 修改

# OmniVoice TTS Relay Server

基于小米 OmniVoice 的本地 TTS 中转服务，兼容 Legado 阅读 APP 的 TTS 接口。

## 环境要求

- Python 3.10+
- 至少 8 GB 可用内存（CPU 推理建议 16 GB+）
- 约 6 GB 磁盘空间（模型下载）

## 安装

### 1. 创建虚拟环境并安装依赖

```bash
cd mimo-tts-relay

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 安装依赖
pip install fastapi uvicorn omnivoice soundfile numpy
```

安装 `omnivoice` 时会自动拉取依赖的 PyTorch（CPU 版）。如果需要 CUDA 加速：

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

### 2. 下载模型

首次启动时会自动从 HuggingFace 下载模型 `k2-fsa/OmniVoice`（约 6 GB）。也可以提前手动下载：

```bash
# 安装 huggingface_hub
pip install huggingface_hub

# 下载模型到 HuggingFace 缓存目录
huggingface-cli download k2-fsa/OmniVoice
```

默认缓存位置：
- Windows: `%USERPROFILE%\.cache\huggingface\hub`
- macOS/Linux: `~/.cache/huggingface/hub`

## 启动服务

### 无认证模式（默认，适合局域网）

```bash
python main.py
```

或使用 uvicorn 直接启动：

```bash
uvicorn main:app --host 0.0.0.0 --port 8002
```

### 启用认证

设置环境变量后启动：

```bash
# Windows PowerShell
$env:TTS_AUTH_USERNAME="myuser"
$env:TTS_AUTH_PASSWORD="mypassword"
$env:TTS_SESSION_SECRET="your-random-secret-here"
python main.py

# macOS / Linux
TTS_AUTH_USERNAME="myuser" TTS_AUTH_PASSWORD="mypassword" TTS_SESSION_SECRET="your-random-secret-here" python main.py
```

### 启动参数

建议使用 uvicorn 以获得更好的性能和日志：

```bash
uvicorn main:app --host 0.0.0.0 --port 8002 --log-level info
```

## API 接口

### `POST /tts`

请求体（JSON）：

```json
{
  "text": "要合成的文本",
  "lang": "zh",
  "speed": "1.0"
}
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `text` | 待合成文本（必填） | - |
| `lang` | 语言：`zh` / `en` / `chinese` / `english` | 自动检测 |
| `speed` | 语速倍率，如 `1.2` | `1.0`（中文默认 `1.05`） |
| `locale` / `voice` | lang 的别名，兼容 Legado | - |

成功返回 `audio/wav` 二进制流。

也支持 GET 请求（查询参数方式）：

```
GET /tts?text=你好&lang=zh
```

plain text 请求体也兼容：

```
POST /tts
Content-Type: text/plain

你好世界
```

### `GET /auth/login`

认证登录页面（仅启用认证时可用）。

### `GET /auth/check`

检查会话是否有效。

### `GET /auth/logout`

登出。

## 测试

### 运行测试客户端

```bash
python test-client.py
```

会生成以下文件：
- `result_zh.wav` — 中文测试
- `result_en.wav` — 英文测试
- `result_default.wav` — 默认语音测试
- `result_speed.wav` — 自定义语速测试
- `result_get.wav` — GET 请求测试

## 与 Legado 阅读集成

在 Legado 阅读 APP 的「语音引擎设置」中添加：

- **URL**: `http://<服务器IP>:8002/tts`
- **请求方式**: POST
- **Body**: `{"text":"%s","lang":"zh"}`
- **Content-Type**: `application/json`
- **返回格式**: WAV（audio/wav）

> 建议在局域网内使用，首次请求需要加载模型（约 20-60 秒），之后秒回。

## 故障排查

**模型加载慢或失败**
- 检查网络是否能访问 HuggingFace
- 可设置 `HF_ENDPOINT=https://hf-mirror.com` 使用国内镜像
- 确认磁盘空间充足

**内存不足**
- CPU 推理约需 8-12 GB 内存
- 尝试关闭其他应用或增加 swap

**首次请求超时**
- 首次请求会加载模型到内存，耗时较长
- 可以在启动后先访问一次 `/tts?text=hello` 预热

**声音不对**
- OmniVoice 的 instruct 只支持固定的标签：
  - 性别: `male` / `female`
  - 年龄: `child` / `teenager` / `young adult` / `middle-aged` / `elderly`
  - 音高: `low pitch` / `moderate pitch` / `high pitch` / `very high pitch`
  - 口音: `american accent` / `british accent` / `indian accent` 等
- 详见 `VENV_PATH/Lib/site-packages/omnivoice/utils/voice_design.py`





<del>
# mimo-tts-relay

This project forwards MiMo TTS and exposes it as a TTS API that can be used directly by Legado (开源阅读).

Its main purpose is exactly this: convert MiMo TTS into a Legado-friendly TTS service interface.

## What it does

- Accepts text requests from clients such as Legado.
- Calls Xiaomi MiMo speech synthesis (defaults to `mimo-v2.5-tts`).
- Returns generated WAV audio.
- Supports language-based built-in voice selection via URL params (`en`, `zh`, or default).
- Supports specifying the version via the `v` URL param (`&v=2` or `&v=2.5`). The default is `v=2.5`.
- Supports optional speed style control via request params.
- Supports session-based auth endpoints for clients that use a login flow.

## Run

Set required environment variables:

- MIMO_API_KEY

Optional auth variables (set all three to enable login/session auth):

- TTS_AUTH_USERNAME
- TTS_AUTH_PASSWORD
- TTS_SESSION_SECRET

Install dependencies and start service:

```bash
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8080
```

Quick local test:

```bash
uv run python test-client.py
```
</del>
## Legado setup

Use the following values in Legado TTS server settings.

Protocol note:

- This app serves plain HTTP by default.
- If you need HTTPS, put it behind your own reverse proxy/TLS terminator (for example Nginx or Caddy).

- url:
	`http://your-domain/tts?text={{speakText}}&lang=zh`
- Content_Type:
	audio/wav
- concurrentRate:
	1

If auth is enabled in this relay, use login flow values below.

- loginUrl:
	http://your-domain/auth/login
- header:
	Leave empty when using login cookie session.


<del>
Language and speed notes:

- lang=zh uses Chinese voice 冰糖 (MiMo v2.5) or default_zh (MiMo v2).
- lang=en uses English voice Mia (MiMo v2.5) or default_en (MiMo v2).
- no lang uses mimo_default.
- when speed is not provided: zh defaults to 变快, en defaults to Speed up.
- you can override speed by passing speed in request params.
- specify version via `v` (for example `&v=2` or `&v=2.5`); otherwise `mimo-v2.5-tts` is used by default.
</del>
## License

MIT
