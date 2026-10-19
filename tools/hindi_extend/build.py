"""Builds the generated block of AutoCorrectHindi.ahk.

Every entry is  wrong -> right  where
  * right is a real word: common in Hindi Wikipedia (or in the Hunspell dictionary and attested there),
  * wrong is NOT a word: it occurs nowhere in Hindi Wikipedia (text and titles), Hindi Wiktionary titles,
    the Hunspell dictionary or the subtitle word list,
  * wrong differs from right by one mechanical slip (nukta dropped, long/short vowel swapped, ...),
  * wrong is not the tail of a real word typed after a matra (the AutoHotkey word-boundary hazard),
  * wrong is not already a hotstring, and does not clash with another entry.

Word sources live in .tmp\\hindict (safe to delete; fetched from Wikimedia dumps, Chromium's hunspell_dictionaries,
hermitdave/FrequencyWords). Run:  python build.py [--cap=3000] [--write]
"""
import json, re, sys, unicodedata, collections

ROOT = "D:/Software/Auto correct typo global/"
S = ROOT + ".tmp/hindict/"
AHK = ROOT + "AutoCorrectHindi.ahk"
CAP = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--cap=")), "3000"))
RDIC = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--rdic=")), "5"))
RSUB = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--rsub=")), "3"))
RWIKI = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--rwiki=")), "100"))
RLOOSE = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--rloose=")), "50"))
BEGIN, END = "; ==== generated:begin", "; ==== generated:end"
nfc = lambda s: unicodedata.normalize("NFC", s)
NUK, VIR = "\u093c", "\u094d"
DEV = re.compile(r"[\u0900-\u097F]+")


def clean(w):
    """A plain Devanagari word: letters and vowel signs only (no digits, danda, joiners)."""
    return bool(w) and all(unicodedata.category(c)[0] in "LM" for c in w) and not any(c in "\u0964\u0965\u0970\u0971" for c in w)


wc = collections.Counter(json.load(open(S + "hiwiki_counts.json", encoding="utf-8")))
dic = set()
for i, l in enumerate(open(S + "hi_IN.dic", encoding="utf-8", errors="replace")):
    if i:
        dic.add(nfc(l.strip().split("/")[0]))
sub = {}
for l in open(S + "hi_full.txt", encoding="utf-8"):
    p = l.split()
    if len(p) == 2 and p[1].isdigit():
        sub[nfc(p[0])] = int(p[1])
titles = set()
wikt = set()
for f in ("hiwikt", "hiwiki"):
    for l in open(S + f, encoding="utf-8"):
        for t in DEV.findall(nfc(l)):
            titles.add(t)
            if f == "hiwikt" and nfc(l.strip()) == t:
                wikt.add(t)

ne = set()
for i, l in enumerate(open(S + "ne.dic", encoding="utf-8", errors="replace")):
    if i:
        ne.add(nfc(l.strip().split("/")[0]))

# a wrong form must be absent from all of these
seen_anywhere = set(wc) | dic | set(sub) | titles | ne
# looser bar for "real word": used only to protect real words from the word-boundary hazard
real = {w for w, n in wc.items() if n >= 2} | dic | ne | {w for w in sub if sub[w] >= 2} | titles


def score(w):
    return wc[w] + 5 * sub.get(w, 0) + (50 if w in dic else 0)


# ---------- existing entries
raw = open(AHK, "rb").read().decode("utf-8-sig")
body = raw.split("/*")[0]
if BEGIN in body:
    body = body[: body.index(BEGIN)]
existing = {}
for line in body.splitlines():
    if line.startswith(";"):
        continue
    m = re.match(r"^::([^:\n]+)::(\S+)", line) or re.match(r"^:[^:\n]+:([^:\n]+)::(\S+)", line)
    if m:
        existing[nfc(m.group(1))] = nfc(m.group(2))


# ---------- families: each yields wrong forms of a right word
def at(w, chars):
    return [i for i, c in enumerate(w) if c in chars]


