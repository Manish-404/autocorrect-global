import pathlib, sys
root = pathlib.Path(__file__).parent
res = (root / 'result.txt').read_text(encoding='utf-8-sig')
if res.startswith('ABORT'):
    sys.exit(res)
got = [l.rstrip('\r') for l in res.replace('\r\n', '\n').split('\n')]
if got and got[-1] == '':
    got.pop()
typed = (root / 'tests.txt').read_text().split('\n')[:-1]
want = (root / 'expected.txt').read_text().split('\n')[:-1]
print(f'typed {len(typed)}  lines read back {len(got)}  expected {len(want)}')
bad = [(t, w, g) for t, w, g in zip(typed, want, got) if w != g]
print(f'passed {len(want) - len(bad)} / {len(want)}')
for t, w, g in bad[:60]:
    print(f'   typed {t!r:22} wanted {w!r:22} got {g!r}')
