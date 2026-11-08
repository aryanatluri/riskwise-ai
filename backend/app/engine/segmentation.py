"""Split a contract into clauses using its numbering, not blank lines.

Handles "14.2 Breach Notification SLA: ...", "Section 8.1 ...", "Clause 3 ...",
"ARTICLE 5 ..." and falls back to paragraphs for unnumbered documents.
"""

import re
from dataclasses import dataclass

NUMBERED = re.compile(
    r"^\s*(?:(?:section|clause|article)\s+)?(\d{1,3}(?:\.\d{1,3}){0,3})[.)]?\s+(\S.*)$",
    re.IGNORECASE,
)
RULE_LINE = re.compile(r"^\s*[-=_*]{5,}\s*$")


@dataclass
class Segment:
    idx: int
    section_number: str
    heading: str
    text: str


def _heading_of(rest: str) -> str:
    # "Breach Notification SLA: In the event..." -> "Breach Notification SLA"
    m = re.match(r"^([^.:]{3,80}):\s", rest)
    if m and len(m.group(1).split()) <= 10:
        return m.group(1).strip()
    words = rest.split()
    return " ".join(words[:8]) + ("..." if len(words) > 8 else "")


def segment(text: str, max_segments: int = 400) -> list[Segment]:
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").split("\n")]
    blocks: list[tuple[str, list[str]]] = []  # (section_number, lines)
    current: tuple[str, list[str]] | None = None
    preamble: list[str] = []

    for ln in lines:
        if RULE_LINE.match(ln):
            continue
        m = NUMBERED.match(ln)
        if m:
            if current:
                blocks.append(current)
            current = (m.group(1), [m.group(2)])
        elif current is not None:
            current[1].append(ln)
        else:
            preamble.append(ln)
    if current:
        blocks.append(current)

    segments: list[Segment] = []
    numbered_count = len(blocks)
    if numbered_count >= 2:
        # Drop pure headings ("8. DATA RESIDENCY AND PROCESSING") that only title their subsections,
        # but keep the title as context for the subsections' headings.
        for number, body in blocks:
            body_text = " ".join(s.strip() for s in body if s.strip())
            if not body_text:
                continue
            is_title_only = len(body) == 1 and body_text.isupper() and len(body_text.split()) <= 8
            if is_title_only:
                continue
            segments.append(Segment(len(segments), number, _heading_of(body_text), body_text))
    else:
        paras = re.split(r"\n\s*\n", text)
        for p in paras:
            p = " ".join(p.split())
            if len(p) >= 40:
                segments.append(Segment(len(segments), "", _heading_of(p), p))

    return segments[:max_segments]