def put(w, i, to):
    return w[:i] + to + w[i + 1:]


def f_nukta(r):
    w = r
    for b in "डढ":
        w = w.replace(b + NUK, b)
    if w != r:
        yield w


def f_bya(r):
    if "व्य" in r:
        yield r.replace("व्य", "ब्य")


def f_gya(r):
    if "ज्ञ" in r:
        yield r.replace("ज्ञ", "ग्य")


def f_vowel(r):
    pair = {"ि": "ी", "ी": "ि", "ु": "ू", "ू": "ु"}
    for i in at(r, pair):
        yield put(r, i, pair[r[i]])
    if r[0] in "इईउऊ":
        yield put(r, 0, {"इ": "ई", "ई": "इ", "उ": "ऊ", "ऊ": "उ"}[r[0]])


def f_ri(r):
    # कृ typed as क + ् + र
    for i in at(r, "ृ"):
        yield r[: i - 1] + r[i - 1] + VIR + "र" + r[i + 1:]


def f_aiau(r):
    pair = {"ै": "े", "े": "ै", "ौ": "ो", "ो": "ौ"}
    for i in at(r, pair):
        yield put(r, i, pair[r[i]])
    if r[0] in "एऐओऔ":
        yield put(r, 0, {"ए": "ऐ", "ऐ": "ए", "ओ": "औ", "औ": "ओ"}[r[0]])


def f_nasal(r):
    for i in at(r, "ंँ"):
        yield r[:i] + r[i + 1:]


def f_sibilant(r):
    pair = {"श": "ष", "ष": "श", "ण": "न"}
    for i in at(r, pair):
        if i + 1 < len(r) and r[i + 1] == VIR:      # leave conjuncts alone
            continue
        yield put(r, i, pair[r[i]])


FAMILIES = [  # (label, generator, minimum Wikipedia count of the right word)
    ("nukta", f_nukta, 10),
    ("bya", f_bya, 10),
    ("gya", f_gya, 10),
    ("vowel", f_vowel, 50),
    ("ri", f_ri, 30),
    ("aiau", f_aiau, 150),
    ("nasal", f_nasal, 150),
    ("sibilant", f_sibilant, 300),
]

# Right-hand words removed after reading every one of them: non-standard or contested spellings, the -ये/-यी forms the
# project keeps in its commented "ambiguous" block, names with several spellings, and fragments.
RIGHT_BLACKLIST = set("""
आवृति पुनरावृति निवृति प्रवृत प्रतिकृत नेतृत्त्व वैज्ञानिको व्यस्क शुरूआती वृहत् वृहद् वृहस्पति वृक्ष्य
श्रृंखला श्रृंखलाएं श्रृंखलाओं श्रृंखलाबद्ध श्रृंगार श्रृंगी श्रृंगेरी
चाहिये किये दिये नये इसलिये जायेगा पायी जाये पाये बनाये जरिये जोकि जिनमे जिसमे क्रमश युक्रेन
इसपर उसपर उनपर जिसपर करनेवाले बंगलौर मध्यप्रदेश कर्त्तव्य तत्वज्ञान आव्यूह
काव्या नव्या भव्या बृंदा मृत् हृद् कटड़ा चप्पड़ विज्ञानं
""".split())
PRECISE = {"nukta", "bya", "gya", "ri"}   # these slips can only produce non-words, so a frequent right word is enough
cands = {}  # wrong -> (right, family, score)
for r in wc:
    if not clean(r) or len(r) < 3 or r in RIGHT_BLACKLIST:
        continue
    strict = (r in dic and wc[r] >= RDIC) or (sub.get(r, 0) >= RSUB and wc[r] >= RWIKI)
    loose = wc[r] >= RLOOSE and r in wikt        # frequent in Wikipedia AND a Hindi Wiktionary headword
    if not (strict or loose):
        continue
    for fam, gen, minwc in FAMILIES:
        if not (strict or (loose and fam in PRECISE)):
            continue
        for w in gen(r):
            w = nfc(w)
            if w == r or not clean(w) or w in seen_anywhere or w in existing:
                continue
            sc = score(r)
            if w not in cands or sc > cands[w][2]:
                cands[w] = (r, fam, sc)


