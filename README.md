# mimo-tts-relay

This project forwards MiMo TTS and exposes it as a TTS API that can be used directly by Legado (开源阅读).

Its main purpose is exactly this: convert MiMo TTS into a Legado-friendly TTS service interface.

## What it does

- Accepts text requests from clients such as Legado.
- Calls Xiaomi MiMo speech synthesis (`mimo-v2-tts`).
- Returns generated WAV audio.
- Supports language-based built-in voice selection via URL params (`en`, `zh`, or default).
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

## Legado setup

Use the following values in Legado TTS server settings.

Protocol note:

- This app serves plain HTTP by default.
- If you need HTTPS, put it behind your own reverse proxy/TLS terminator (for example Nginx or Caddy).

- url:
	http://your-domain/tts?text={{speakText}}&lang=zh
- Content_Type:
	audio/wav
- concurrentRate:
	1

If auth is enabled in this relay, use login flow values below.

- loginUrl:
	http://your-domain/auth/login?redirect=/auth/check
- loginCheckJs:
	(result || "").indexOf("OK") > -1
- header:
	Leave empty when using login cookie session.

Notes for loginCheckJs:

- This relay returns `OK` on `/auth/check` when the session cookie is valid.
- The `loginUrl` above redirects to `/auth/check` after successful login, so `result` should be the `/auth/check` response body.
- The example checks whether response text contains `OK`.
- If your Legado version uses a different variable name, keep the same logic: check whether the response content contains `OK`.

Language and speed notes:

- lang=zh uses Chinese voice default_zh.
- lang=en uses English voice default_en.
- no lang uses mimo_default.
- when speed is not provided: zh defaults to 变快, others default to Speed up.
- you can override speed by passing speed in request params.

## License

MIT
