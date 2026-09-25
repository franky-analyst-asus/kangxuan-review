#!/usr/bin/env python3
"""Grade a photo of a child's handwritten dictation answers with the OpenAI Codex CLI.

Runs `codex exec` in headless mode, authenticated with the existing ChatGPT/Codex
subscription login (`codex login`) rather than a separate metered API key. The result
is a JSON file that the practice page can load under "複習記錄 → 核對 AI 判讀結果";
nothing is written into the review record until a parent reviews and confirms it there.

This script assumes "逐句練習" mode: the page always shows sentences in the same fixed
order as optimized-review.json, so a handwritten "第 3 句" on the photo really is
sentence #3 in that file, and this script reads the answer key straight from there —
no exported batch file needed. (local_server.py, used by the page's in-browser upload
button, does not have this limitation: it knows exactly which sentences were practiced,
in any mode, and passes that along automatically.)

Usage:
    python3 grade_photo.py --photo photo.jpg
    python3 grade_photo.py --photo p1.jpg --photo p2.jpg --range 1-5 --out result.json
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

ROOT = Path(__file__).resolve().parent
HAN_RE = re.compile(r"[㐀-鿿]")
STATUSES = {"correct", "needs_practice", "unclear", "blank"}

RULES = (
    "你是協助家長核對國小一年級國語聽寫照片的助手，請用國小一年級的標準來看，不是成人書法標準："
    "字寫得不工整、筆畫粗細不均、字有點歪或稍微超出格子，只要能認出是哪個字、主要部件和筆畫數大致正確，就算對；"
    "不要因為字不好看、不夠端正就判錯。"
    "照片上孩子會在每句前面寫題號，請先讀出照片裡實際出現的題號"
    "（不要用猜的、不要假設全部題號都在照片裡），只針對照片上真的看得到的題號逐字判讀。"
    "只根據照片上實際可見的筆跡逐字判讀，不要依正確答案推測、補字或改字。"
    "主要判斷兩件事：(1) 該寫的字有沒有寫——沒寫的字狀態填 blank；"
    "(2) 寫的字對不對——確定是正確的字填 correct，確定寫成別的字、缺重要部件、或明顯不是該字填 needs_practice。"
    "模糊、反光、遮住、被劃掉重寫看不出結果，或不確定的字狀態填 unclear，不要用猜的。"
    "不要判斷筆順。這只是輔助判讀，最後仍由家長確認，不代表最終成績。"
)


def load_master_sentences() -> list[dict]:
    """Load the full sentence bank in the same fixed order the page uses for "逐句練習"."""
    primary = ROOT / "optimized-review.json"
    fallback = ROOT / "review-data.json"
    data = json.loads((primary if primary.exists() else fallback).read_text(encoding="utf-8"))
    flat = list(data["sentences"]) if "sentences" in data else [
        sentence for lesson in data["lessons"] for sentence in lesson["sentences"]
    ]
    return [{"index": i + 1, "id": item["id"], "text": item["text"]} for i, item in enumerate(flat)]


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
    lines = [RULES, "", "以下是題庫裡每個題號對應的正確句子（僅供核對，不代表照片裡一定全部出現）：", ""]
    lines += [f"第 {item['index']} 句：{item['text']}" for item in sentences]
    lines += [
        "",
        "請先判斷照片裡實際出現哪些題號，只針對那些題號逐句、逐字列出「該句所有漢字」的判讀狀態"
        "（包含判斷為 correct 的字，不要省略），依照指定的 JSON 結構輸出，不要輸出結構以外的文字。"
        "照片裡沒出現的題號，不要放進結果。",
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
        raise RuntimeError("codex exec 執行失敗，請看終端機輸出；也可能需要先執行 `codex login`。")


def extract_result(raw: dict, by_index: dict[int, dict]) -> list[dict]:
    """Cross-check the model's raw output against the known answer key: drop any
    character it invented that isn't actually part of that sentence's text."""
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
        # The model sometimes silently omits a character instead of grading it — most
        # dangerous for exactly the characters it struggled with. Never let a target
        # character disappear with no verdict; force it to "unclear" instead.
        for char in text_chars - seen:
            characters.append({"char": char, "status": "unclear"})
        if characters:
            result_sentences.append({
                "index": source["index"], "id": source["id"], "text": source["text"], "characters": characters,
            })
    return result_sentences


def grade(sentences: list[dict], photos: list[Path]) -> list[dict]:
    with tempfile.TemporaryDirectory() as tmp:
        schema_path = Path(tmp) / "schema.json"
        raw_path = Path(tmp) / "raw.json"
        schema_path.write_text(json.dumps(build_schema(), ensure_ascii=False), encoding="utf-8")
        run_codex(build_prompt(sentences), photos, schema_path, raw_path)
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
    by_index = {item["index"]: item for item in sentences}
    return extract_result(raw, by_index)


def parse_range(text: str, total: int) -> tuple[int, int]:
    if "-" in text:
        start, end = text.split("-", 1)
        start, end = int(start), int(end)
    else:
        start = end = int(text)
    if not (1 <= start <= end <= total):
        raise SystemExit(f"--range 超出範圍，題庫共有 {total} 句。")
    return start, end


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--photo", required=True, type=Path, action="append", help="作答照片，可重複指定多張")
    parser.add_argument("--range", type=str, default=None, help="限定題號範圍，例如 1-5（預設用全部題庫當候選）")
    parser.add_argument("--out", type=Path, default=Path("判讀結果.json"), help="輸出的判讀結果 JSON 路徑")
    args = parser.parse_args()

    photos = [photo.resolve() for photo in args.photo]
    for photo in photos:
        if not photo.exists():
            raise SystemExit(f"找不到照片：{photo}")

    master = load_master_sentences()
    if args.range:
        start, end = parse_range(args.range, len(master))
        master = [item for item in master if start <= item["index"] <= end]

    try:
        result_sentences = grade(master, photos)
    except RuntimeError as error:
        raise SystemExit(str(error))

    out_path = args.out.resolve()
    payload = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sentences": result_sentences,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    needs_practice = sorted({
        c["char"] for s in result_sentences for c in s["characters"] if c["status"] in ("needs_practice", "unclear")
    })
    print(f"已判讀 {len(result_sentences)} 句（從照片辨認出的題號），寫入 {out_path}")
    if not result_sentences:
        print("沒有辨認出任何題號，請確認照片裡有清楚寫出題號，或用 --range 縮小範圍再試一次。")
    if needs_practice:
        print("初步判斷需要再練或需確認的字：" + "、".join(needs_practice))
    print("這只是 AI 的初步判斷。請到網頁「複習記錄 → 核對 AI 判讀結果」載入這個檔案，勾選確認後才會寫入紀錄。")


if __name__ == "__main__":
    main()
