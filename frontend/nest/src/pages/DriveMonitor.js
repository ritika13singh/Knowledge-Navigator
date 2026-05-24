import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  HiOutlineArrowLeft,
  HiOutlineFolder,
  HiOutlinePlay,
  HiOutlineStop,
  HiOutlineRefresh,
  HiOutlineDocumentText,
  HiOutlineUser,
  HiOutlineChevronDown,
  HiOutlineChevronUp,
} from 'react-icons/hi';
import { getApiBase, useAuth } from '../context/AuthContext';

/**
 * Parse folder ID from common Google Drive folder URLs.
 * Supports:
 *   - .../drive/folders/FOLDER_ID
 *   - .../drive/u/0/folders/FOLDER_ID (and u/1, u/2, etc.)
 *   - ...?id=FOLDER_ID
 */
function parseFolderIdFromUrl(url) {
  const s = (url || '').trim();
  if (!s) return null;
  // Match /drive/folders/ID or /drive/u/N/folders/ID (Google often uses /u/2/ for multi-account)
  const foldersMatch = s.match(/\/drive(\/u\/\d+)?\/folders\/([a-zA-Z0-9_-]+)/);
  if (foldersMatch) return foldersMatch[2];
  try {
    const u = new URL(s);
    const id = u.searchParams.get('id');
    if (id) return id;
  } catch {
    // not a valid URL
  }
  return null;
}

/** Returns true if URL looks like the generic "My Drive" page (no folder ID). */
function isMyDriveLandingUrl(url) {
  const s = (url || '').trim().toLowerCase();
  return s.includes('my-drive') || (s.includes('drive.google.com') && !s.includes('/folders/') && !parseFolderIdFromUrl(url));
}

