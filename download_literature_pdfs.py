"""
Download all reachable PDFs referenced in `literature review.xlsx`
(columns Published_Link / Original_Link) into a single folder.

- arXiv abs/pdf links -> normalized to the PDF endpoint.
- Other links ending in .pdf -> downloaded as-is.
- Everything else (paywalled IEEE/ACM/ResearchGate/MDPI html, conference
  tracker pages without a direct PDF, etc.) is skipped and logged.

Usage:
    python download_literature_pdfs.py
"""
import csv
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import openpyxl
import requests

ROOT = Path(__file__).parent
XLSX_PATH = ROOT / "literature review.xlsx"
OUT_DIR = ROOT / "literature_review_pdfs"
LOG_PATH = OUT_DIR / "_download_log.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

ARXIV_ABS_RE = re.compile(r"arxiv\.org/(?:abs|pdf|html)/([\w.\-]+?)(?:v\d+)?(?:\.pdf|\.html)?/?$")


def sanitize_filename(name: str, max_len: int = 150) -> str:
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) > max_len:
        name = name[:max_len].rstrip()
    return name or "untitled"


def to_arxiv_pdf_url(url: str) -> str | None:
    m = ARXIV_ABS_RE.search(url)
    if not m:
        return None
    arxiv_id = m.group(1)
    return f"https://arxiv.org/pdf/{arxiv_id}"


def candidate_pdf_url(link: str) -> str | None:
    if not link:
        return None
    if "arxiv.org" in link:
        pdf_url = to_arxiv_pdf_url(link)
        if pdf_url:
            return pdf_url
    parsed = urlparse(link)
    if parsed.path.lower().endswith(".pdf"):
        return link
    return None


def download(url: str, dest: Path) -> tuple[bool, str]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower() and not resp.content[:5].startswith(b"%PDF"):
            return False, f"not a PDF (content-type={content_type})"
        dest.write_bytes(resp.content)
        return True, "ok"
    except requests.RequestException as e:
        return False, str(e)


def main():
    OUT_DIR.mkdir(exist_ok=True)
    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
    ws = wb["Sheet1"]
    rows = list(ws.iter_rows(min_row=2, values_only=True))

    seen_titles = {}
    log_rows = []
    downloaded, skipped = 0, 0

    for i, row in enumerate(rows, start=2):
        title, published_link, original_link = row[0], row[4], row[10]
        if not title:
            continue

        base_name = sanitize_filename(title)
        # de-duplicate identical titles (e.g. rows 36/101, 37/102)
        count = seen_titles.get(base_name, 0)
        seen_titles[base_name] = count + 1
        fname = base_name if count == 0 else f"{base_name} ({count})"
        dest = OUT_DIR / f"{fname}.pdf"

        if dest.exists():
            log_rows.append([i, title, "skip", "already downloaded"])
            continue

        pdf_url = candidate_pdf_url(published_link) or candidate_pdf_url(original_link)
        if not pdf_url:
            print(f"[SKIP] row {i}: no direct PDF link -> {title}")
            log_rows.append([i, title, "skip", f"no pdf link (pub={published_link}, orig={original_link})"])
            skipped += 1
            continue

        ok, msg = download(pdf_url, dest)
        if ok:
            print(f"[OK]   row {i}: {title} <- {pdf_url}")
            log_rows.append([i, title, "downloaded", pdf_url])
            downloaded += 1
        else:
            print(f"[FAIL] row {i}: {title} <- {pdf_url} ({msg})")
            log_rows.append([i, title, "fail", f"{pdf_url} :: {msg}"])
            skipped += 1
            if dest.exists():
                dest.unlink()

        time.sleep(1)  # be polite to arxiv.org / hosts

    with LOG_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["row", "title", "status", "detail"])
        writer.writerows(log_rows)

    print(f"\nDone. Downloaded: {downloaded}, skipped/failed: {skipped}.")
    print(f"Log written to {LOG_PATH}")


if __name__ == "__main__":
    main()
