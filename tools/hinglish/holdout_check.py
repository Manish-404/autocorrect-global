"""Which held-out (never used for generation) real words collide with an enabled hotstring?
usage: holdout_check.py <holdout file>"""
import json, pathlib, sys
root = pathlib.Path(__file__).parent
d = json.loads((root / 'final.json').read_text(encoding='utf-8'))
words = set((root / sys.argv[1]).read_text(encoding='utf-8').split())
valid = set((root / 'valid.txt').read_text().split())
fresh = {w for w in words if w not in valid}          # words the lexicon did not already know
enabled, optional = {}, {}
for kind, rows in d.items():
    for c, a, s in rows:
        (enabled if kind in ('cur-on', 'typo-transposed', 'typo-omitted') else optional)[a] = (c, kind)
hits_on = sorted((w, enabled[w]) for w in fresh if w in enabled)
hits_off = sorted((w, optional[w]) for w in fresh if w in optional)
print(f'holdout words: {len(words)}   not already known to the lexicon: {len(fresh)}')
print(f'collide with ENABLED entries: {len(hits_on)}')
for w, (c, k) in hits_on:
    print(f'   {w} -> {c}  [{k}]')
print(f'collide with optional entries: {len(hits_off)}')
for w, (c, k) in hits_off[:30]:
    print(f'   {w} -> {c}  [{k}]')
