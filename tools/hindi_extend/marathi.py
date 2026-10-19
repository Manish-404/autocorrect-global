"""Finds hotstrings whose left side is a Marathi word and (with --apply) removes them from AutoCorrectHindi.ahk.

A left side counts as Marathi when it shows up in Marathi Wikipedia (text, titles), Marathi Wiktionary titles or the Marathi
Hunspell dictionary AND it is clearly more common there than in Hindi Wikipedia (per token). Words that are at least as
common in Hindi as in Marathi are Hindi typos that merely also occur in Marathi text, so they stay (e.g. नही).

Run:  python marathi.py [--min=3] [--ratio=2] [--apply]      Sources: .tmp\\mr (see count_wiki.py for the word counts)
"""
import json, re, sys, unicodedata

ROOT = "D:/Software/Auto correct typo global/"
M = ROOT + ".tmp/mr/"
AHK = ROOT + "AutoCorrectHindi.ahk"
RATIO = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--ratio=")), "2"))
MIN = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--min=")), "3"))
nfc = lambda s: unicodedata.normalize("NFC", s)
DEV = re.compile(r"[\u0900-\u097F]+")

mc = json.load(open(M + "mrwiki_counts.json", encoding="utf-8"))
hc = json.load(open(ROOT + ".tmp/hindict/hiwiki_counts.json", encoding="utf-8"))
MR_TOK, HI_TOK = sum(mc.values()), sum(hc.values())
dic = set()
for i, l in enumerate(open(M + "mr_IN.dic", encoding="utf-8", errors="replace")):
    if i:
        dic.add(nfc(l.strip().split("/")[0]))
titles = set()
for f in ("mrwiki-latest-all-titles-in-ns0", "mrwiktionary-latest-all-titles-in-ns0"):
    for l in open(M + f, encoding="utf-8"):
        for t in DEV.findall(nfc(l)):
            titles.add(t)


def ratio(w):
    """How many times more common w is in Marathi Wikipedia than in Hindi Wikipedia, per token."""
    return (mc.get(w, 0) / MR_TOK) / ((hc.get(w, 0) + 1) / HI_TOK)


raw = open(AHK, "rb").read().decode("utf-8-sig")
out, flagged, kept = [], [], []
for line in raw.split("\n"):
    m = re.match(r"^::([^:\n]+)::(\S+)", line)
    if m:
        L = nfc(m.group(1))
        n = mc.get(L, 0)
        if L in dic or L in titles or n >= MIN:
            r = ratio(L)
            why = f"mr={n} hi={hc.get(L, 0)} x{r:.1f}" + (" dict" if L in dic else "") + (" title" if L in titles else "")
            (flagged if r >= RATIO else kept).append((L, m.group(2), why, n))
            if r >= RATIO:
                continue
    out.append(line)

print("hotstrings whose left side is a Marathi word:", len(flagged))
for L, R, why, n in sorted(flagged, key=lambda x: -x[3]):
    print(f"  {L} -> {R}   [{why}]")
print("\nalso seen in Marathi but at least as common in Hindi, kept:", len(kept))
for L, R, why, n in sorted(kept, key=lambda x: -x[3]):
    print(f"  {L} -> {R}   [{why}]")
if "--apply" in sys.argv:
    open(AHK, "wb").write(b"\xef\xbb\xbf" + "\n".join(out).encode("utf-8"))
    print("removed", len(flagged))
