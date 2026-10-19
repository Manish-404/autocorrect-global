"""Build tests.txt (what to type) and expected.txt (what must come out) from the generated entries."""
import json, random, pathlib, re
random.seed(2026)
root = pathlib.Path(__file__).parent
d = json.loads((root / 'final.json').read_text(encoding='utf-8'))
valid = [w for w in (root / 'valid.txt').read_text().split() if 4 <= len(w) <= 10]

typed, expected = [], []


def add(t, e):
    typed.append(t)
    expected.append(e)


# 1. every kind that is switched on
for kind, n in (('cur-on', 60), ('typo-transposed', 70), ('typo-omitted', 45)):
    for c, a, _ in random.sample(d[kind], n):
        add(a, c)

# 2. capitalisation is kept
for c, a, _ in random.sample(d['cur-on'], 8):
    add(a.capitalize(), c.capitalize())
for c, a, _ in random.sample(d['typo-transposed'], 6):
    add(a.upper(), c.upper())

# 3. punctuation after the word also triggers it
for c, a, _ in random.sample(d['cur-on'], 6):
    add(a + ',', c + ',')
for c, a, _ in random.sample(d['typo-transposed'], 4):
    add(a + '?', c + '?')
for c, a, _ in random.sample(d['typo-transposed'], 3):
    add(a + '.', c + '.')

# 4. correct words must stay exactly as typed (Hinglish, English, names, the optional block)
keep = random.sample(valid, 70)
keep += ['kyu', 'pani', 'jana', 'kam', 'kaam', 'main', 'mein', 'bhai', 'acha', 'accha', 'apka', 'nahin', 'kuchh',
         'hello', 'the', 'and', 'form', 'pure', 'ache', 'string', 'rahul', 'delhi', 'python', 'function', 'because']
for w in keep:
    add(w, w)
# optional entries are switched off, so these stay as typed
for c, a, _ in random.sample(d['cur-alt'], 12):
    add(a, a)
for c, a, _ in random.sample(d['rule-style'], 6):
    add(a, a)

order = list(range(len(typed)))
random.shuffle(order)
(root / 'tests.txt').write_text('\n'.join(typed[i] for i in order) + '\n', encoding='ascii', newline='\n')
(root / 'expected.txt').write_text('\n'.join(expected[i] for i in order) + '\n', encoding='ascii', newline='\n')
print(len(typed), 'tests')
