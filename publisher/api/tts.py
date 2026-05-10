"""
책방 리더기용 TTS 합성 (Vercel Python serverless function).

POST /api/tts
Body JSON: { "text": "...", "voice": "ko-KR-InJoonNeural", "rate": "+0%" }
응답: audio/mpeg (mp3 binary)

엔진: edge-tts (Microsoft Edge 의 TTS 엔드포인트, 무료).
브라우저 OS 음성과 별개로 InJoon(남성) 같은 고품질 한국어 합성을 제공한다.
"""
from http.server import BaseHTTPRequestHandler
import asyncio
import json

import edge_tts


DEFAULT_VOICE = "ko-KR-InJoonNeural"
MAX_TEXT_LEN = 5000  # 한 요청 본문 최대 길이 (문장 단위 호출이라 충분)
ALLOWED_VOICE_PREFIX = "ko-"   # 한국어 음성만 허용


async def synth(text: str, voice: str, rate: str) -> bytes:
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    chunks = []
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)


class handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length else ""
            data = json.loads(body) if body else {}

            text = (data.get("text") or "").strip()
            voice = (data.get("voice") or DEFAULT_VOICE).strip()
            rate = (data.get("rate") or "+0%").strip()

            if not text:
                return self._error(400, "text required")
            if len(text) > MAX_TEXT_LEN:
                return self._error(413, f"text too long (max {MAX_TEXT_LEN})")
            if not voice.startswith(ALLOWED_VOICE_PREFIX):
                return self._error(400, "ko-* voice only")

            audio = asyncio.run(synth(text, voice, rate))
            if not audio:
                return self._error(502, "empty audio")

            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Content-Length", str(len(audio)))
            # 같은 (text, voice, rate) 조합은 항상 같은 결과 → 강한 캐시 OK.
            # 본 응답은 클라이언트 IndexedDB 도 캐시하므로 CDN 까지는 짧게.
            self.send_header("Cache-Control", "public, max-age=86400, immutable")
            self._cors()
            self.end_headers()
            self.wfile.write(audio)
        except json.JSONDecodeError:
            self._error(400, "invalid JSON body")
        except Exception as e:
            self._error(500, f"{type(e).__name__}: {e}")

    def _error(self, code: int, msg: str):
        body = json.dumps({"error": msg}, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)
