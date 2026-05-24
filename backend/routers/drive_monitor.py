"""
Google Drive folder monitoring: webhook-driven check. Run one "tick" (list folder, ingest new files)
either by an internal scheduler thread or by calling POST /api/drive/watch/tick (e.g. from cron/n8n).
UI-agnostic: status is read once via GET /watch/status; no polling required.
"""
from __future__ import annotations
import io
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from backend import documents_db, drive_tokens
from backend.auth import AuthUser, get_optional_user
from backend.config import ALLOWED_EXTENSIONS, BACKEND_PORT, UPLOAD_DIR

OptionalUser = Annotated[Optional[AuthUser], Depends(get_optional_user)]

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/drive", tags=["drive"])

# MIME types we can ingest (map to extension for RAG)
DRIVE_MIME_TO_EXT = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "application/vnd.ms-excel": ".csv",
}

_monitor_lock = threading.Lock()
_monitor_state = {
    "running": False,
    "folder_id": None,
    "folder_name": None,
    "user_sub": None,
    "seen_ids": set(),
    "last_check": None,
    "last_error": None,
    "last_files_listed": None,
    "ingested": [],
    "stop_requested": False,
    "webhook_url": None,
    "interval_seconds": 60,
}


def _get_drive_service(user_sub: Optional[str] = None):
    """
    Build Google Drive API service.
    If user_sub is set, use that user's OAuth token (personal account). Otherwise use service account.
    """
    if user_sub:
        access_token = drive_tokens.get_access_token_for_drive(user_sub)
        if not access_token:
            return None, "Could not get Drive access for your account. Sign out and sign in again, and ensure you approved Drive access."
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            creds = Credentials(token=access_token)
            service = build("drive", "v3", credentials=creds)
            return service, None
        except Exception as e:
            logger.exception("Failed to build Drive service with user token")
            return None, str(e)
    creds_path = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON", "").strip() or os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS", ""
    ).strip()
    if not creds_path or not os.path.isfile(creds_path):
        return None, "Google Drive credentials not configured. Set GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON or use 'My Google account' when signed in."
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
        service = build("drive", "v3", credentials=creds)
        return service, None
    except Exception as e:
        logger.exception("Failed to build Drive service")
        return None, str(e)


def _download_file(service, file_id: str) -> Optional[bytes]:
    """Download file content from Drive. Returns bytes or None on error."""
    try:
        from googleapiclient.http import MediaIoBaseDownload

        request = service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buf.getvalue()
    except Exception as e:
        logger.warning("Drive download failed for %s: %s", file_id, e)
        return None


def _ingest_file(content: bytes, file_name: str, suffix: str) -> bool:
    """Write content to temp file, call backend POST /api/rag/insert/file (so insert shows in access log), then delete temp file."""
    safe_name = "".join(c for c in file_name if c.isalnum() or c in "._- ") or "upload"
    if not suffix or suffix not in ALLOWED_EXTENSIONS:
        return False
    if not safe_name.endswith(suffix):
        safe_name = (safe_name.rstrip(". ") or "file") + suffix
    path = UPLOAD_DIR / safe_name
    try:
        path.write_bytes(content)
        logger.info("Drive monitor: calling RAG insert for %s (size %s bytes)", safe_name, len(content))
        # Call our own backend so "POST /api/rag/insert/file" appears in access log
        url = f"http://127.0.0.1:{BACKEND_PORT}/api/rag/insert/file"
        with httpx.Client(timeout=120.0) as client:
            with open(path, "rb") as f:
                files = {"file": (safe_name, f)}
                resp = client.post(url, files=files)
        if resp.status_code != 200:
            logger.warning("RAG insert failed for %s: %s %s", safe_name, resp.status_code, resp.text[:300])
            return False
        return True
    except Exception as e:
        logger.warning("RAG insert failed for %s: %s", safe_name, e)
        return False
    finally:
        if path.exists():
            path.unlink(missing_ok=True)


def _notify_webhook(payload: dict) -> None:
    """Fire-and-forget POST to configured webhook_url (e.g. for file_ingested events)."""
    with _monitor_lock:
        url = _monitor_state.get("webhook_url")
    if not url or not isinstance(url, str) or not url.strip():
        return
    url = url.strip()

    def _post():
        try:
            with httpx.Client(timeout=10.0) as client:
                client.post(url, json=payload)
        except Exception as e:
            logger.warning("Drive webhook POST failed to %s: %s", url[:50], e)

    threading.Thread(target=_post, daemon=True).start()


