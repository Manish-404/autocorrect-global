#!/usr/bin/env python3
"""Build AutoCorrectHinglish.ahk from the lexicon files in ./lex.

Lexicon line formats (see lex/*.txt):
  @ Section title            start of a section (used for grouping in the output)
  %enabled / %alt            default for the variants that follow: corrected by default / optional
  =w1 w2 ...                 valid words: never corrected, never produced by a correction
  word | v1 +v2 ~v3 !v4      word + explicit variants. + = switched on, ~ = optional (alternate
                             spelling), ! = keep even if the English dictionary knows the word.
                             Typos are generated for it too (transposed / omitted / doubled letters).
  -word | v1 v2              no typos or rule variants are generated for it
  w1 w2 w3                   several words without variants
  flags after ';': norules notypos
Verb files (lex/verbs*.txt): one stem per token (stem/elided); a leading * on a line marks the
stems whose forms get typo coverage.
"""
import re, sys, subprocess, collections, pathlib, time, json

ROOT = pathlib.Path(__file__).resolve().parent
LEXDIR = ROOT / 'lex'
PROJECT = ROOT.parent.parent                    # the repository root
ENG_AHK = PROJECT / 'AutoCorrect.ahk'
SPELL_PS1 = ROOT.parent / 'spell.ps1'
TMPDIR = PROJECT / '.tmp'                       # temp files for the spell check stay inside the project folder
REPORT = ROOT / 'report.txt'
ALPHA = 'abcdefghijklmnopqrstuvwxyz'

# abbreviations we never want in the file (offensive words that come out of leaving letters out)
BLOCK_PREFIX = ('chod', 'chud', 'lund', 'gand', 'bhosd', 'madarc', 'randi', 'lauda', 'lavd')
BLOCK_EXACT = {'chut', 'gaand', 'gand'}

PRIO = {'cur-on': 0, 'cur-alt': 1, 'rule-style': 2, 'rule-elong': 3,
        'typo-transposed': 4, 'typo-omitted': 4, 'typo-doubled': 5}
ENABLED_KINDS = {'cur-on', 'typo-transposed', 'typo-omitted'}

log = []


def say(msg=''):
    print(msg)
    log.append(msg)


# --------------------------------------------------------------------------- lexicon
class Entry:
    def __init__(self, word, section, mode):
        self.word = word
        self.section = section
        self.mode = mode          # full | curated
        self.variants = {}        # variant -> (enabled, forced)
        self.norules = False
        self.notypos = False
        self.typo_forms_only = False


entries = {}
valid_only = set()
verb_forms_valid = set()
section_order = []


def parse_variant(tok, default_enabled):
    enabled, forced = default_enabled, False
    while tok and tok[0] in '+~!':
        ch, tok = tok[0], tok[1:]
        if ch == '+':
            enabled = True
        elif ch == '~':
            enabled = False
        else:
            forced = True
    return tok.lower(), enabled, forced


def add_entry(word, section, mode, variants, flags, default_enabled, where):
    e = entries.get(word)
    if e is None:
        e = Entry(word, section, mode)
        entries[word] = e
    for tok in variants:
        v, enabled, forced = parse_variant(tok, default_enabled)
        if not re.fullmatch(r'[a-z]+', v):
            say(f'BAD VARIANT {v!r} for {word} ({where})')
            continue
        old = e.variants.get(v)
        vsec = section
        if old:
            if not enabled:
                vsec = old[2]          # keep the section of the earlier (possibly enabled) definition
            enabled, forced = enabled or old[0], forced or old[1]
        e.variants[v] = (enabled, forced, vsec)
    if 'norules' in flags:
        e.norules = True
    if 'notypos' in flags:
        e.notypos = True
    if mode == 'curated':
        e.mode = 'curated'


INFLECT = {
    # adjectives and nouns ending in -a:  bada -> badi, bade
    'adj': lambda w: [w, w[:-1] + 'i', w[:-1] + 'e'] if w.endswith('a') else [w],
    # masculine nouns ending in -a:  ladka -> ladke, ladkon
    'ma': lambda w: [w, w[:-1] + 'e', w[:-1] + 'on'] if w.endswith('a') else [w],
    # feminine nouns ending in -i:  ladki -> ladkiyan, ladkiyon
    'fi': lambda w: [w, w + 'yan', w + 'yon'],
    # feminine nouns ending in -iya:  chidiya -> chidiyan, chidiyon
    'fiya': lambda w: [w, w + 'n', w[:-1] + 'on'],
    # feminine nouns ending in a consonant:  baat -> baatein, baaton
    'fc': lambda w: [w, w + 'ein', w + 'on'],
    # feminine nouns ending in -a:  hawa -> hawayein, hawaon
    'fa': lambda w: [w, w + 'yein', w + 'on'],
    # masculine nouns ending in a consonant:  ghar -> gharon
    'mc': lambda w: [w, w + 'on'],
    # words that only need to be known
    'word': lambda w: [w],
}


