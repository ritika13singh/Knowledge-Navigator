#!/usr/bin/env python3
"""
Ingest all allowed documents (PDF, TXT, CSV) from a data folder into the RAG index
via POST /api/rag/insert/file.

Start the app first (e.g. uvicorn backend.main:app --reload --port 8000 or python run.py).
Then: python scripts/ingest_hackathon_folder.py

Set INGEST_DIR to point at your documents folder (default: data/documents).
If the app runs on another port: BASE_URL=http://localhost:PORT python scripts/ingest_hackathon_folder.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INGEST_DIR = Path(os.environ.get("INGEST_DIR", str(ROOT / "data" / "documents")))
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".csv"}


def main():
    if not INGEST_DIR.exists():
        print(f"Folder not found: {INGEST_DIR}")
        print("Create it and add PDF/TXT/CSV files, or set INGEST_DIR=/path/to/documents")
        sys.exit(1)

    files = [
        p
        for p in sorted(INGEST_DIR.iterdir())
        if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS
    ]
    if not files:
        print(f"No PDF, TXT, or CSV files in {INGEST_DIR}")
        sys.exit(1)

    try:
        import requests
    except ImportError:
        print("Install requests: pip install requests")
        sys.exit(1)

    # Check app is reachable before uploading
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if r.status_code != 200:
            print(f"App at {BASE_URL} returned {r.status_code}. Start the app first.")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Cannot reach app at {BASE_URL}: {e}")
        print("Start the app first, e.g.: uvicorn backend.main:app --reload --port 8000")
        print("If the app is on another port: BASE_URL=http://localhost:PORT python scripts/ingest_hackathon_folder.py")
        sys.exit(1)

    print("NESsT RAG — ingest documents folder\n")
    print(f"Base URL: {BASE_URL}")
    print(f"Ingest dir: {INGEST_DIR}")
    print(f"Files to ingest: {len(files)}\n")

    ok, fail = 0, 0
    for path in files:
        name = path.name
        try:
            with open(path, "rb") as f:
                resp = requests.post(
                    f"{BASE_URL}/api/rag/insert/file",
                    files={"file": (name, f)},
                    timeout=120,
                )
            if resp.status_code == 200:
                ok += 1
                print("  OK:", name)
            else:
                fail += 1
                err = (resp.text or resp.reason or "")[:120]
                print("  FAIL:", name, resp.status_code, err)
        except requests.exceptions.RequestException as e:
            fail += 1
            print("  ERROR:", name, e)
        except Exception as e:
            fail += 1
            print("  ERROR:", name, e)

    print(f"\nDone. Ingested: {ok}, Failed: {fail}")


if __name__ == "__main__":
    main()