function DriveMonitor() {
  const { user } = useAuth();
  const [driveUrl, setDriveUrl] = useState('');
  const [folderName, setFolderName] = useState('');
  const [usePersonalDrive, setUsePersonalDrive] = useState(true);
  const [monitorMyDriveRoot, setMonitorMyDriveRoot] = useState(true);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showIngestedList, setShowIngestedList] = useState(false);

  const apiBase = getApiBase();
  const isSignedIn = Boolean(user);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/api/drive/watch/status`, { credentials: 'include' });
      const data = await res.json();
      setStatus(data);
      if (!res.ok) setError(data.detail || 'Failed to load status');
      else setError(null);
      return data;
    } catch (e) {
      setError(e.message || 'Network error');
      setStatus(null);
      return null;
    }
  }, [apiBase]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // Poll status while monitoring so the user sees last_check and ingested count update
  useEffect(() => {
    if (!status?.running) return;
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, [status?.running, fetchStatus]);

  const handleStart = async (e) => {
    e.preventDefault();
    let folderId;
    let usePersonal = false;

    if (usePersonalDrive && isSignedIn) {
      usePersonal = true;
      if (monitorMyDriveRoot) {
        folderId = 'root';
      } else {
        folderId = parseFolderIdFromUrl(driveUrl);
        if (!folderId) {
          setError('Paste a folder URL (e.g. https://drive.google.com/drive/folders/...) or select "Monitor root of My Drive".');
          return;
        }
      }
    } else {
      if (isMyDriveLandingUrl(driveUrl)) {
        setError(
          'That link is your general My Drive page, not a folder. Sign in and use "Use my Google account" + "Monitor root of My Drive", or open a specific folder in Drive and paste that folder\'s URL (it will contain /folders/...).'
        );
        return;
      }
      folderId = parseFolderIdFromUrl(driveUrl);
      if (!folderId) {
        setError(
          'Enter a folder URL (e.g. https://drive.google.com/drive/folders/...). For your personal My Drive root, sign in and choose "Use my Google account" then "Monitor root of My Drive".'
        );
        return;
      }
    }

    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/api/drive/watch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          folder_id: folderId,
          folder_name: folderName.trim() || (folderId === 'root' ? 'My Drive root' : undefined),
          interval_seconds: 60,
          use_personal_drive: usePersonal,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to start monitoring');
      setStatus((prev) => ({ ...prev, running: true, folder_id: folderId, folder_name: data.folder_name }));
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to start');
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    setError(null);
    try {
      await fetch(`${apiBase}/api/drive/watch/stop`, {
        method: 'POST',
        credentials: 'include',
      });
      await fetchStatus();
    } catch (err) {
      setError(err.message || 'Failed to stop');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard drive-monitor theme-dark">
      <header className="dashboard__header">
        <Link to="/" className="dashboard__back" aria-label="Back to chat">
          <HiOutlineArrowLeft className="dashboard__back-icon" aria-hidden="true" />
          <span>Back to chat</span>
        </Link>
        <h1 className="dashboard__title">
          <HiOutlineFolder className="dashboard__title-icon" aria-hidden="true" />
          Google Drive monitor
        </h1>
        <p className="dashboard__subtitle">
          Monitor your Google Drive (personal account or a shared folder). New PDF, TXT, and CSV
          files will be automatically ingested into the knowledge base.
        </p>
      </header>

      {isSignedIn && (
        <div className="drive-monitor__drive-help" role="status">
          <strong>Using your Google account?</strong> If you see &quot;Could not get Drive access&quot;, sign out and sign in again once—this grants the app permission to read your Drive files.
        </div>
      )}

      <form className="drive-monitor__form" onSubmit={handleStart}>
        {isSignedIn && (
          <div className="drive-monitor__field drive-monitor__field--checkbox">
            <label className="drive-monitor__checkbox-label">
              <input
                type="checkbox"
                className="drive-monitor__checkbox"
                checked={usePersonalDrive}
                onChange={(e) => setUsePersonalDrive(e.target.checked)}
                disabled={status?.running}
              />
              <HiOutlineUser className="drive-monitor__checkbox-icon" aria-hidden="true" />
              Use my Google account (personal Drive)
            </label>
            <span className="drive-monitor__hint">
              Monitor files from the account you signed in with. No service account or folder sharing needed.
            </span>
          </div>
        )}

        {usePersonalDrive && isSignedIn ? (
          <>
            <div className="drive-monitor__field drive-monitor__field--radio">
              <span className="drive-monitor__label">What to monitor</span>
              <label className="drive-monitor__radio-label">
                <input
                  type="radio"
                  name="personal-target"
                  className="drive-monitor__radio"
                  checked={monitorMyDriveRoot}
                  onChange={() => setMonitorMyDriveRoot(true)}
                  disabled={status?.running}
                />
                Root of My Drive (top-level files and folders)
              </label>
              <label className="drive-monitor__radio-label">
                <input
                  type="radio"
                  name="personal-target"
                  className="drive-monitor__radio"
                  checked={!monitorMyDriveRoot}
                  onChange={() => setMonitorMyDriveRoot(false)}
                  disabled={status?.running}
                />
                A specific folder (paste URL below)
              </label>
            </div>
            {!monitorMyDriveRoot && (
              <div className="drive-monitor__field">
                <label htmlFor="drive-url" className="drive-monitor__label">
                  Folder URL
                </label>
                <input
                  id="drive-url"
                  type="url"
                  className="drive-monitor__input"
                  placeholder="https://drive.google.com/drive/folders/..."
                  value={driveUrl}
                  onChange={(e) => setDriveUrl(e.target.value)}
                  disabled={status?.running}
                  aria-describedby="drive-url-hint"
                />
              </div>
            )}
          </>
        ) : (
          <div className="drive-monitor__field">
            <label htmlFor="drive-url" className="drive-monitor__label">
              Google Drive folder URL
            </label>
            <input
              id="drive-url"
              type="url"
              className="drive-monitor__input"
              placeholder="https://drive.google.com/drive/folders/..."
              value={driveUrl}
              onChange={(e) => setDriveUrl(e.target.value)}
              disabled={status?.running}
              aria-describedby="drive-url-hint"
            />
            <span id="drive-url-hint" className="drive-monitor__hint">
              Paste the link to the folder (must be shared with the service account).
            </span>
            <p className="drive-monitor__signin-hint">
              <Link to="/login">Sign in with Google</Link> to monitor your personal Drive (e.g. root of My Drive) without a service account.
            </p>
          </div>
        )}

        <div className="drive-monitor__field">
          <label htmlFor="folder-name" className="drive-monitor__label">
            Folder name <span className="drive-monitor__optional">(optional)</span>
          </label>
          <input
            id="folder-name"
            type="text"
            className="drive-monitor__input"
            placeholder={folderName ? undefined : 'e.g. My Drive root'}
            value={folderName}
            onChange={(e) => setFolderName(e.target.value)}
            disabled={status?.running}
          />
        </div>
        <div className="drive-monitor__actions">
          {status?.running ? (
            <button
              type="button"
              className="drive-monitor__btn drive-monitor__btn--stop"
              onClick={handleStop}
              disabled={loading}
              aria-label="Stop monitoring"
            >
              <HiOutlineStop className="drive-monitor__btn-icon" aria-hidden="true" />
              Stop monitoring
            </button>
          ) : (
            <button
              type="submit"
              className="drive-monitor__btn drive-monitor__btn--start"
              disabled={loading}
              aria-label="Start monitoring"
            >
              <HiOutlinePlay className="drive-monitor__btn-icon" aria-hidden="true" />
              Start monitoring
            </button>
          )}
          <button
            type="button"
            className="dashboard__refresh drive-monitor__refresh"
            onClick={() => fetchStatus()}
            disabled={loading}
            aria-label="Refresh status"
          >
            <HiOutlineRefresh className="dashboard__refresh-icon" aria-hidden="true" />
            Refresh
          </button>
        </div>
      </form>

      {/* Completion status bar: what's happening in the background */}
      {(loading || status?.running) && (
        <div className="drive-monitor__status-bar" role="status" aria-live="polite">
          {loading && (
            <span className="drive-monitor__status-bar-message drive-monitor__status-bar-message--loading">
              <span className="drive-monitor__status-bar-spinner" aria-hidden="true" />
              Starting monitoring…
            </span>
          )}
          {!loading && status?.running && (
            <>
              {status.last_check ? (
                <span className="drive-monitor__status-bar-message">
                  Last check: {new Date(status.last_check).toLocaleString()}
                  {typeof status.last_files_listed === 'number' && (
                    <> · {status.last_files_listed} files in folder</>
                  )}
                  {(status.ingested_count ?? (status.ingested || []).length) > 0 && (
                    <> · {status.ingested_count ?? (status.ingested || []).length} ingested into knowledge base</>
                  )}
                </span>
              ) : (
                <span className="drive-monitor__status-bar-message drive-monitor__status-bar-message--loading">
                  <span className="drive-monitor__status-bar-spinner" aria-hidden="true" />
                  Monitoring started. Checking folder…
                </span>
              )}
            </>
          )}
        </div>
      )}

      {error && (
        <div className="dashboard__error" role="alert">
          {error}
        </div>
      )}

      {status && (
        <section className="drive-monitor__status" aria-live="polite">
          <h2 className="drive-monitor__status-title">Status</h2>
          <div className="dashboard__cards drive-monitor__cards">
            <div className="dashboard__card">
              <div className="dashboard__card-icon-wrap">
                <HiOutlineFolder className="dashboard__card-icon" aria-hidden="true" />
              </div>
              <div className="dashboard__card-body">
                <span className="dashboard__card-value">
                  {status.running ? 'Monitoring' : 'Stopped'}
                </span>
                <span className="dashboard__card-label">
                  {status.folder_name || status.folder_id || '—'}
                </span>
                {status.last_check && (
                  <span className="dashboard__card-meta">
                    Last check: {new Date(status.last_check).toLocaleString()}
                  </span>
                )}
                {typeof status.last_files_listed === 'number' && (
                  <span className="dashboard__card-meta">
                    Files in folder (last list): {status.last_files_listed} (only PDF, TXT, CSV are ingested)
                  </span>
                )}
              </div>
            </div>
            <div className="dashboard__card">
              <div className="dashboard__card-icon-wrap">
                <HiOutlineDocumentText className="dashboard__card-icon" aria-hidden="true" />
              </div>
              <div className="dashboard__card-body">
                <span className="dashboard__card-value">
                  {status.ingested_count ?? (status.ingested || []).length}
                </span>
                <span className="dashboard__card-label">Files ingested</span>
              </div>
            </div>
          </div>
          {status.last_error && (
            <p className="drive-monitor__last-error" role="alert">
              Error: {status.last_error}
            </p>
          )}
          {(status.ingested_count ?? (status.ingested || []).length) > 0 && (
            <div className="drive-monitor__ingested">
              <button
                type="button"
                className="drive-monitor__ingested-toggle"
                onClick={() => setShowIngestedList((v) => !v)}
                aria-expanded={showIngestedList}
              >
                {showIngestedList ? (
                  <HiOutlineChevronUp className="drive-monitor__ingested-chevron" aria-hidden="true" />
                ) : (
                  <HiOutlineChevronDown className="drive-monitor__ingested-chevron" aria-hidden="true" />
                )}
                <span>
                  {status.ingested_count ?? (status.ingested || []).length} ingested file
                  {(status.ingested_count ?? (status.ingested || []).length) !== 1 ? 's' : ''}
                  {showIngestedList ? ' (click to collapse)' : ' (click to expand)'}
                </span>
              </button>
              {showIngestedList && status.ingested && status.ingested.length > 0 && (
                <ul className="drive-monitor__ingested-list">
                  {[...(status.ingested || [])].reverse().slice(0, 50).map((item, i) => (
                    <li key={item.file_id + (item.at || '') + i} className="drive-monitor__ingested-item">
                      <span className="drive-monitor__ingested-name">{item.file_name}</span>
                      {item.at && (
                        <span className="drive-monitor__ingested-at">
                          {new Date(item.at).toLocaleString()}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

export default DriveMonitor;