def read_inflect():
    n = 0
    for p in sorted(LEXDIR.glob('inflect*.txt')):
        for ln, raw in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
            line = re.sub(r'(^|\s)#.*$', '', raw).strip()
            if not line:
                continue
            kind, _, rest = line.partition(':')
            kind = kind.strip()
            if kind not in INFLECT:
                say(f'BAD INFLECT KIND {kind!r} ({p.name}:{ln})')
                continue
            for w in rest.split():
                w = w.lower()
                if '?' in w:            # a word I was not sure about: left out on purpose
                    continue
                if not re.fullmatch(r'[a-z]+', w):
                    say(f'BAD WORD {w!r} ({p.name}:{ln})')
                    continue
                for f in INFLECT[kind](w):
                    if f not in entries:
                        entries[f] = Entry(f, 'Inflected forms', 'full')
                        entries[f].norules = (f != w)
                        n += 1
    say(f'inflected / listed words: {n}')


def read_lex():
    for p in sorted(LEXDIR.glob('*.txt')):
        if p.name.startswith(('verbs', 'inflect')):
            continue
        section = 'Miscellaneous'
        default_enabled = False
        for ln, raw in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
            line = re.sub(r'(^|\s)#.*$', '', raw).strip()
            if not line:
                continue
            where = f'{p.name}:{ln}'
            if line.startswith('@'):
                section = line[1:].strip()
                if section not in section_order:
                    section_order.append(section)
                continue
            if line.startswith('%'):
                default_enabled = line[1:].strip() == 'enabled'
                continue
            if line.startswith('='):
                for w in line.split():
                    w = w.lstrip('=')
                    if not re.fullmatch(r'[a-z]+', w):
                        say(f'BAD VALID WORD {w!r} ({where})')
                    valid_only.add(w)
                continue
            mode = 'full'
            if line.startswith('-'):
                mode, line = 'curated', line[1:]
            flags = set()
            if ';' in line:
                line, fl = line.split(';', 1)
                flags = set(fl.split())
            if '|' in line:
                w, vs = line.split('|', 1)
                words, vs = [w.strip().lower()], vs.split()
            else:
                words, vs = line.lower().split(), []
            for w in words:
                if not re.fullmatch(r'[a-z]+', w):
                    say(f'BAD WORD {w!r} ({where})')
                    continue
                add_entry(w, section, mode, vs, flags, default_enabled, where)


# --------------------------------------------------------------------------- verbs
def conj(stem, elided):
    """Return {form: eligible_for_typos} for a regular stem."""
    s, e = stem, elided
    forms = {}

    def put(f, elig=False):
        forms[f] = forms.get(f, False) or elig

    if s[-1] == 'a':                           # class A: bata, kha, aa, la, paa ...
        put(s + 'na', True); put(s + 'ne'); put(s + 'ni')
        put(s + 'ta', True); put(s + 'ti', True); put(s + 'te', True)
        put(s + 'o', True); put(s + 'iye'); put(s + 'ie')
        put(s + 'ye'); put(s + 'yen'); put(s + 'un')
        put(s + 'unga', True); put(s + 'ungi', True)
        put(s + 'yega', True); put(s + 'yegi', True); put(s + 'yenge', True); put(s + 'yengi')
        put(s + 'oge', True); put(s + 'ogi', True)
        put(s + 'ya', True); put(s + 'yi', True)
        put(s + 'ke'); put(s + 'kar')
    elif s[-1] == 'o':                         # class O: so, ro, dho, kho
        put(s + 'na', True); put(s + 'ne'); put(s + 'ni')
        put(s + 'ta', True); put(s + 'ti', True); put(s + 'te', True)
        put(s + 'iye'); put(s + 'ye'); put(s + 'yen'); put(s + 'un')
        put(s + 'unga'); put(s + 'ungi'); put(s + 'yega', True); put(s + 'yegi', True); put(s + 'yenge', True)
        put(s + 'ge'); put(s + 'gi')
        put(s + 'ya', True); put(s + 'yi', True)
        put(s + 'ke'); put(s + 'kar')
    else:                                      # class C: consonant-final
        put(s + 'na', True); put(s + 'ne'); put(s + 'ni')
        put(s + 'ta', True); put(s + 'ti', True); put(s + 'te', True)
        put(s); put(s + 'o', True); put(s + 'iye'); put(s + 'ie')
        for stem2 in {e, s}:
            el = stem2 == e
            put(stem2 + 'e', el)
            put(stem2 + 'en'); put(stem2 + 'un')
            put(stem2 + 'unga', el); put(stem2 + 'ungi', el)
            put(stem2 + 'ega', el); put(stem2 + 'egi', el)
            put(stem2 + 'enge', el); put(stem2 + 'engi')
            put(stem2 + 'a', el); put(stem2 + 'i', el)
        put(s + 'oge', True); put(s + 'ogi', True)
        put(s + 'ke'); put(s + 'kar')
    return forms


