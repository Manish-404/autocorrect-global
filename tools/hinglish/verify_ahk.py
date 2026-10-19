"""Static checks on AutoCorrectHinglish.ahk: BOM, CRLF, duplicates, clashes with AutoCorrect.ahk and AutoCorrectHindi.ahk,
active vs commented-out counts.  usage: verify_ahk.py"""
import pathlib, re, collections

proj = pathlib.Path(__file__).resolve().parent.parent.parent
f = proj / 'AutoCorrectHinglish.ahk'
raw = f.read_bytes()
print('BOM:', raw[:3] == b'\xef\xbb\xbf', '  size:', len(raw), '  CRLF only:', raw.count(b'\r\n') == raw.count(b'\n'))
text = raw.decode('utf-8-sig')

HS = re.compile(r'^:([^:]*):([^:\s][^:]*)::(.*)$')


def hotstrings(txt, skip_block_comments=True):
    on, off = [], []
    in_block = False
    for line in txt.splitlines():
        s = line.strip()
        if s.startswith('/*'):
            in_block = True
            continue
        if s.startswith('*/'):
            in_block = False
            continue
        m = HS.match(line) or re.match(r'^()(.+?)::(.*)$', line)
        if not m or line.lstrip().startswith(';') or line.startswith('#') or '::' not in line:
            continue
        opts, abbr, rep = m.group(1), m.group(2), m.group(3)
        if abbr.startswith(':'):
            continue
        (off if in_block else on).append((opts.lower(), abbr.lower(), rep))
    return on, off


on, off = hotstrings(text)
print('active hotstrings:', len(on), '  commented-out (block):', len(off))
dups = [k for k, v in collections.Counter(a for _, a, _ in on + off).items() if v > 1]
print('duplicate abbreviations (active+block):', len(dups), dups[:10])
act = {a for _, a, _ in on}
for name in ('AutoCorrect.ahk', 'AutoCorrectHindi.ahk'):
    t = (proj / name).read_bytes().decode('utf-8-sig')
    o, _ = hotstrings(t)
    clash = sorted(act & {a for _, a, _ in o})
    print(f'clashes with {name}: {len(clash)}', clash[:15])
# a hotstring whose abbreviation equals its replacement does nothing
noop = [a for _, a, r in on if a == r.lower()]
print('no-op entries:', len(noop), noop[:5])
# non-ASCII in the Hinglish file?
bad = [i for i, ch in enumerate(text) if ord(ch) > 127]
print('non-ASCII characters:', len(bad))
