#!/usr/bin/env python3
"""Grade a photo of a child's handwritten dictation answers with the OpenAI Codex CLI.

Runs `codex exec` in headless mode, authenticated with the existing ChatGPT/Codex
subscription login (`codex login`) rather than a separate metered API key. The result
is a JSON file that the practice page can load under "複習記錄 → 核對 AI 判讀結果";
nothing is written into the review record until a parent reviews and confirms it there.

Usage:
    python3 grade_photo.py --batch 聽寫批次-2026-09-25.json --photo photo.jpg
    python3 grade_photo.py --batch batch.json --photo p1.jpg --photo p2.jpg --out result.json

The batch file is produced by the page itself: practice a few sentences, tick
"我已確認這些題號都寫完了", then click "匯出批次 JSON（給自動判讀腳本）".
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HAN_RE = re.compile(r"[㐀-鿿]")
STATUSES = {"correct", "needs_practice", "unclear", "blank"}

RULES = (
    "你是協助家長核對一年級國語聽寫照片的助手。只根據照片上實際可見的筆跡逐字判讀，"
    "不要依正確答案推測、補字或改字。沒有寫的字狀態填 blank；模糊、反光、遮住或無法確定的字狀態填 "
    "unclear，不要用猜的；確定寫對的字狀態填 correct；確定寫錯或明顯缺筆畫、部件不對的字狀態填 "
    "needs_practice。不要判斷筆順。這只是輔助判讀，最後仍由家長確認，不代表最終成績。"
)


def build_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "sentences": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer"},
                        "characters": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "char": {"type": "string"},
                                    "status": {"type": "string", "enum": sorted(STATUSES)},
                                },
                                "required": ["char", "status"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["index", "characters"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["sentences"],
        "additionalProperties": False,
    }


def build_prompt(sentences: list[dict]) -> str:
    lines = [RULES, "", "照片裡包含以下題目的手寫作答，請逐句、逐字判讀：", ""]
    lines += [f"第 {item['index']} 句：{item['text']}" for item in sentences]
    lines += [
        "",
        "請針對每句列出「該句所有漢字」的判讀狀態（包含判斷為 correct 的字，不要省略），"
        "依照指定的 JSON 結構輸出，不要輸出結構以外的文字。",
    ]
    return "\n".join(lines)


def run_codex(prompt: str, photos: list[Path], schema_path: Path, out_path: Path) -> None:
    cmd = [
        "codex", "exec", prompt,
        "--sandbox", "read-only",
        "--skip-git-repo-check",
        "--output-schema", str(schema_path),
        "-o", str(out_path),
    ]
    for photo in photos:
        cmd += ["-i", str(photo)]
    result = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True)
    if result.returncode != 0 or not out_path.exists():
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit("codex exec 執行失敗，請看上面的輸出；也可能需要先執行 `codex login`。")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--batch", required=True, type=Path, help="網頁「匯出批次 JSON」產生的檔案")
    parser.add_argument("--photo", required=True, type=Path, action="append", help="作答照片，可重複指定多張")
    parser.add_argument("--out", type=Path, default=None, help="輸出的判讀結果 JSON（預設依批次檔名自動命名）")
    args = parser.parse_args()

    batch_path = args.batch.resolve()
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    sentences = batch.get("sentences")
    if not isinstance(sentences, list) or not sentences:
        raise SystemExit(f"{batch_path} 不是有效的批次檔，請用網頁重新匯出。")

    photos = [photo.resolve() for photo in args.photo]
    for photo in photos:
        if not photo.exists():
            raise SystemExit(f"找不到照片：{photo}")

    out_path = (args.out or batch_path.with_name(batch_path.stem + "-判讀結果.json")).resolve()

    with tempfile.TemporaryDirectory() as tmp:
        schema_path = Path(tmp) / "schema.json"
        raw_path = Path(tmp) / "raw.json"
        schema_path.write_text(json.dumps(build_schema(), ensure_ascii=False), encoding="utf-8")
        run_codex(build_prompt(sentences), photos, schema_path, raw_path)
        raw = json.loads(raw_path.read_text(encoding="utf-8"))

    by_index = {item["index"]: item for item in sentences}
    result_sentences = []
    for entry in raw.get("sentences", []):
        source = by_index.get(entry.get("index"))
        if not source:
            continue
        text_chars = set(HAN_RE.findall(source["text"]))
        seen: set[str] = set()
        characters = []
        for item in entry.get("characters", []):
            if not isinstance(item, dict):
                continue
            char, status = item.get("char"), item.get("status")
            if char not in text_chars or status not in STATUSES or char in seen:
                continue
            seen.add(char)
            characters.append({"char": char, "status": status})
        if characters:
            result_sentences.append({
                "index": source["index"], "id": source["id"], "text": source["text"], "characters": characters,
            })

    payload = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sentences": result_sentences,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    needs_practice = sorted({
        c["char"] for s in result_sentences for c in s["characters"] if c["status"] in ("needs_practice", "unclear")
    })
    print(f"已判讀 {len(result_sentences)} 句，寫入 {out_path}")
    if needs_practice:
        print("初步判斷需要再練或需確認的字：" + "、".join(needs_practice))
    print("這只是 AI 的初步判斷。請到網頁「複習記錄 → 核對 AI 判讀結果」載入這個檔案，勾選確認後才會寫入紀錄。")


if __name__ == "__main__":
    main()