def read_verbs():
    n_core = 0
    for p in sorted(LEXDIR.glob('verbs*.txt')):
        for raw in p.read_text(encoding='utf-8').splitlines():
            line = re.sub(r'(^|\s)#.*$', '', raw).strip()
            if not line or line.startswith('@'):
                continue
            core = line.startswith('*')
            for tok in line.lstrip('*').split():
                stem, el = tok.split('/') if '/' in tok else (tok, tok)
                for f, elig in conj(stem, el).items():
                    if not re.fullmatch(r'[a-z]+', f):
                        continue
                    if core and elig and f not in entries:
                        e = Entry(f, 'Verb forms', 'full')
                        e.norules = True      # style variants of conjugated forms are not generated
                        entries[f] = e
                        n_core += 1
                    elif f not in entries:
                        verb_forms_valid.add(f)
    say(f'verb forms: {n_core} typo-eligible, {len(verb_forms_valid)} valid-only')


# --------------------------------------------------------------------------- English hotstrings
class EnglishIndex:
    def __init__(self, path):
        self.exact, self.prefix, self.suffix, self.inner = set(), set(), set(), set()
        self.count = 0
        in_block = False
        for raw in path.read_text(encoding='utf-8-sig').splitlines():
            s = raw.strip()
            if s.startswith('/*'):
                in_block = True
            if in_block:
                if '*/' in s:
                    in_block = False
                continue
            m = re.match(r'^:(?P<o>[^:]*):(?P<a>.+?)::', raw)
            if not m:
                continue
            opts, abbr = m.group('o'), m.group('a')
            if ' ' in abbr:
                continue
            if re.search(r'C(?![01])', opts) and abbr != abbr.lower():
                continue  # case-sensitive with capitals: never matches lower-case typing
            abbr = abbr.lower()
            star, q = '*' in opts, '?' in opts
            if star and q:
                self.inner.add(abbr)
            elif star:
                self.prefix.add(abbr)
            elif q:
                self.suffix.add(abbr)
            else:
                self.exact.add(abbr)
            self.count += 1

    def conflict(self, w):
        if w in self.exact:
            return 'exact:' + w
        n = len(w)
        for i in range(1, n + 1):
            if w[:i] in self.prefix:
                return 'prefix:' + w[:i]
        for i in range(n):
            if w[i:] in self.suffix:
                return 'suffix:' + w[i:]
        for i in range(n):
            for j in range(i + 1, n + 1):
                if w[i:j] in self.inner:
                    return 'inner:' + w[i:j]
        return None


# --------------------------------------------------------------------------- generators
STYLE_RULES = [
    ('aa-a', lambda w: w.replace('aa', 'a') if 'aa' in w else None),
    ('ee-i', lambda w: w.replace('ee', 'i') if 'ee' in w else None),
    ('oo-u', lambda w: w.replace('oo', 'u') if 'oo' in w else None),
    ('w-v', lambda w: w.replace('w', 'v') if 'w' in w else None),
    ('z-j', lambda w: w.replace('z', 'j') if 'z' in w else None),
    ('ph-f', lambda w: w.replace('ph', 'f') if 'ph' in w else None),
    ('ai-e', lambda w: (lambda v: v if v != w else None)(re.sub(r'ai(?=[b-df-hj-np-tv-z][aeiou])', 'e', w))),
]
ELONG_RULES = [
    ('final-a', lambda w: w + 'a' if w.endswith('a') and not w.endswith('aa') and len(w) >= 3 else None),
    ('final-i', lambda w: w[:-1] + 'ee' if w.endswith('i') and not w.endswith('ii') and len(w) >= 3 else None),
    ('final-e', lambda w: w + 'y' if w.endswith('e') and not w.endswith('ee') and len(w) >= 3 else None),
]


