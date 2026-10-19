import bz2, re, unicodedata, collections, json, urllib.request, sys
url="https://dumps.wikimedia.org/hiwiki/latest/hiwiki-latest-pages-articles.xml.bz2"
tok=re.compile(r"[\u0900-\u097F]+")
cnt=collections.Counter()
import subprocess
req=open(sys.argv[1] if len(sys.argv) > 1 else "hiwiki-articles.xml.bz2","rb")
dec=bz2.BZ2Decompressor()
buf=b""
n=0
while True:
    chunk=req.read(1<<20)
    if not chunk: break
    try:
        data=dec.decompress(chunk)
    except EOFError:
        break
    buf+=data
    # decode on a safe boundary
    cut=len(buf)
    while cut>0 and (buf[cut-1]&0xC0)==0x80: cut-=1
    if cut>0 and buf[cut-1]>=0xC0: cut-=1
    text=buf[:cut].decode("utf-8","ignore"); buf=buf[cut:]
    for w in tok.findall(unicodedata.normalize("NFC",text)):
        cnt[w]+=1
    n+=len(chunk)
    if dec.eof:
        rest=dec.unused_data
        dec=bz2.BZ2Decompressor()
        if rest:
            try: buf+=dec.decompress(rest)
            except Exception: pass
json.dump(cnt, open(sys.argv[2] if len(sys.argv) > 2 else "hiwiki_counts.json","w",encoding="utf-8"), ensure_ascii=False)
print("tokens", sum(cnt.values()), "types", len(cnt))
