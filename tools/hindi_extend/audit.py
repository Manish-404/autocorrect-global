"""Audit: for every hotstring in the Hindi file, find real words (Wikipedia >= 2 uses, dictionary, Wiktionary titles) that END with the
hotstring right after a matra/virama/anusvara/nukta - typing such a word would fire the hotstring in the middle of it.
Prints only the harmful ones: where prefix + replacement is not itself a word."""
import re, sys, unicodedata
sys.argv_orig = list(sys.argv)
sys.argv = ["x", "--cap=0"]
src = open("build.py", encoding="utf-8").read().split("# ---------- families")[0]
exec(src)
def mk(c): return unicodedata.category(c) in ("Mn", "Mc")
allbody = raw.split("/*")[0]
ents = {}
for line in allbody.splitlines():
    if line.startswith(";"): continue
    m = re.match(r"^::([^:\n]+)::(\S+)", line) or re.match(r"^:[^:\n]+:([^:\n]+)::(\S+)", line)
    if m and not line.startswith(":?"): ents[nfc(m.group(1))] = nfc(m.group(2))
idx = {}
for w in real:
    for i in range(1, len(w)):
        if mk(w[i-1]) and w[i:] in ents: idx.setdefault(w[i:], []).append(w)
bad = []; total = 0
for L, ws in idx.items():
    for w in ws:
        total += 1
        fixed = w[:len(w)-len(L)] + ents[L]
        if fixed not in real and fixed not in wc: bad.append((L, w, fixed))
print("entries that appear as the tail of a real word:", len(idx), "| word instances:", total, "| harmful (result not a word):", len(bad))
for b in sorted(bad)[:60]: print(" ", b)

import collections
agg = collections.defaultdict(lambda: [0, []])
for L, w, fixed in bad:
    agg[L][0] += wc[w]; agg[L][1].append((w, wc[w]))
print("\nper entry (total Wikipedia uses of the harmed words):")
for L, (s, ws) in sorted(agg.items(), key=lambda kv: -kv[1][0]):
    print(f"{s:6d} {L}->{ents[L]}  n={len(ws)}  e.g. " + ", ".join(w for w, _ in sorted(ws, key=lambda x: -x[1])[:4]))

if "--apply" in sys.argv_orig:
    KEEP = {"नही", "चिन्ह"}   # nही: only Marathi words are harmed; चिन्ह: the "harmed" compound still gets a valid spelling
    drop = {L for L, (s, ws) in agg.items() if (s >= 20 or len(ws) >= 5 or max(c for _, c in ws) >= 8) and L not in KEEP}
    out_lines = []; removed = []
    gen = False
    for line in raw.split("\n"):
        if line.startswith(BEGIN): gen = True
        m = re.match(r"^::([^:\n]+)::(\S+)", line)
        if m and not gen and nfc(m.group(1)) in drop:
            removed.append(line); continue
        if line.startswith(END): gen = False
        out_lines.append(line)
    open(AHK, "wb").write(b"\xef\xbb\xbf" + "\n".join(out_lines).encode("utf-8"))
    print("removed", len(removed), "hotstrings:", " ".join(r.split("::")[1] for r in removed))

print("\nentries whose worst harmed word occurs >= 5 times:")
for L, (s, ws) in sorted(agg.items(), key=lambda kv: -max(c for _, c in kv[1][1])):
    mx = max(c for _, c in ws)
    if mx >= 5: print(f"  {L}->{ents[L]}  worst: " + ", ".join(f"{w}({c})" for w, c in sorted(ws, key=lambda x: -x[1])[:3]))
