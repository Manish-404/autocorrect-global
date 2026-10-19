"""Which abbreviation -> word examples quoted in the header really exist in the build, and as which kind?
usage: check_header_examples.py nhi:nahi mjhe:mujhe ...   (also lists, for each word, a few real entries of each kind)"""
import json, pathlib, sys

root = pathlib.Path(__file__).parent
d = json.loads((root / 'final.json').read_text(encoding='utf-8'))
index = {}
for kind, rows in d.items():
    for c, a, _ in rows:
        index[a] = (c, kind)
for pair in sys.argv[1:]:
    a, c = pair.split(':')
    got = index.get(a)
    ok = 'OK ' if got and got[0] == c else 'MISSING/DIFFERENT'
    print(f'{ok:18} {a} -> {c}   build says: {got}')
