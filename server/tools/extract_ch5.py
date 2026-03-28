from __future__ import annotations

import re
import sys
from pathlib import Path

from pypdf import PdfReader


def extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def find_chapter_5(full_text: str) -> str | None:
    # Support both Arabic numerals and Chinese numerals.
    start_match = (
        re.search(r"第\s*5\s*章[\s\S]{0,40}?(系统实现|系统功能实现|功能实现)", full_text)
        or re.search(r"第\s*五\s*章[\s\S]{0,40}?(系统实现|系统功能实现|功能实现)", full_text)
        or re.search(r"第\s*5\s*章", full_text)
        or re.search(r"第\s*五\s*章", full_text)
    )
    if not start_match:
        return None

    start = start_match.start()
    rest = full_text[start:]
    end_match = re.search(r"第\s*6\s*章|第\s*六\s*章", rest)
    end = start + (end_match.start() if end_match else len(rest))
    return full_text[start:end]


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python extract_ch5.py <path-to-pdf>")
        return 2

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"PDF_NOT_FOUND: {pdf_path}")
        return 2

    full = extract_text(pdf_path)
    ch5 = find_chapter_5(full)
    if not ch5:
        print("CH5_NOT_FOUND")
        # Print some chapter-like titles to help debugging.
        for pat in [r"第\s*[0-9]+\s*章[^\n]{0,60}", r"第\s*[一二三四五六七八九十]+\s*章[^\n]{0,60}"]:
            hits = re.findall(pat, full)
            if hits:
                print("SAMPLE_TITLES")
                for h in hits[:30]:
                    print(h.strip())
        return 0

    print("CH5_FOUND")

    # Extract section headings like 5.1 / 5.2.3.
    sec = re.findall(r"\n\s*(5\.[0-9]+(?:\.[0-9]+)?)\s+([^\n]{2,80})", ch5)
    seen: set[tuple[str, str]] = set()
    if sec:
        print("CH5_SECTIONS")
        for num, title in sec:
            t = re.sub(r"\s+", " ", title).strip(" -·\t")
            key = (num, t)
            if key in seen:
                continue
            seen.add(key)
            print(f"{num} {t}")
        return 0

    # Fallback: print lines that look like 5.x headings.
    print("CH5_LINES")
    for ln in ch5.splitlines():
        s = re.sub(r"\s+", " ", ln).strip()
        if re.match(r"^5\.[0-9]", s):
            print(s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
