#!/usr/bin/env python3
"""Local helper server so the practice page can upload a photo and get an AI reading
back directly — no manual JSON export/import, no terminal command per session.

Serves index.html itself, plus one endpoint the page calls with `fetch`:
  POST /api/grade   {sentences, photos}   -> {sentences: [...]}

Calls the OpenAI Codex CLI (`codex exec`), authenticated with the existing ChatGPT/Codex
subscription login (`codex login`) — no separate metered API key.

Run this on the same Mac that has `codex` installed and logged in:
    python3 local_server.py
Then open the printed http://<lan-ip>:8787/ address on the parent's phone, as long
as the phone is on the same WiFi as this Mac. http://localhost:8787/ works on the Mac
itself. Leave this running while you want the page's upload button to work; closing
the terminal (Ctrl+C) stops it — the page still works without it, just falls back to
the manual "產生核對文字（給 ChatGPT）" / "載入判讀結果 JSON" flow.
"""
from __future__ import annotations

import base64
import json
import socket
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import grade_photo

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
PORT = 8787


def lan_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A002 - quiet default logging
        pass

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0 or length > 30_000_000:
            raise ValueError("請求內容太大或是空的（可能是照片檔案太大）。")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            body = INDEX.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/health":
            self._send_json(200, {"ok": True})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        try:
            if self.path == "/api/grade":
                self._handle_grade()
            else:
                self.send_response(404)
                self.end_headers()
        except (ValueError, RuntimeError) as error:
            self._send_json(400, {"error": str(error)})
        except Exception as error:  # noqa: BLE001 - report back instead of dropping the connection
            self._send_json(500, {"error": f"未預期的錯誤：{error}"})

    def _handle_grade(self) -> None:
        payload = self._read_json()
        sentences = payload.get("sentences")
        photos_b64 = payload.get("photos")
        if not isinstance(sentences, list) or not sentences:
            raise ValueError("缺少題目內容，請重新從練習頁操作。")
        if not isinstance(photos_b64, list) or not photos_b64:
            raise ValueError("沒有收到照片。")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            photo_paths = []
            for i, data_url in enumerate(photos_b64):
                header, _, encoded = str(data_url).partition(",")
                ext = ".png" if "png" in header else ".jpg"
                photo_path = tmp_path / f"photo-{i}{ext}"
                photo_path.write_bytes(base64.b64decode(encoded))
                photo_paths.append(photo_path)

            result_sentences = grade_photo.grade(sentences, photo_paths)

        self._send_json(200, {"schemaVersion": 1, "sentences": result_sentences})


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    ip = lan_ip()
    print(f"這台電腦：   http://localhost:{PORT}/")
    print(f"手機（同 WiFi）：http://{ip}:{PORT}/")
    print("開著這個視窗，網頁的「拍照上傳」才能用；按 Ctrl+C 結束。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()
