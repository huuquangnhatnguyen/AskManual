"""Verify every eval/data/gold.jsonl entry against the PDF page it cites.

For each entry, opens doc_id at `page` (1-based PDF index, NOT the printed
number) and checks that distinctive content words from answer_gist actually
appear there. Diagram entries carry their answer in the image rather than the
text layer, so those are held to the weaker test that the section heading is
present on the page.

Run:  python tools/verify_gold.py
Exit code is non-zero if any entry fails, so this can gate a commit.
"""
import sys, io, json, re, glob, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pymupdf

STOP = set("""the a an and or of to in on for with is are was were be been it its this that
these those from at as by if then than which what when where how do does did you your i my
also not no yes can could should would may might must will shall there here their them they
he she his her we us our one two three all any each some more most other another same such
only own so too very just now new old good best first last long great little much many
""".split())

def words(s):
    return [w for w in re.findall(r"[a-z0-9]{4,}", s.lower()) if w not in STOP]

rows = [json.loads(l) for l in io.open("eval/data/gold.jsonl", encoding="utf-8") if l.strip()]
docs = {os.path.basename(p)[:-4]: p for p in glob.glob("corpus/*.pdf")}

fails = 0
for r in rows:
    path = docs.get(r["doc_id"])
    if not path:
        print(f"FAIL {r['id']}  no such doc: {r['doc_id']}")
        fails += 1
        continue
    # A flattened "scan" has no text layer; check the gold against its digital original.
    digital = os.path.join("corpus", "_digital", os.path.basename(path))
    d = pymupdf.open(digital if os.path.exists(digital) else path)
    if not (1 <= r["page"] <= len(d)):
        print(f"FAIL {r['id']}  page {r['page']} out of range (doc has {len(d)})")
        fails += 1
        d.close()
        continue
    text = d[r["page"] - 1].get_text().lower()
    d.close()

    if r["query_type"] == "diagram":
        key = words(r["section"])
        hit = sum(1 for w in key if w in text)
        ok = hit >= max(1, len(key) // 2)
        detail = f"section terms {hit}/{len(key)}"
    else:
        key = words(r["answer_gist"])
        hit = sum(1 for w in key if w in text)
        ok = len(key) and hit / len(key) >= 0.25
        detail = f"answer terms {hit}/{len(key)} = {hit/max(1,len(key)):.0%}"

    print(f"{'PASS' if ok else 'FAIL'} {r['id']}  {r['doc_id']} p{r['page']}  ({r['query_type']}, {detail})")
    if not ok:
        fails += 1

print(f"\n{len(rows) - fails}/{len(rows)} verified")
sys.exit(1 if fails else 0)