def combos(c, table):
    out = {}
    n = len(table)
    for mask in range(1, 1 << n):
        w, names, ok = c, [], True
        for k in range(n):
            if mask >> k & 1:
                r = table[k][1](w)
                if r is None:
                    ok = False
                    break
                w = r
                names.append(table[k][0])
        if ok and w != c:
            out.setdefault(w, '+'.join(names))
    return out


def style_variants(c):
    out = combos(c, STYLE_RULES)
    for m in re.finditer('aa', c):             # single occurrences of aa -> a
        out.setdefault(c[:m.start()] + 'a' + c[m.end():], 'aa-a')
    return out


def elong_variants(c):
    return combos(c, ELONG_RULES)


# 4-letter words get swapped-letter typos only when they are this common. Short words sit next to many
# other real words (abbu/babu), so the other 4-letter words are left alone. (Held-out test, 2026-10-19.)
COMMON4 = set('''nahi kuch kaun kisi abhi phir tera mera uska unka inka apne hota hoga hogi hota raha rahi rahe
kaha kahi wahi yahi sath bhai jaha waha yaha unko usko isko tumhe humko apka uski unki kabhi sabhi
thik acha accha dost pyar kaam karo karu kare kiya kiye gaya gaye gayi aaya aaye aayi liya liye diya diye
mili mila mile bola bole boli dekh sunn suna sune suni baat raat roti paas dard mujh tujh hame tumko
'''.split())


def typos_for(c):
    out = {}
    n = len(c)
    for i in range(n - 1):
        if n == 4 and c not in COMMON4:
            break
        if c[i] != c[i + 1]:
            out.setdefault(c[:i] + c[i + 1] + c[i] + c[i + 2:], 'transposed')
    if n >= 6:
        for i in range(1, n - 1):                 # interior letters only: first/last drops are often other words
            out.setdefault(c[:i] + c[i + 1:], 'omitted')
    return out


def edits1(w):
    n = len(w)
    res = set()
    for i in range(n):
        res.add(w[:i] + w[i + 1:])
        for ch in ALPHA:
            res.add(w[:i] + ch + w[i + 1:])
    for i in range(n + 1):
        for ch in ALPHA:
            res.add(w[:i] + ch + w[i:])
    for i in range(n - 1):
        res.add(w[:i] + w[i + 1] + w[i] + w[i + 2:])
    return res


# --------------------------------------------------------------------------- spell check
def english_valid(words):
    words = sorted(words)
    inp, outp = ROOT / 'spell_in.txt', ROOT / 'spell_out.txt'
    inp.write_text('\n'.join(words) + '\n', encoding='ascii')
    if outp.exists():
        outp.unlink()
    import os
    TMPDIR.mkdir(exist_ok=True)
    env = dict(os.environ, TEMP=str(TMPDIR), TMP=str(TMPDIR))   # the C# compile in spell.ps1 writes to TEMP
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(SPELL_PS1),
                        '-InFile', str(inp), '-OutFile', str(outp)], capture_output=True, text=True, env=env)
    if not outp.exists():
        raise SystemExit('spell check failed: ' + r.stdout + r.stderr)
    return set(outp.read_text(encoding='utf-8-sig').split())


