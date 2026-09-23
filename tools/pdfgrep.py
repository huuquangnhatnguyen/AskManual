"""Search the corpus for a regex, reporting doc + 1-based page + matching line.

Usage:  python tools/pdfgrep.py <regex> [file-substring] [--ctx N]
Page numbers printed are 1-based and match what a PDF viewer shows,
which is the number that goes into eval/data/gold.jsonl.
"""
import sys, io
import sys as _s
_s.stdout.reconfigure(encoding='utf-8', errors='replace')
import sys, re, glob, os, pymupdf

pat = re.compile(sys.argv[1], re.I)
filt = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else ""
ctx = 0
if "--ctx" in sys.argv:
    ctx = int(sys.argv[sys.argv.index("--ctx") + 1])

for path in sorted(glob.glob("corpus/*.pdf")):
    if filt and filt not in os.path.basename(path):
        continue
    d = pymupdf.open(path)
    for i, page in enumerate(d, start=1):
        lines = page.get_text().splitlines()
        for j, line in enumerate(lines):
            if pat.search(line):
                print(f"{os.path.basename(path)}  p{i}  {line.strip()[:160]}")
                for k in range(j + 1, min(j + 1 + ctx, len(lines))):
                    print(f"       | {lines[k].strip()[:160]}")
    d.close()
