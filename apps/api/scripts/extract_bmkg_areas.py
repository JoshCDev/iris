"""One-off: extract Kemendagri level-IV codes from BMKG area_code_part*.pdf."""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

_CODE = re.compile(r"(\d{2}\.\d{2}\.\d{2}\.\d{4})\s+(.*)")
_ROW_NO = re.compile(r"^\d+\s+")

PDF_DIR = Path(r"C:\xampp\htdocs\responcepat")
OUT = Path(__file__).resolve().parents[1] / "data" / "bmkg_areas.json.gz"


def _clean_name(raw: str) -> str:
    name = _ROW_NO.sub("", raw.strip())
    name = re.split(r"\s{2,}", name)[0].strip(" -")
    return name


def extract(pdf_dir: Path = PDF_DIR) -> dict[str, str]:
    areas: dict[str, str] = {}
    files = sorted(pdf_dir.glob("area_code_part*.pdf"))
    if not files:
        raise SystemExit(f"no area_code_part*.pdf in {pdf_dir}")
    for path in files:
        print(f"reading {path.name} ...", flush=True)
        reader = PdfReader(str(path))
        for page in reader.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                m = _CODE.search(line)
                if not m:
                    continue
                code, rest = m.group(1), m.group(2)
                name = _clean_name(rest)
                if name:
                    areas[code] = name
        print(f"  {len(areas)} unique codes so far", flush=True)
    return areas


def main() -> None:
    areas = extract()
    rows = sorted(areas.items())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    main()
