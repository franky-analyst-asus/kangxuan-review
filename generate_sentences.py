#!/usr/bin/env python3
"""Draft new dictation sentences for characters that still need practice.

Runs `codex exec` in headless mode, authenticated with the existing ChatGPT/Codex
subscription login (`codex login`) rather than a separate metered API key. The output
is a plain-text draft for a parent to read; nothing is added to the practice page
automatically. Sentences you approve should be pasted into the page's
"複習記錄 → 貼上家長審核後的新句" box, which re-checks them before adding.

Usage:
    python3 generate_sentences.py --weak 雨 停 兒
    python3 generate_sentences.py --record 康軒國語複習記錄-2026-09-25.json
    python3 generate_sentences.py --grading 聽寫批次-2026-09-25-判讀結果.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HAN_RE = re.compile(r"[㐀-鿿]")
PUNCTUATION = set("，。！？、；：「」『』（）…,.!?;:()\"' ")
MAX_HAN = 30


def load_allowed_characters() -> list[str]:
    vocabulary = json.loads((ROOT / "vocabulary.json").read_text(encoding="utf-8"))
    seen: list[str] = []
    for lesson in vocabulary["lessons"]:
        for term in lesson["terms"]:
            for ch in term:
                if HAN_RE.match(ch) and ch not in seen:
                    seen.append(ch)
    return seen


def load_existing_sentences() -> list[str]:
    texts: list[str] = []
    for name in ("review-data.json", "optimized-review.json"):
        path = ROOT / name
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for lesson in data.get("lessons", []):
            texts += [s["text"] for s in lesson["sentences"]]
        texts += [s["text"] for s in data.get("sentences", [])]
    return texts


def collect_weak_characters(args: argparse.Namespace) -> list[str]:
    chars: set[str] = set()
    if args.weak:
        chars.update(ch for ch in args.weak if HAN_RE.match(ch))
    if args.record:
        record = json.loads(args.record.read_text(encoding="utf-8"))
        chars.update(record.get("weakCharacters", []))
    if args.grading:
        grading = json.loads(args.grading.read_text(encoding="utf-8"))
        for sentence in grading.get("sentences", []):
            for c in sentence.get("characters", []):
                if c.get("status") in ("needs_practice", "unclear"):
                    chars.add(c["char"])
    return sorted(chars)


def build_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "sentences": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "covers": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["text", "covers"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["sentences"],
        "additionalProperties": False,
    }


def build_prompt(weak: list[str], allowed: list[str], existing: list[str]) -> str:
    return "\n\n".join([
        "你是協助家長準備國小一年級國語複習的老師，請為「需要再練的字」設計新的聽寫短句。",
        "規則：\n"
        "1) 只能使用下方允許漢字，不能自行加入字表外的字或同義字；\n"
        "2) 用少量句子盡量涵蓋所有需練字，同一個字可以重複練習；\n"
        "3) 每句 8-20 個漢字為主，最多 30 個漢字，標點不計字數；\n"
        "4) 句子要自然、適合一年級，不要為了塞字而不通順；\n"
        "5) 不要照抄下方列出的現有句子，同一個字盡量換詞或換情境；\n"
        "6) 若某字很難自然放入句子，可以不勉強塞入，不用湊。",
        "需要再練的字：" + "、".join(weak),
        "允許使用的漢字：" + "".join(allowed),
        "請不要照抄以下現有句子：\n" + "\n".join(existing),
        "請依照指定的 JSON 結構輸出：每句包含 text（句子本文，只含漢字與標點，不放注音或拼音）"
        "與 covers（這句實際涵蓋到的需練字）。",
    ])


def validate_sentence(text: str, allowed: set[str], weak: set[str], existing_keys: set[str]) -> str | None:
    han = HAN_RE.findall(text)
    if not text.strip() or not han or len(han) > MAX_HAN:
        return f"每句需有 1～{MAX_HAN} 個漢字"
    bad = sorted({ch for ch in text if ch not in allowed and ch not in PUNCTUATION and HAN_RE.match(ch)})
    if bad:
        return f"含有字表外的字：{'、'.join(bad)}"
    if any(ch not in allowed and ch not in PUNCTUATION and not HAN_RE.match(ch) for ch in text):
        return "含有不支援的符號"
    if not any(ch in weak for ch in han):
        return "沒有包含任何需練字"
    if re.sub(r"\s+", "", text) in existing_keys:
        return "與現有題庫或已產生的句子重複"
    return None


def run_codex(prompt: str, schema_path: Path, out_path: Path) -> None:
    cmd = [
        "codex", "exec", prompt,
        "--sandbox", "read-only",
        "--skip-git-repo-check",
        "--output-schema", str(schema_path),
        "-o", str(out_path),
    ]
    result = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True)
    if result.returncode != 0 or not out_path.exists():
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit("codex exec 執行失敗，請看上面的輸出；也可能需要先執行 `codex login`。")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--weak", nargs="*", help="直接列出需要再練的字，例如 --weak 雨 停 兒")
    parser.add_argument("--record", type=Path, help="網頁匯出的複習記錄 JSON（採用其中的 weakCharacters）")
    parser.add_argument("--grading", type=Path, help="grade_photo.py 產生的判讀結果 JSON（採用 needs_practice/unclear 的字）")
    parser.add_argument("--out", type=Path, default=ROOT / "draft-new-sentences.txt", help="草稿輸出路徑")
    args = parser.parse_args()

    weak = collect_weak_characters(args)
    if not weak:
        raise SystemExit("沒有任何需要再練的字，請至少用 --weak / --record / --grading 其中一種指定。")

    allowed = load_allowed_characters()
    allowed_set = set(allowed)
    unknown = [c for c in weak if c not in allowed_set]
    if unknown:
        raise SystemExit(f"這些字不在字表內，無法出題：{'、'.join(unknown)}")

    existing = load_existing_sentences()
    existing_keys = {re.sub(r"\s+", "", t) for t in existing}
    weak_set = set(weak)

    with tempfile.TemporaryDirectory() as tmp:
        schema_path = Path(tmp) / "schema.json"
        raw_path = Path(tmp) / "raw.json"
        schema_path.write_text(json.dumps(build_schema(), ensure_ascii=False), encoding="utf-8")
        run_codex(build_prompt(weak, allowed, existing), schema_path, raw_path)
        raw = json.loads(raw_path.read_text(encoding="utf-8"))

    accepted: list[str] = []
    rejected: list[tuple[str, str]] = []
    seen_keys = set(existing_keys)
    for item in raw.get("sentences", []):
        text = (item.get("text") or "").strip()
        reason = validate_sentence(text, allowed_set, weak_set, seen_keys)
        if reason:
            rejected.append((text, reason))
            continue
        accepted.append(text)
        seen_keys.add(re.sub(r"\s+", "", text))

    args.out.write_text("\n".join(accepted) + ("\n" if accepted else ""), encoding="utf-8")

    covered = {ch for text in accepted for ch in HAN_RE.findall(text) if ch in weak_set}
    uncovered = sorted(weak_set - covered)

    print(f"已產生 {len(accepted)} 句草稿，寫入 {args.out}")
    if rejected:
        print(f"另外 {len(rejected)} 句被程式擋下（未寫入草稿）：")
        for text, reason in rejected:
            print(f"  - {text!r}：{reason}")
    if uncovered:
        print("尚未覆蓋到的需練字：" + "、".join(uncovered))
    print("這是 AI 草稿，不會自動加入練習。請先自己讀過確認合理，"
          "再把接受的句子貼到網頁「複習記錄 → 貼上家長審核後的新句」欄位。")


if __name__ == "__main__":
    main()