# ---------- word-boundary hazard (Windows does not count matras/virama/nukta as letters)
def mark(c):
    return unicodedata.category(c) in ("Mn", "Mc")


tails = set()
for w in real:
    for i in range(1, len(w)):
        if mark(w[i - 1]):
            tails.add(w[i:])
hazard = {w for w in cands if w in tails}

# clash: one entry's left side is the tail of another's (after a mark), new vs new or new vs existing
lefts = set(cands) | set(existing)
tail_of = collections.defaultdict(set)
for w in lefts:
    for i in range(1, len(w)):
        if mark(w[i - 1]):
            tail_of[w[i:]].add(w)
clash = set()
for w in cands:
    if tail_of.get(w):          # w is the tail of another left side
        clash.add(w)
    for i in range(1, len(w)):  # another left side is a tail of w
        if mark(w[i - 1]) and w[i:] in lefts:
            clash.add(w)
ok = {w: v for w, v in cands.items()
      if w not in hazard and w not in clash and v[0] not in cands and v[0] not in existing}

# ---------- rank, cap, print
order = {f[0]: i for i, f in enumerate(FAMILIES)}
items = sorted(ok.items(), key=lambda kv: -kv[1][2])   # most common correct words first
stats = collections.Counter(v[1] for _, v in items)
print("candidates", len(cands), "hazard", len(hazard), "clash", len(clash), "kept", len(ok), dict(stats))
precise = [kv for kv in items if kv[1][1] in PRECISE]
rest = [kv for kv in items if kv[1][1] not in PRECISE]
items = precise + rest[: max(0, CAP - len(precise))]

TITLES = {
    "nukta": "More ड़ / ढ़ written without the nukta (Marathi writes these without it - delete this block if you type Marathi)",
    "bya": "More ब्य written for व्य",
    "gya": "ग्य written for ज्ञ",
    "vowel": "Short / long vowel mixed up: ि ी ु ू (more words)",
    "ri": "ृ written as the conjunct with र (more words)",
    "aiau": "े / ै and ो / ौ mixed up (more words)",
    "nasal": "Missing anusvara or chandrabindu (more words)",
    "sibilant": "श / ष and ण / न mixed up (more words)",
}
byfam = collections.defaultdict(list)
for w, (r, fam, sc) in items:
    byfam[fam].append((w, r))
out = [BEGIN + "  (tools\\hindi_extend\\build.py rewrites everything between begin and end)"]
for fam, _, _ in FAMILIES:
    if byfam[fam]:
        out.append("\n; " + TITLES[fam])
        out += [f"::{w}::{r}" for w, r in byfam[fam]]
out.append(END)
text = "\n".join(out) + "\n"
open(S + "generated.txt", "w", encoding="utf-8").write(text)
json.dump([[w, r, fam, sc, r in dic] for w, (r, fam, sc) in items], open(S + "generated_meta.json", "w", encoding="utf-8"), ensure_ascii=False)
print("emitted", len(items), {f: len(v) for f, v in byfam.items()})

if "--write" in sys.argv:
    full = raw
    if BEGIN in full:
        a = full.index(BEGIN)
        b = full.index(END) + len(END) + 1
        full = full[:a] + text + full[b:]
    else:
        marker = ";------------------------------------------------------------------------------\n; Ambiguous / prescriptive"
        i = full.index(marker)
        full = full[:i].rstrip("\n") + "\n\n\n" + text + "\n\n" + full[i:]
    open(AHK, "wb").write(b"\xef\xbb\xbf" + full.encode("utf-8"))
    print("written")
