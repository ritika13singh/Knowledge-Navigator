import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  HiOutlineChartBar,
  HiOutlineClock,
  HiOutlineThumbUp,
  HiOutlineThumbDown,
  HiOutlineArrowLeft,
  HiOutlineRefresh,
  HiOutlineFolder,
  HiOutlineDatabase,
  HiOutlinePlay,
  HiOutlineStop,
  HiOutlineDocumentText,
  HiOutlineUser,
  HiOutlineChevronDown,
  HiOutlineChevronUp,
} from 'react-icons/hi';
import { getApiBase, useAuth } from '../context/AuthContext';

// ─── helpers ─────────────────────────────────────────────────────────────────

const PERIODS = [
  { value: '7', label: 'Last 7 days' },
  { value: '30', label: 'Last 30 days' },
  { value: 'all', label: 'All time' },
];

function formatLatency(seconds) {
  if (seconds == null || seconds === 0) return '—';
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)} ms`;
  return `${Number(seconds).toFixed(1)}s`;
}

function getDateRange(period) {
  if (period === 'all') return { date_from: null, date_to: null };
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - parseInt(period, 10));
  return { date_from: from.toISOString().slice(0, 10), date_to: to.toISOString().slice(0, 10) };
}

function parseFolderIdFromUrl(url) {
  const s = (url || '').trim();
  if (!s) return null;
  const m = s.match(/\/drive(\/u\/\d+)?\/folders\/([a-zA-Z0-9_-]+)/);
  if (m) return m[2];
  try {
    const id = new URL(s).searchParams.get('id');
    if (id) return id;
  } catch {}
  return null;
}

function isMyDriveLandingUrl(url) {
  const s = (url || '').trim().toLowerCase();
  return s.includes('my-drive') || (s.includes('drive.google.com') && !s.includes('/folders/') && !parseFolderIdFromUrl(url));
}

function statusIcon(status) {
  if (status === 'ok') return '✓';
  if (status === 'skipped') return '–';
  return '✗';
}

// ─── Drive Monitor tab ────────────────────────────────────────────────────────

function DriveMonitorTab() {
  const { user } = useAuth();
  const apiBase = getApiBase();
  const isSignedIn = Boolean(user);

  const [driveUrl, setDriveUrl] = useState('');
  const [folderName, setFolderName] = useState('');
  const [usePersonalDrive, setUsePersonalDrive] = useState(true);
  const [monitorMyDriveRoot, setMonitorMyDriveRoot] = useState(true);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showIngestedList, setShowIngestedList] = useState(false);

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
      return null;
    }
  }, [apiBase]);

  useEffect(() => { fetchStatus(); }, [fetchStatus]);

  useEffect(() => {
    if (!status?.running) return;
    const iv = setInterval(fetchStatus, 10000);
    return () => clearInterval(iv);
  }, [status?.running, fetchStatus]);

  const handleStart = async (e) => {
    e.preventDefault();
    let folderId, usePersonal = false;
    if (usePersonalDrive && isSignedIn) {
      usePersonal = true;
      folderId = monitorMyDriveRoot ? 'root' : parseFolderIdFromUrl(driveUrl);
      if (!folderId) { setError('Paste a folder URL or select "Monitor root of My Drive".'); return; }
    } else {
      if (isMyDriveLandingUrl(driveUrl)) { setError('Paste a specific folder URL (containing /folders/…).'); return; }
      folderId = parseFolderIdFromUrl(driveUrl);
      if (!folderId) { setError('Enter a valid Google Drive folder URL.'); return; }
    }
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${apiBase}/api/drive/watch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ folder_id: folderId, folder_name: folderName.trim() || undefined, interval_seconds: 60, use_personal_drive: usePersonal }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to start');
      setStatus((p) => ({ ...p, running: true, folder_id: folderId, folder_name: data.folder_name }));
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await fetch(`${apiBase}/api/drive/watch/stop`, { method: 'POST', credentials: 'include' });
      await fetchStatus();
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="dp-tab-content">
      <p className="dp-tab-desc">
        Monitor your Google Drive for new PDF, TXT, and CSV files — they are automatically ingested into the knowledge base.
      </p>

      {isSignedIn && (
        <div className="dp-drive-hint">
          <strong>Signed in as {user.email}.</strong> If you see "Could not get Drive access", sign out and back in to grant Drive permissions.
        </div>
      )}

      <form className="dp-form" onSubmit={handleStart}>
        {isSignedIn && (
          <label className="dp-checkbox-row">
            <input type="checkbox" checked={usePersonalDrive} onChange={(e) => setUsePersonalDrive(e.target.checked)} disabled={status?.running} />
            <HiOutlineUser className="dp-row-icon" />
            Use my Google account (personal Drive)
          </label>
        )}

        {usePersonalDrive && isSignedIn ? (
          <div className="dp-radio-group">
            <label className="dp-radio-row">
              <input type="radio" name="target" checked={monitorMyDriveRoot} onChange={() => setMonitorMyDriveRoot(true)} disabled={status?.running} />
              Root of My Drive
            </label>
            <label className="dp-radio-row">
              <input type="radio" name="target" checked={!monitorMyDriveRoot} onChange={() => setMonitorMyDriveRoot(false)} disabled={status?.running} />
              A specific folder (paste URL below)
            </label>
            {!monitorMyDriveRoot && (
              <input className="dp-input" type="url" placeholder="https://drive.google.com/drive/folders/…" value={driveUrl} onChange={(e) => setDriveUrl(e.target.value)} disabled={status?.running} />
            )}
          </div>
        ) : (
          <div className="dp-field">
            <label className="dp-label">Google Drive folder URL</label>
            <input className="dp-input" type="url" placeholder="https://drive.google.com/drive/folders/…" value={driveUrl} onChange={(e) => setDriveUrl(e.target.value)} disabled={status?.running} />
            {!isSignedIn && (
              <span className="dp-hint"><Link to="/login">Sign in with Google</Link> to monitor your personal Drive without a service account.</span>
            )}
          </div>
        )}

        <div className="dp-field">
          <label className="dp-label">Folder name <span className="dp-optional">(optional)</span></label>
          <input className="dp-input" type="text" placeholder="e.g. NESsT Knowledge" value={folderName} onChange={(e) => setFolderName(e.target.value)} disabled={status?.running} />
        </div>

        <div className="dp-actions">
          {status?.running ? (
            <button type="button" className="dp-btn dp-btn--stop" onClick={handleStop} disabled={loading}>
              <HiOutlineStop className="dp-btn-icon" /> Stop monitoring
            </button>
          ) : (
            <button type="submit" className="dp-btn dp-btn--start" disabled={loading}>
              <HiOutlinePlay className="dp-btn-icon" /> Start monitoring
            </button>
          )}
          <button type="button" className="dp-btn dp-btn--ghost" onClick={fetchStatus} disabled={loading}>
            <HiOutlineRefresh className="dp-btn-icon" /> Refresh
          </button>
        </div>
      </form>

      {error && <div className="dashboard__error" role="alert">{error}</div>}

      {status && (
        <div className="dp-status-cards">
          <div className="dp-stat">
            <HiOutlineFolder className="dp-stat-icon" />
            <div>
              <span className="dp-stat-value">{status.running ? 'Monitoring' : 'Stopped'}</span>
              <span className="dp-stat-label">{status.folder_name || status.folder_id || 'No folder set'}</span>
              {status.last_check && <span className="dp-stat-meta">Last check: {new Date(status.last_check).toLocaleString()}</span>}
              {typeof status.last_files_listed === 'number' && <span className="dp-stat-meta">{status.last_files_listed} files listed</span>}
            </div>
          </div>
          <div className="dp-stat">
            <HiOutlineDocumentText className="dp-stat-icon" />
            <div>
              <span className="dp-stat-value">{status.ingested_count ?? (status.ingested || []).length}</span>
              <span className="dp-stat-label">Files ingested</span>
            </div>
          </div>
        </div>
      )}

      {status?.last_error && <p className="dp-error-inline">Error: {status.last_error}</p>}

      {(status?.ingested_count ?? (status?.ingested || []).length) > 0 && (
        <div className="dp-ingested">
          <button type="button" className="dp-ingested-toggle" onClick={() => setShowIngestedList((v) => !v)}>
            {showIngestedList ? <HiOutlineChevronUp /> : <HiOutlineChevronDown />}
            {status.ingested_count ?? status.ingested.length} ingested file{(status.ingested_count ?? status.ingested.length) !== 1 ? 's' : ''} — {showIngestedList ? 'collapse' : 'expand'}
          </button>
          {showIngestedList && (
            <ul className="dp-ingested-list">
              {[...(status.ingested || [])].reverse().slice(0, 50).map((item, i) => (
                <li key={item.file_id + i} className="dp-ingested-item">
                  <span>{item.file_name}</span>
                  {item.at && <span className="dp-ingested-at">{new Date(item.at).toLocaleString()}</span>}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Local Ingest tab ─────────────────────────────────────────────────────────

function LocalIngestTab() {
  const [ingest, setIngest] = useState(null);
  const [ingestLoading, setIngestLoading] = useState(false);
  const pollRef = useRef(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${getApiBase()}/api/rag/ingest/status`, { credentials: 'include' });
      const json = await res.json();
      setIngest(json);
      return json;
    } catch { return null; }
  }, []);

  const startIngest = async () => {
    setIngestLoading(true);
    try {
      await fetch(`${getApiBase()}/api/rag/ingest/data-dir`, { method: 'POST', credentials: 'include' });
      const json = await fetchStatus();
      if (json?.running) {
        pollRef.current = setInterval(async () => {
          const s = await fetchStatus();
          if (!s?.running) clearInterval(pollRef.current);
        }, 3000);
      }
    } finally { setIngestLoading(false); }
  };

  useEffect(() => {
    fetchStatus();
    return () => clearInterval(pollRef.current);
  }, [fetchStatus]);

  const ok = ingest?.results?.filter(r => r.status === 'ok').length ?? 0;
  const skipped = ingest?.results?.filter(r => r.status === 'skipped').length ?? 0;
  const errors = ingest?.results?.filter(r => r.status === 'error').length ?? 0;

  return (
    <div className="dp-tab-content">
      <p className="dp-tab-desc">
        Index all PDF, TXT, and CSV files in the <code>data/documents/</code> folder.
        Files already in ChromaDB are skipped — no duplicate embedding calls.
      </p>

      <div className="dp-actions">
        <button
          type="button"
          className="dp-btn dp-btn--start"
          onClick={startIngest}
          disabled={ingestLoading || ingest?.running}
        >
          <HiOutlineDatabase className="dp-btn-icon" />
          {ingest?.running ? `Ingesting… (${ingest.processed}/${ingest.total})` : 'Start Ingest'}
        </button>
        <button type="button" className="dp-btn dp-btn--ghost" onClick={fetchStatus}>
          <HiOutlineRefresh className="dp-btn-icon" /> Refresh
        </button>
        {ingest?.running && ingest?.current_file && (
          <span className="dp-current-file">Processing: {ingest.current_file}</span>
        )}
      </div>

      {ingest && !ingest.running && ingest.finished_at && (
        <div className="dp-summary">
          Completed at {new Date(ingest.finished_at).toLocaleTimeString()} —{' '}
          <span className="dp-summary--ok">{ok} indexed</span>,{' '}
          <span className="dp-summary--skip">{skipped} skipped</span>,{' '}
          <span className="dp-summary--err">{errors} errors</span>
        </div>
      )}

      {ingest?.results?.length > 0 && (
        <table className="dp-table">
          <thead>
            <tr><th>File</th><th>Status</th><th>Chunks</th></tr>
          </thead>
          <tbody>
            {ingest.results.map((r, i) => (
              <tr key={i} className={`dp-table-row--${r.status}`}>
                <td className="dp-table-filename">{r.filename}</td>
                <td>{statusIcon(r.status)} {r.status}{r.error ? `: ${r.error}` : ''}</td>
                <td>{r.chunks || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

function Dashboard() {
  const [period, setPeriod] = useState('7');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('ingest');

  const fetchSummary = async () => {
    setLoading(true); setError(null);
    const { date_from, date_to } = getDateRange(period);
    const params = new URLSearchParams();
    if (date_from) params.set('date_from', date_from);
    if (date_to) params.set('date_to', date_to);
    try {
      const res = await fetch(`${getApiBase()}/api/metrics/summary?${params}`, { credentials: 'include' });
      const ct = res.headers.get('content-type') || '';
      if (!ct.includes('application/json')) {
        const text = await res.text();
        setError(text.trimStart().startsWith('<') ? 'Metrics API returned HTML — is the backend running?' : text.slice(0, 200));
        setData(null); return;
      }
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || 'Failed to load metrics');
      setData(json);
    } catch (e) { setError(e.message || 'Failed to load metrics.'); setData(null); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchSummary(); }, [period]);

  const feedbackTotal = data && (data.feedback_helpful_count || 0) + (data.feedback_not_helpful_count || 0);
  const feedbackHelpfulPct = feedbackTotal > 0 && data ? Math.round((data.feedback_helpful_count / feedbackTotal) * 100) : null;

  const TABS = [
    { id: 'ingest', label: 'Local Ingest', icon: <HiOutlineDatabase /> },
    { id: 'drive', label: 'Drive Monitor', icon: <HiOutlineFolder /> },
  ];

  return (
    <div className="dashboard theme-dark">
      <header className="dashboard__header">
        <Link to="/staff" className="dashboard__back" aria-label="Back to chat">
          <HiOutlineArrowLeft className="dashboard__back-icon" aria-hidden="true" />
          <span>Back to chat</span>
        </Link>
        <h1 className="dashboard__title">
          <HiOutlineChartBar className="dashboard__title-icon" aria-hidden="true" />
          Metrics & usage
        </h1>
        <p className="dashboard__subtitle">
          See how the Knowledge Navigator is performing and track progress toward the 60% time-saved target.
        </p>
      </header>

      {/* ── Knowledge panel with tabs ── */}
      <div className="dp-panel">
        <div className="dp-tabs" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={activeTab === t.id}
              className={`dp-tab ${activeTab === t.id ? 'dp-tab--active' : ''}`}
              onClick={() => setActiveTab(t.id)}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>
        {activeTab === 'ingest' && <LocalIngestTab />}
        {activeTab === 'drive'  && <DriveMonitorTab />}
      </div>

      {/* ── Metrics ── */}
      <div className="dashboard__period">
        <span className="dashboard__period-label">Period:</span>
        <div className="dashboard__period-btns" role="group" aria-label="Select time period">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              type="button"
              className={`dashboard__period-btn ${period === p.value ? 'dashboard__period-btn--active' : ''}`}
              onClick={() => setPeriod(p.value)}
              aria-pressed={period === p.value}
            >
              {p.label}
            </button>
          ))}
        </div>
        <button type="button" className="dashboard__refresh" onClick={fetchSummary} disabled={loading} aria-label="Refresh metrics">
          <HiOutlineRefresh className="dashboard__refresh-icon" aria-hidden="true" />
          Refresh
        </button>
      </div>

      {error && <div className="dashboard__error" role="alert">{error}</div>}
      {loading && !data && <div className="dashboard__loading" aria-live="polite">Loading metrics…</div>}

      {data && !loading && (
        <>
          <div className="dashboard__cards">
            <div className="dashboard__card">
              <div className="dashboard__card-icon-wrap">
                <HiOutlineChartBar className="dashboard__card-icon" aria-hidden="true" />
              </div>
              <div className="dashboard__card-body">
                <span className="dashboard__card-value">{data.query_count ?? 0}</span>
                <span className="dashboard__card-label">Queries in period</span>
                {period !== 'all' && <span className="dashboard__card-meta">~{period === '7' ? 'per week' : 'per month'}: {data.query_count ?? 0}</span>}
              </div>
            </div>
            <div className="dashboard__card">
              <div className="dashboard__card-icon-wrap">
                <HiOutlineClock className="dashboard__card-icon" aria-hidden="true" />
              </div>
              <div className="dashboard__card-body">
                <span className="dashboard__card-value">{formatLatency(data.avg_latency_seconds)}</span>
                <span className="dashboard__card-label">Avg time to answer</span>
                {(data.p50_latency_seconds != null || data.p95_latency_seconds != null) && (
                  <span className="dashboard__card-meta">P50: {formatLatency(data.p50_latency_seconds)} · P95: {formatLatency(data.p95_latency_seconds)}</span>
                )}
              </div>
            </div>
            <div className="dashboard__card">
              <div className="dashboard__card-icon-wrap">
                <HiOutlineThumbUp className="dashboard__card-icon dashboard__card-icon--up" aria-hidden="true" />
                <HiOutlineThumbDown className="dashboard__card-icon dashboard__card-icon--down" aria-hidden="true" />
              </div>
              <div className="dashboard__card-body">
                <span className="dashboard__card-value">{feedbackHelpfulPct != null ? `${feedbackHelpfulPct}%` : '—'}</span>
                <span className="dashboard__card-label">Found it helpful</span>
                <span className="dashboard__card-meta">{data.feedback_helpful_count ?? 0} yes · {data.feedback_not_helpful_count ?? 0} no</span>
              </div>
            </div>
          </div>

          <section className="dashboard__target" aria-labelledby="target-heading">
            <h2 id="target-heading" className="dashboard__target-title">60% time-saved target</h2>
            <p className="dashboard__target-desc">
              Use the baseline (e.g. hours/week spent searching before this tool) to compare. Average time to answer above shows how quickly users get results now.
            </p>
            <div className="dashboard__target-bar-wrap">
              <div className="dashboard__target-bar-fill" style={{ width: feedbackHelpfulPct != null ? `${Math.min(100, feedbackHelpfulPct)}%` : '0%' }} aria-hidden="true" />
              <span className="dashboard__target-bar-label">
                {feedbackHelpfulPct != null ? `${feedbackHelpfulPct}% of feedback positive` : 'No feedback yet — use "Was this helpful?" in chat'}
              </span>
            </div>
          </section>

          {data.message && <p className="dashboard__stub-note" role="status">{data.message}</p>}
        </>
      )}
    </div>
  );
}

export default Dashboard;
