"""Print the text of given 1-based PDF pages. Usage: python tools/pdfpage.py <file-substring> <page> [page...]"""
import sys, io
import sys as _s
_s.stdout.reconfigure(encoding='utf-8', errors='replace')
import sys, glob, os, pymupdf
filt = sys.argv[1]
path = [p for p in sorted(glob.glob("corpus/*.pdf")) if filt in os.path.basename(p)][0]
d = pymupdf.open(path)
for a in sys.argv[2:]:
    i = int(a)
    print(f"===== {os.path.basename(path)} PDF page {i} =====")
    print(d[i-1].get_text())
d.close()