def _run_one_tick() -> None:
    """
    Run one check cycle: list Drive folder, ingest new PDF/TXT/CSV files, update state.
    Call this from the scheduler thread or from POST /watch/tick (webhook).
    """
    with _monitor_lock:
        if not _monitor_state.get("running") or _monitor_state.get("stop_requested"):
            return
        folder_id = _monitor_state.get("folder_id")
        folder_name = _monitor_state.get("folder_name")
        user_sub = _monitor_state.get("user_sub")
        if not folder_id:
            return
        seen = _monitor_state["seen_ids"]

    logger.info("Drive monitor tick: listing folder_id=%s folder_name=%s", folder_id, folder_name or folder_id)

    service, err = _get_drive_service(user_sub=user_sub)
    if err or not service:
        with _monitor_lock:
            _monitor_state["last_check"] = datetime.now(timezone.utc).isoformat()
            _monitor_state["last_error"] = err or "No Drive service"
        return

    # If folder is in a Shared Drive, we need driveId for the list call.
    drive_id = None
    try:
        folder_meta = service.files().get(fileId=folder_id, fields="driveId", supportsAllDrives=True).execute()
        drive_id = folder_meta.get("driveId")
    except Exception:
        pass

    list_params = {
        "q": f"'{folder_id}' in parents and trashed = false",
        "fields": "files(id, name, mimeType)",
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
    }
    if drive_id:
        list_params["driveId"] = drive_id
        list_params["corpora"] = "drive"

    try:
        response = service.files().list(**list_params).execute()
        files = response.get("files") or []
    except Exception as e:
        logger.warning("Drive list failed: %s", e)
        with _monitor_lock:
            _monitor_state["last_check"] = datetime.now(timezone.utc).isoformat()
            _monitor_state["last_error"] = str(e)
        return

    with _monitor_lock:
        _monitor_state["last_check"] = datetime.now(timezone.utc).isoformat()
        _monitor_state["last_error"] = None
        _monitor_state["last_files_listed"] = len(files)
        seen = _monitor_state["seen_ids"]

    ingestible = [f for f in files if DRIVE_MIME_TO_EXT.get((f.get("mimeType") or "").strip()) in ALLOWED_EXTENSIONS]
    new_count = sum(1 for f in ingestible if f.get("id") not in seen)
    logger.info(
        "Drive monitor tick: listed %s files, %s PDF/TXT/CSV, %s new (not yet ingested)",
        len(files), len(ingestible), new_count,
    )

    for f in files:
        file_id = f.get("id")
        name = f.get("name") or "unknown"
        mime = (f.get("mimeType") or "").strip()
        ext = DRIVE_MIME_TO_EXT.get(mime)
        if not ext or ext not in ALLOWED_EXTENSIONS:
            continue
        with _monitor_lock:
            if file_id in seen:
                continue
        content = _download_file(service, file_id)
        if content is None:
            continue
        if _ingest_file(content, name, ext):
            at = datetime.now(timezone.utc).isoformat()
            logger.info("Drive monitor: RAG insert completed for %s (file_id=%s)", name, file_id)
            with _monitor_lock:
                seen.add(file_id)
                _monitor_state["ingested"] = (
                    _monitor_state.get("ingested") or []
                ) + [{"file_id": file_id, "file_name": name, "at": at}]
            _notify_webhook({
                "event": "file_ingested",
                "folder_id": folder_id,
                "folder_name": folder_name,
                "file_id": file_id,
                "file_name": name,
                "at": at,
            })


def _scheduler_loop() -> None:
    """Background loop: run first tick immediately, then every interval_seconds until stop requested."""
    _run_one_tick()
    while True:
        with _monitor_lock:
            if _monitor_state.get("stop_requested"):
                _monitor_state["running"] = False
                _monitor_state["stop_requested"] = False
                break
            interval = max(30, min(3600, _monitor_state.get("interval_seconds") or 60))
        time.sleep(interval)
        _run_one_tick()
    with _monitor_lock:
        _monitor_state["running"] = False


