"""Validate the compact, full-year dictation sentence bank."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
source = json.loads((ROOT / "vocabulary.json").read_text())
optimized = json.loads((ROOT / "optimized-review.json").read_text())
reference = json.loads((ROOT / "review-data.json").read_text())

target = set(char for lesson in source["lessons"] for char in lesson["characters"])
allowed = list(dict.fromkeys(char for lesson in source["lessons"] for term in lesson["terms"] for char in term))
assert optimized["allowedCharacters"] == allowed
assert (optimized["schoolYear"], optimized["publisher"], optimized["grade"]) == (
    source["schoolYear"], source["publisher"], source["grade"]
)
assert len(target) == 262 and len(allowed) == 263

seen_ids = set()
covered = set()
lengths = []
for sentence in optimized["sentences"]:
    assert sentence["id"] not in seen_ids, sentence["id"]
    seen_ids.add(sentence["id"])
    han = re.findall(r"[\u4e00-\u9fff]", sentence["text"])
    assert set(han) <= set(allowed), (sentence["id"], set(han) - set(allowed))
    assert len(han) <= 24, (sentence["id"], len(han))
    expected_targets = list(dict.fromkeys(char for char in han if char in target))
    assert sentence["targets"] == expected_targets, sentence["id"]
    covered.update(expected_targets)
    lengths.append(len(han))

assert covered == target, target - covered
old_sentences = [sentence for lesson in reference["lessons"] for sentence in lesson["sentences"]]
old_han = sum(len(re.findall(r"[\u4e00-\u9fff]", sentence["text"])) for sentence in old_sentences)
stats = optimized["statistics"]
assert stats == {
    "sourceSentenceCount": len(old_sentences),
    "sourceTotalHanCharacters": old_han,
    "sentenceCount": len(lengths),
    "totalHanCharacters": sum(lengths),
    "maxHanCharactersPerSentence": max(lengths),
    "allowedCharacterCount": len(allowed),
    "targetCharacterCount": len(target),
    "coveredTargetCount": len(covered),
    "uncoveredCharacters": [],
}
print(
    f"OK: {len(lengths)} sentences, {sum(lengths)} Han characters, "
    f"{len(covered)}/{len(target)} targets covered, no out-of-list characters."
)