# --------------------------------------------------------------------------- main
def main():
    t0 = time.time()
    read_lex()
    read_inflect()
    read_verbs()
    # words declared valid-only (=word) get no typo coverage even if a word list also lists them
    for w in list(valid_only):
        e = entries.get(w)
        if e is not None and not e.variants:
            del entries[w]
    eng = EnglishIndex(ENG_AHK)
    say(f'English hotstrings indexed: {eng.count}')

    valid = set(valid_only) | set(entries) | verb_forms_valid
    say(f'entries: {len(entries)}  valid-only: {len(valid_only)}  verb forms (valid-only): {len(verb_forms_valid)}')

    # candidates: abbr -> list of (prio, canonical, kind, section, forced)
    cands = collections.defaultdict(list)

    def cand(abbr, c, kind, section, forced=False, minlen=4):
        if len(abbr) >= minlen and abbr != c:
            cands[abbr].append((PRIO[kind], c, kind, section, forced))

    alt_map = collections.defaultdict(set)      # alternate spelling -> canonical words
    for c, e in entries.items():
        for v, (enabled, forced, vsec) in e.variants.items():
            cand(v, c, 'cur-on' if enabled else 'cur-alt', vsec, forced, minlen=2)
            if not enabled:
                alt_map[v].add(c)
        if e.mode != 'full':
            continue
        if not e.norules:
            for v, rule in style_variants(c).items():
                cand(v, c, 'rule-style', rule)
                alt_map[v].add(c)
            for v, rule in elong_variants(c).items():
                cand(v, c, 'rule-elong', rule)
                alt_map[v].add(c)
        if not e.notypos:
            for t, kind in typos_for(c).items():
                cand(t, c, 'typo-' + kind, 'typo')
    alt_spellings = set(alt_map)
    say(f'raw candidate abbreviations: {len(cands)}')

    eng_valid = english_valid(cands.keys())
    say(f'abbreviations that are English words: {len(eng_valid)}')

    drops = collections.Counter()
    dropped_cur, dropped_gen = [], []
    final = {}
    for abbr, lst in cands.items():
        forced = any(x[4] for x in lst)
        reason = None
        if abbr in valid:
            reason = 'valid-word'
        elif abbr in eng_valid and not forced:
            reason = 'english-word'
        elif abbr in BLOCK_EXACT or abbr.startswith(BLOCK_PREFIX):
            reason = 'blocklist'
        else:
            hit = eng.conflict(abbr)
            if hit:
                reason = 'english-script ' + hit
        best = min(x[0] for x in lst)
        top = [x for x in lst if x[0] == best]
        targets = {x[1] for x in top}
        if reason is None and len(targets) > 1:
            reason = 'ambiguous ' + '/'.join(sorted(targets))
        if reason is None and best >= PRIO['rule-style'] and abbr in alt_spellings and \
                not any(x[2] in ('rule-style', 'rule-elong') or x[2] == 'cur-alt' for x in top):
            reason = 'is an alternate spelling of another word'
        if reason:
            drops[reason.split(' ')[0]] += 1
            (dropped_cur if best <= 1 else dropped_gen).append((abbr, sorted(targets), reason))
            continue
        pick = top[0]
        final[abbr] = (pick[1], pick[2], pick[3])

    # a typo must not be one edit away from a different valid word
    valid4 = {w for w in valid if len(w) >= 4}
    alt4 = {w: cs for w, cs in alt_map.items() if len(w) >= 4}
    removed_nb, nb_examples = 0, []
    for abbr in list(final):
        c, kind, sec = final[abbr]
        if not kind.startswith('typo'):
            continue
        for x in edits1(abbr):
            if x == c or x == abbr:
                continue
            if x in valid4 or (x in alt4 and alt4[x] != {c}):
                del final[abbr]
                removed_nb += 1
                if len(nb_examples) < 12:
                    nb_examples.append((abbr, c, x))
                break
    say(f'typos dropped because a different valid word is one edit away: {removed_nb}')
    say('dropped reasons: ' + ', '.join(f'{k}={v}' for k, v in drops.most_common()))
    say(f'curated variants dropped ({len(dropped_cur)}):')
    for abbr, tg, reason in sorted(dropped_cur):
        say(f'   {abbr} -> {",".join(tg)}   [{reason}]')
    say('neighbour examples: ' + '; '.join(f'{a}->{c} (near {x})' for a, c, x in nb_examples))
    say(f'generated variants dropped for conflicts ({len(dropped_gen)}): ' +
        '; '.join(f'{a}->{",".join(t)} [{r}]' for a, t, r in sorted(dropped_gen)[:400]))

    kinds = collections.Counter(v[1] for v in final.values())
    on = sum(n for k, n in kinds.items() if k in ENABLED_KINDS)
    say(f'final: {len(final)} (on by default: {on}, optional: {len(final) - on})  by kind: {dict(kinds)}')

    # save for the emitter
    by_kind = collections.defaultdict(list)
    for abbr, (c, kind, sec) in final.items():
        by_kind[kind].append([c, abbr, sec])
    (ROOT / 'final.json').write_text(json.dumps(by_kind), encoding='utf-8')
    (ROOT / 'valid.txt').write_text('\n'.join(sorted(valid)) + '\n', encoding='ascii')
    stats = {'sections': section_order, 'valid_words': len(valid), 'entries': len(entries),
             'verb_forms': len(verb_forms_valid) + sum(1 for e in entries.values() if e.section == 'Verb forms')}
    (ROOT / 'stats.json').write_text(json.dumps(stats), encoding='utf-8')
    REPORT.write_text('\n'.join(log), encoding='utf-8')
    say(f'done in {time.time() - t0:.1f}s')


if __name__ == '__main__':
    main()
