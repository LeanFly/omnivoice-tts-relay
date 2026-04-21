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

## License

MIT
