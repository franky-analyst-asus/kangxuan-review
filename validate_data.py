"""Check source preservation, cumulative character boundaries, and target coverage."""
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parent
source = json.loads((root / 'vocabulary.json').read_text())
review = json.loads((root / 'review-data.json').read_text())
assert len(source['lessons']) == len(review['lessons']) == 18
allowed = set()
ids = set()
all_targets = set()
for original, lesson in zip(source['lessons'], review['lessons']):
    for key in ('id', 'semester', 'title', 'url', 'terms', 'characters', 'phrases'):
        assert original[key] == lesson[key], (lesson['id'], key)
    allowed.update(''.join(lesson['terms']))
    covered = set()
    for sentence in lesson['sentences']:
        assert sentence['id'] not in ids
        ids.add(sentence['id'])
        han = set(re.findall(r'[\u4e00-\u9fff]', sentence['text']))
        assert han <= allowed, (sentence['id'], han - allowed)
        expected = [char for char in lesson['characters'] if char in han]
        assert expected == sentence['targets'], sentence['id']
        assert expected, ('No current-lesson targets', sentence['id'])
        covered.update(expected)
    assert covered == set(lesson['characters']), (lesson['id'], set(lesson['characters']) - covered)
    all_targets.update(covered)
assert len(all_targets) == 262
print(f'OK: {len(review["lessons"])} lessons, {len(ids)} sentences, {len(all_targets)} target characters; zero future-lesson or out-of-list characters.')