class DriveWatchRequest(BaseModel):
    folder_id: str
    folder_name: Optional[str] = None
    interval_seconds: int = 60
    use_personal_drive: bool = False
    webhook_url: Optional[str] = None  # optional: we POST { event, file_name, ... } when a file is ingested


@router.post("/watch")
def drive_watch_start(body: DriveWatchRequest, user: OptionalUser = None):
    """
    Start monitoring a Google Drive folder. Checks run on an interval (webhook-driven: either
    internal scheduler or external POST /api/drive/watch/tick). New PDF/TXT/CSV files are ingested.
    Optionally set webhook_url to receive POST when a file is ingested.
    """
    folder_id = (body.folder_id or "").strip()
    if not folder_id:
        raise HTTPException(400, detail="folder_id is required")
    use_personal = body.use_personal_drive
    if use_personal:
        if not user:
            raise HTTPException(401, detail="Sign in with Google to use your personal Drive.")
        user_sub = user.sub
    else:
        user_sub = None

    with _monitor_lock:
        if _monitor_state.get("running"):
            raise HTTPException(409, detail="Monitoring is already running. Stop it first.")
        _monitor_state["folder_id"] = folder_id
        _monitor_state["folder_name"] = (body.folder_name or "").strip() or (folder_id if folder_id != "root" else "My Drive root")
        _monitor_state["user_sub"] = user_sub
        _monitor_state["running"] = True
        _monitor_state["stop_requested"] = False
        _monitor_state["ingested"] = []
        _monitor_state["last_error"] = None
        _monitor_state["seen_ids"] = set()
        _monitor_state["interval_seconds"] = max(30, min(3600, body.interval_seconds))
        _monitor_state["webhook_url"] = (body.webhook_url or "").strip() or None

    service, err = _get_drive_service(user_sub=user_sub)
    if err or not service:
        with _monitor_lock:
            _monitor_state["running"] = False
        raise HTTPException(503, detail=err or "Google Drive not configured")

    threading.Thread(target=_scheduler_loop, daemon=True).start()
    return {
        "status": "started",
        "folder_id": folder_id,
        "folder_name": _monitor_state["folder_name"],
        "message": "First check runs immediately; then every interval_seconds. Use GET /watch/status to see last_check and last_error.",
    }


@router.post("/watch/tick")
def drive_watch_tick(
    x_drive_webhook_secret: Optional[str] = Header(None, alias="X-Drive-Webhook-Secret"),
):
    """
    Webhook: run one check cycle now. Call this from cron, n8n, or Cloud Scheduler to drive
    checks without relying on the internal scheduler. If DRIVE_WEBHOOK_SECRET is set, request
    must include header X-Drive-Webhook-Secret with that value.
    """
    secret = (os.getenv("DRIVE_WEBHOOK_SECRET") or "").strip()
    if secret and secret != (x_drive_webhook_secret or ""):
        raise HTTPException(401, detail="Invalid or missing X-Drive-Webhook-Secret")
    _run_one_tick()
    with _monitor_lock:
        return {
            "status": "tick_complete",
            "running": _monitor_state.get("running", False),
            "last_check": _monitor_state.get("last_check"),
            "last_error": _monitor_state.get("last_error"),
        }


@router.get("/watch/status")
def drive_watch_status():
    """Return current monitoring status (single read; no polling needed)."""
    with _monitor_lock:
        ingested_all = list(_monitor_state.get("ingested") or [])
        return {
            "running": _monitor_state.get("running", False),
            "folder_id": _monitor_state.get("folder_id"),
            "folder_name": _monitor_state.get("folder_name"),
            "use_personal_drive": bool(_monitor_state.get("user_sub")),
            "last_check": _monitor_state.get("last_check"),
            "last_error": _monitor_state.get("last_error"),
            "last_files_listed": _monitor_state.get("last_files_listed"),
            "ingested_count": len(ingested_all),
            "ingested": ingested_all[-50:],
        }


@router.post("/watch/stop")
def drive_watch_stop():
    """Stop the Drive folder monitoring."""
    with _monitor_lock:
        _monitor_state["stop_requested"] = True
    return {"status": "stop_requested"}
