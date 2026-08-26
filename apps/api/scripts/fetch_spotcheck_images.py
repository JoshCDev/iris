"""Fetch candidate real-photo rice-disease images from Wikimedia Commons.

Queries the Commons API per class, downloads the top image candidates into
experiments/data/field_spotcheck/<class>/ for manual label verification.
"""
from __future__ import annotations

import json
import pathlib
import urllib.parse
import urllib.request

OUT_ROOT = pathlib.Path(r"C:\xampp\htdocs\iris-platform\experiments\data\field_spotcheck")

QUERIES = {
    "blast": [
        'filetype:bitmap rice blast leaf lesion',
        'filetype:bitmap Magnaporthe oryzae leaf',
    ],
    "brown_spot": [
        'filetype:bitmap rice brown spot leaf Bipolaris',
        'filetype:bitmap Cochliobolus miyabeanus rice',
    ],
    "bacterial_leaf_blight": [
        'filetype:bitmap rice bacterial leaf blight Xanthomonas',
        'filetype:bitmap bacterial blight rice leaf',
    ],
    "tungro": [
        'filetype:bitmap rice tungro disease',
        'filetype:bitmap tungro virus rice leaf',
    ],
}

HEADERS = {"User-Agent": "IRIS-spotcheck/1.0 (academic model evaluation)"}


def api_search(term: str, limit: int = 6) -> list[dict]:
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": term,
        "gsrnamespace": "6",
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|size|mime",
        "iiurlwidth": "1024",
        "format": "json",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    pages = data.get("query", {}).get("pages", {})
    out = []
    for p in pages.values():
        for ii in p.get("imageinfo", []):
            if ii.get("mime") in ("image/jpeg", "image/png") and ii.get("width", 0) >= 400:
                out.append({"title": p.get("title", ""), "url": ii.get("thumburl") or ii.get("url"),
                            "w": ii.get("width"), "h": ii.get("height")})
    return out


def main() -> None:
    for cls, terms in QUERIES.items():
        dest = OUT_ROOT / cls
        dest.mkdir(parents=True, exist_ok=True)
        seen: set[str] = set()
        n = 0
        for term in terms:
            try:
                results = api_search(term)
            except Exception as exc:  # noqa: BLE001
                print(f"[{cls}] search failed: {exc}")
                continue
            for item in results:
                if item["url"] in seen or n >= 5:
                    continue
                seen.add(item["url"])
                n += 1
                ext = ".jpg" if "jpeg" in item["url"].lower() or ".jpg" in item["url"].lower() else ".png"
                path = dest / f"{cls}_{n}{ext}"
                try:
                    req = urllib.request.Request(item["url"], headers=HEADERS)
                    with urllib.request.urlopen(req, timeout=40) as r:
                        path.write_bytes(r.read())
                    print(f"[{cls}] saved {path.name}  <- {item['title']} ({item['w']}x{item['h']})")
                except Exception as exc:  # noqa: BLE001
                    print(f"[{cls}] download failed {item['title']}: {exc}")
                    n -= 1


if __name__ == "__main__":
    main()
