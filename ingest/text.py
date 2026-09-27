"""Text normalisation and fault-code extraction shared by the chunkers."""
import re

_PUA = re.compile(r"[-]")          # symbol-font bullets, e.g. U+F06E
_HYPHEN_BREAK = re.compile(r"(\w)-\n(?=[a-z])")
_WS = re.compile(r"\s+")

# All-digit codes collide with parameter values, years and page numbers, so they
# only count next to a keyword. Letter-led codes (A2B1, AFF6) need one digit, so
# ordinary capitalised words (FACE, BEAD) don't match.
_KEYWORD_CODE = re.compile(r"\b(?:fault|warning|event|alarm)s?(?:\s+code)?\s*\(?([0-9A-Fa-f]{4})\b", re.I)
_LETTER_CODE = re.compile(r"\b(?=[A-F][0-9A-F]{3}\b)(?=\w*\d)[A-F][0-9A-F]{3}\b")
FAULT_CODE = re.compile(r"^[0-9A-F]{4}$")


def clean(s: str) -> str:
    s = s.replace("­", "")
    s = _PUA.sub(" ", s)
    s = _HYPHEN_BREAK.sub(r"\1", s)
    return _WS.sub(" ", s).strip()


def codes_in_prose(text: str) -> list[str]:
    found = [m.upper() for m in _KEYWORD_CODE.findall(text)] + _LETTER_CODE.findall(text)
    return sorted(set(found))
