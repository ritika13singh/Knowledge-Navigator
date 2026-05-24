import React, { useState } from 'react';
import { HiOutlineSparkles, HiOutlineDocumentDuplicate, HiOutlineCheck, HiOutlineThumbUp, HiOutlineThumbDown } from 'react-icons/hi';
function Message({ id, role, content, sources, latencySeconds, sessionId }) {
  const isUser = role === 'user';
  const [copied, setCopied] = useState(false);
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [feedbackSending, setFeedbackSending] = useState(false);
  const hasSources = !isUser && Array.isArray(sources) && sources.length > 0;
  const showLatency = !isUser && typeof latencySeconds === 'number' && latencySeconds >= 0;

  const sendFeedback = async (helpful) => {
    if (feedbackSent || feedbackSending) return;
    setFeedbackSending(true);
    try {
      const res = await fetch('/api/metrics/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ helpful, session_id: sessionId || undefined }),
      });
      setFeedbackSent(true);
      if (!res.ok) {
        const err = await res.text().catch(() => '');
        console.warn('Feedback request failed:', res.status, err);
      }
    } catch (e) {
      setFeedbackSent(true);
      console.warn('Feedback request error:', e);
    } finally {
      setFeedbackSending(false);
    }
  };

  const handleCopy = async () => {
    const text = typeof content === 'string' ? content : String(content || '');
    if (!text.trim()) return;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        textarea.style.top = '0';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div
      className={`message message--${isUser ? 'user' : 'assistant'}`}
      data-message-id={id}
      role="article"
      aria-label={isUser ? 'Your message' : 'Assistant response'}
    >
      {!isUser && (
        <span className="message__assistant-icon" aria-hidden="true">
          <HiOutlineSparkles />
        </span>
      )}
      <div className="message__bubble">
        <div className="message__content">
          {typeof content === 'string' ? content : (content || '')}
        </div>
        {hasSources && (
          <div className="message__sources" aria-label="Source documents">
            {sources.map((source, i) => {
              const displayName = typeof source === 'string' 
                ? source 
                : (source?.title || source?.file_name || 'Unknown');
              return (
                <span key={i} className="message__source-pill">
                  {displayName}
                </span>
              );
            })}
          </div>
        )}
        {!isUser && (
          <div className="message__footer">
            {showLatency && (
              <span className="message__latency" aria-label={`Response time: ${latencySeconds.toFixed(1)} seconds`}>
                {latencySeconds < 1
                  ? `Responded in ${(latencySeconds * 1000).toFixed(0)} ms`
                  : `Responded in ${latencySeconds.toFixed(1)}s`}
              </span>
            )}
            <div className="message__actions">
            <button
              type="button"
              className="message__copy"
              onClick={handleCopy}
              aria-label={copied ? 'Copied' : 'Copy response'}
            >
              {copied ? (
                <HiOutlineCheck className="message__copy-icon" aria-hidden="true" />
              ) : (
                <HiOutlineDocumentDuplicate className="message__copy-icon" aria-hidden="true" />
              )}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
          </div>
        )}
        {!isUser && (
          <div className="message__feedback">
            {feedbackSent ? (
              <span className="message__feedback-thanks">Thanks for your feedback</span>
            ) : (
              <>
                <span className="message__feedback-label">Was this helpful?</span>
                <button
                  type="button"
                  className="message__feedback-btn"
                  onClick={() => sendFeedback(true)}
                  disabled={feedbackSending}
                  aria-label="Yes, helpful"
                >
                  <HiOutlineThumbUp className="message__feedback-icon" aria-hidden="true" />
                  <span>Yes</span>
                </button>
                <button
                  type="button"
                  className="message__feedback-btn"
                  onClick={() => sendFeedback(false)}
                  disabled={feedbackSending}
                  aria-label="No, not helpful"
                >
                  <HiOutlineThumbDown className="message__feedback-icon" aria-hidden="true" />
                  <span>No</span>
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default Message;
