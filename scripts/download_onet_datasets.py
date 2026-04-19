#!/usr/bin/env python3
"""Download and stage O*NET database files needed for the TrueHire RAG pipeline.

O*NET publishes a freely downloadable text database at:
  https://www.onetcenter.org/database.html

This script downloads the current release, extracts the five files required for
RAG knowledge-base construction, and places them in the Archive/ directory.

Usage
-----
    python scripts/download_onet_datasets.py

    # Specify a version manually if the default fails:
    python scripts/download_onet_datasets.py --version 29.0

Files downloaded into Archive/
-------------------------------
  Occupation Data.txt          — one row per occupation with a text description
  Task Statements.txt          — specific task statements per occupation (~20 per job)
  Skills.txt                   — 35 cognitive/behavioural skills rated per occupation
  Knowledge.txt                — 33 knowledge domains rated per occupation
  Education, Training, and Experience.txt  — education level requirements per job
"""
import argparse
import io
import sys
import zipfile
from pathlib import Path

# Try requests first; fall back to urllib
try:
    import requests
    def _download(url: str) -> bytes:
        r = requests.get(url, stream=True, timeout=120)
        r.raise_for_status()
        return r.content
except ImportError:
    import urllib.request
    def _download(url: str) -> bytes:           # type: ignore[misc]
        with urllib.request.urlopen(url, timeout=120) as resp:
            return resp.read()


# ── Config ────────────────────────────────────────────────────────────────────

# Files we need from the O*NET text zip
REQUIRED_FILES = [
    "Occupation Data.txt",
    "Task Statements.txt",
    "Skills.txt",
    "Knowledge.txt",
    "Education, Training, and Experience.txt",
]

# O*NET releases minor versions (e.g., 29.0, 29.1). Try these in order.
CANDIDATE_VERSIONS = ["29.1", "29.0", "28.3", "28.2", "28.1", "28.0"]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIR  = PROJECT_ROOT / "Archive"


# ── Helpers ───────────────────────────────────────────────────────────────────

def build_url(version: str) -> str:
    ver_slug = version.replace(".", "_")
    return f"https://www.onetcenter.org/dl_files/database/db_{ver_slug}_text.zip"


def try_download(version: str) -> bytes | None:
    url = build_url(version)
    print(f"  Trying {url} ...", end=" ", flush=True)
    try:
        data = _download(url)
        print("OK")
        return data
    except Exception as exc:
        print(f"FAILED ({exc})")
        return None


def extract_files(zip_bytes: bytes, dest_dir: Path) -> list[str]:
    """Extract REQUIRED_FILES from the zip into dest_dir. Returns list of saved paths."""
    saved = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        members = zf.namelist()
        for required in REQUIRED_FILES:
            # The zip may put files in a subdirectory — search by basename
            matches = [m for m in members if Path(m).name == required]
            if not matches:
                print(f"  WARNING: '{required}' not found in archive.")
                continue
            member = matches[0]
            dest = dest_dir / required
            data = zf.read(member)
            dest.write_bytes(data)
            saved.append(str(dest))
            print(f"  Extracted → {dest.relative_to(PROJECT_ROOT)}")
    return saved


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Download O*NET datasets for RAG.")
    parser.add_argument("--version", help="O*NET version (e.g. 29.0). Auto-detected if omitted.")
    args = parser.parse_args()

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    # Check which files are already present
    missing = [f for f in REQUIRED_FILES if not (ARCHIVE_DIR / f).exists()]
    if not missing:
        print("All required O*NET files are already present in Archive/. Nothing to do.")
        return
    print(f"Missing files: {missing}")

    versions = [args.version] if args.version else CANDIDATE_VERSIONS
    zip_bytes = None
    for version in versions:
        zip_bytes = try_download(version)
        if zip_bytes:
            break

    if not zip_bytes:
        print(
            "\nCould not download O*NET database automatically.\n"
            "Please visit https://www.onetcenter.org/database.html,\n"
            "download the 'Text' version of the database, and extract\n"
            f"the following files into {ARCHIVE_DIR}:\n"
            + "\n".join(f"  - {f}" for f in REQUIRED_FILES)
        )
        sys.exit(1)

    print(f"\nExtracting files into {ARCHIVE_DIR.relative_to(PROJECT_ROOT)}/")
    saved = extract_files(zip_bytes, ARCHIVE_DIR)

    print(f"\nDone. {len(saved)}/{len(REQUIRED_FILES)} files saved.")
    if len(saved) < len(REQUIRED_FILES):
        still_missing = [f for f in REQUIRED_FILES if not (ARCHIVE_DIR / f).exists()]
        print("Still missing:", still_missing)
    else:
        print("RAG knowledge base is ready to build.")


if __name__ == "__main__":
    main()
