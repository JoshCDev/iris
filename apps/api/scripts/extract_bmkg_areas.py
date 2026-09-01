"""One-off: extract Kemendagri level-IV codes from BMKG area_code_part*.pdf."""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

_CODE = re.compile(r"(\d{2}\.\d{2}\.\d{2}\.\d{4})\s+(.*)")
_ROW_NO = re.compile(r"^\d+\s+")

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "apps" / "api" / "data" / "bmkg_areas.json.gz"


def _clean_name(raw: str) -> str:
    name = _ROW_NO.sub("", raw.strip())
    name = re.split(r"\s{2,}", name)[0].strip(" -")
    return name


def extract(pdf_dir: Path) -> dict[str, str]:
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


def main(pdf_dir: Path) -> None:
    if not pdf_dir.is_dir():
        raise SystemExit(
            f"pdf directory not found: {pdf_dir}\n"
            "Pass --pdf-dir containing the BMKG area_code_part*.pdf files.")
    areas = extract(pdf_dir)
    rows = sorted(areas.items())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    ap = argparse.ArgumentParser(
        description="Extract Kemendagri level-IV codes from BMKG area PDFs")
    ap.add_argument("--pdf-dir", type=Path, required=True,
                    help="directory containing area_code_part*.pdf")
    args = ap.parse_args()
    main(args.pdf_dir)
