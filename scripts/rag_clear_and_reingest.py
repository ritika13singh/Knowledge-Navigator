#!/usr/bin/env python3
"""
Clear all data from the RAG index by calling rag/delete/file for each known file.
Run with the server up: python run.py  then  BASE_URL=http://localhost:8001 python scripts/rag_clear_and_reingest.py

Set INGEST_DIR to the folder containing your documents (default: data/documents).
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INGEST_DIR = Path(os.environ.get("INGEST_DIR", str(ROOT / "data" / "documents")))
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8001")


def main():
    if not INGEST_DIR.exists():
        print(f"Folder not found: {INGEST_DIR}")
        sys.exit(1)

    pdfs = sorted(INGEST_DIR.glob("*.pdf"))
    if not pdfs:
        print("No PDFs in", INGEST_DIR)
        sys.exit(1)

    print("NESsT RAG — clear all data (delete/file per document)\n")
    print(f"Base URL: {BASE_URL}")
    print(f"Ingest dir: {INGEST_DIR}")
    print(f"Files to delete: {len(pdfs)}\n")

    import urllib.request

    ok, fail = 0, 0
    for path in pdfs:
        name = path.name
        try:
            body = json.dumps({"file_name": name}).encode("utf-8")
            req = urllib.request.Request(
                f"{BASE_URL}/api/rag/delete/file",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode())
            if data.get("ok"):
                ok += 1
                print("  OK:", name)
            else:
                fail += 1
                print("  FAIL:", name, data.get("status_code"), data.get("error", "")[:80])
        except urllib.error.HTTPError as e:
            fail += 1
            body = e.read().decode() if e.fp else ""
            print("  FAIL:", name, e.code, body[:80])
        except Exception as e:
            fail += 1
            print("  ERROR:", name, e)

    print(f"\nDone. Deleted: {ok}, Failed: {fail}")


if __name__ == "__main__":
    main()
