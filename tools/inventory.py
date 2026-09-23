import pymupdf, glob, os, subprocess
for path in sorted(glob.glob("corpus/*.pdf")):
    d = pymupdf.open(path)
    toc = d.get_toc()
    txt = sum(len(p.get_text().strip()) for p in d)
    print(f"--- {os.path.basename(path)}")
    print(f"    pages={len(d)}  size={os.path.getsize(path)/1e6:.1f}MB  text_chars={txt}  toc_entries={len(toc)}")
    for lvl, title, pg in toc[:40]:
        if lvl <= 2:
            print(f"      L{lvl} p{pg:<4d} {title[:70]}")
    d.close()
