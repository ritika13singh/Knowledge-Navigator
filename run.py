#!/usr/bin/env python3
"""Run Knowledge Navigator prototype."""
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    from backend.config import BACKEND_PORT
    load_dotenv(Path(__file__).parent / ".env")
    uvicorn.run(
        "backend.main:app",
        host="localhost",
        port=BACKEND_PORT,
        reload=True,
    )
