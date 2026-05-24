import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { useOutletContext } from 'react-router-dom';
import { HiOutlineChat, HiOutlineSparkles, HiOutlineFilter, HiOutlineDownload, HiOutlineAcademicCap } from 'react-icons/hi';
import jsPDF from 'jspdf';
import { getApiBase, useAuth } from '../context/AuthContext';
import SideNav from './SideNav';
import Message from './Message';
import ChatInput from './ChatInput';
import ThemeFilter from './ThemeFilter';
import OnboardingModal from './OnboardingModal';

const generateId = () => `id-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
const TITLE_MAX_LEN = 36;

function Chat() {
  const outletContext = useOutletContext() || {};
  const { sidebarOpen = true, setSidebarOpen = () => {}, isDarkTheme = true } = outletContext;
  const { user } = useAuth();
  const apiBase = getApiBase();

  const [conversations, setConversations] = useState([{ id: generateId(), title: 'New chat', messages: [], createdAt: Date.now() }]);
  const [activeId, setActiveId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [sessionId] = useState(() => generateId());
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    themes: [],
    documentType: null,
    dateFrom: null,
    dateTo: null,
    internalOnly: false,
  });
  const [showOnboarding, setShowOnboarding] = useState(() => {
    // Show onboarding if user hasn't seen it before
    return !localStorage.getItem('kn_onboarding_completed');
  });
  const [pendingQuery, setPendingQuery] = useState(null);
  const messagesEndRef = useRef(null);

  const activeConversation = conversations.find((c) => c.id === activeId) ?? conversations[0];
  const activeMessages = useMemo(
    () => activeConversation?.messages ?? [],
    [activeConversation]
  );
  const effectiveActiveId = activeId ?? conversations[0]?.id;

  useEffect(() => {
    if (conversations.length && activeId === null) {
      setActiveId(conversations[0].id);
    }
  }, [conversations, activeId]);

  // Load chat history from backend when user is authenticated
  useEffect(() => {
    if (!user || historyLoaded) return;
    
    const loadHistory = async () => {
      try {
        const res = await fetch(`${apiBase}/api/chat-history/conversations`, {
          credentials: 'include',
        });
        if (res.ok) {
          const data = await res.json();
          if (data.conversations && data.conversations.length > 0) {
            setConversations(data.conversations);
            setActiveId(data.conversations[0].id);
          }
        }
      } catch (err) {
        console.warn('Failed to load chat history:', err);
      } finally {
        setHistoryLoaded(true);
      }
    };
    
    loadHistory();
  }, [user, historyLoaded, apiBase]);

  // Save conversation to backend when it changes (debounced)
  const saveTimeoutRef = useRef(null);
  useEffect(() => {
    if (!user || !historyLoaded) return;
    
    // Clear previous timeout
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    
    // Debounce save to avoid too many API calls
    saveTimeoutRef.current = setTimeout(() => {
      const conv = conversations.find(c => c.id === activeId);
      if (conv && conv.messages.length > 0) {
        fetch(`${apiBase}/api/chat-history/conversations`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            conversation_id: conv.id,
            title: conv.title,
            messages: conv.messages,
          }),
        }).catch(err => console.warn('Failed to save conversation:', err));
      }
    }, 1000);
    
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [conversations, activeId, user, historyLoaded, apiBase]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [activeMessages, activeId]);

  const handleNewChat = () => {
    const newConv = { id: generateId(), title: 'New chat', messages: [], createdAt: Date.now() };
    setConversations((prev) => [newConv, ...prev]);
    setActiveId(newConv.id);
  };

  const handleSelectChat = (id) => {
    setActiveId(id);
  };

  const handleOnboardingClose = () => {
    setShowOnboarding(false);
    localStorage.setItem('kn_onboarding_completed', 'true');
  };

  const handleOnboardingQuery = (query) => {
    setPendingQuery(query);
    handleOnboardingClose();
  };

  // Process pending query from onboarding
  useEffect(() => {
    if (pendingQuery && !isLoading) {
      handleSend(pendingQuery);
      setPendingQuery(null);
    }
  }, [pendingQuery, isLoading]);

  const handleShowOnboarding = () => {
    setShowOnboarding(true);
  };

  const activeFilterCount =
    (filters.themes?.length || 0) +
    (filters.documentType ? 1 : 0) +
    (filters.dateFrom ? 1 : 0) +
    (filters.dateTo ? 1 : 0) +
    (filters.internalOnly ? 1 : 0);

  const handleSend = async (text) => {
    const conv = activeConversation;
    if (!conv) return;

    const userMessage = { id: generateId(), role: 'user', content: text };
    const isFirstMessage = conv.messages.length === 0;

    const title = isFirstMessage
      ? (text.length > TITLE_MAX_LEN ? `${text.slice(0, TITLE_MAX_LEN)}…` : text)
      : conv.title;
    setConversations((prev) =>
      prev.map((c) =>
        c.id === conv.id
          ? { ...c, messages: [...c.messages, userMessage], title }
          : c
      )
    );
    setIsLoading(true);

    const apiBase = getApiBase();
    try {
      // Send last 10 messages as context so follow-ups ("tell me more", "what about in Brazil?") work
      const priorMessages = (conv.messages || []).slice(-10).map((m) => ({
        role: m.role || 'user',
        content: typeof m.content === 'string' ? m.content : '',
      }));
      const queryBody = {
        question: text,
        session_id: sessionId,
        conversation_history: priorMessages.length > 0 ? priorMessages : undefined,
        themes: filters.themes?.length ? filters.themes : null,
        document_type: filters.documentType || null,
        date_from: filters.dateFrom || null,
        date_to: filters.dateTo || null,
        internal_only: filters.internalOnly || false,
      };
      const response = await fetch(`${apiBase}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(queryBody),
      });
      let assistantContent = 'No response from the service.';
      let sources = [];
      let latencySeconds;
      if (response.ok) {
        try {
          const data = await response.json();
          assistantContent = data?.answer ?? data?.response ?? assistantContent;
          const raw = data?.sources;
          sources = Array.isArray(raw) ? raw : (raw ? [String(raw)] : []);
          const lat = data?.latency_seconds;
          latencySeconds = typeof lat === 'number' && lat >= 0 ? lat : undefined;
        } catch {
          assistantContent = await response.text() || assistantContent;
        }
      }
      const assistantMessage = {
        id: generateId(),
        role: 'assistant',
        content: assistantContent,
        sources: sources.length ? sources : undefined,
        latencySeconds,
      };
      setConversations((prev) =>
        prev.map((c) =>
          c.id === conv.id ? { ...c, messages: [...c.messages, assistantMessage] } : c
        )
      );
    } catch (err) {
      const fallback = `Sorry, something went wrong: ${err.message}. You can try again.`;
      setConversations((prev) =>
        prev.map((c) =>
          c.id === conv.id
            ? { ...c, messages: [...c.messages, { id: generateId(), role: 'assistant', content: fallback }] }
            : c
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  const chatHistory = conversations.map((c) => ({ id: c.id, title: c.title }));

  const handleExportPDF = useCallback(() => {
    if (activeMessages.length === 0) return;
    
    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.getWidth();
    const margin = 20;
    const maxWidth = pageWidth - margin * 2;
    let yPos = 20;
    
    // Title
    doc.setFontSize(18);
    doc.setFont('helvetica', 'bold');
    doc.text('Knowledge Navigator', margin, yPos);
    yPos += 10;
    
    // Conversation title
    doc.setFontSize(12);
    doc.setFont('helvetica', 'normal');
    doc.text(`Conversation: ${activeConversation?.title || 'Chat'}`, margin, yPos);
    yPos += 5;
    
    // Date
    doc.setFontSize(10);
    doc.setTextColor(100);
    doc.text(`Exported: ${new Date().toLocaleString()}`, margin, yPos);
    yPos += 15;
    
    doc.setTextColor(0);
    
    // Messages
    activeMessages.forEach((msg) => {
      // Check if we need a new page
      if (yPos > 270) {
        doc.addPage();
        yPos = 20;
      }
      
      // Role label
      doc.setFontSize(10);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(msg.role === 'user' ? 0 : 34, msg.role === 'user' ? 102 : 139, msg.role === 'user' ? 204 : 34);
      doc.text(msg.role === 'user' ? 'You:' : 'Knowledge Navigator Assistant:', margin, yPos);
      yPos += 6;
      
      // Message content
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(0);
      doc.setFontSize(11);
      const content = typeof msg.content === 'string' ? msg.content : '';
      const lines = doc.splitTextToSize(content, maxWidth);
      
      lines.forEach((line) => {
        if (yPos > 280) {
          doc.addPage();
          yPos = 20;
        }
        doc.text(line, margin, yPos);
        yPos += 5;
      });
      
      // Sources
      if (msg.sources && msg.sources.length > 0) {
        yPos += 3;
        doc.setFontSize(9);
        doc.setTextColor(100);
        const sourceNames = msg.sources.map(s => 
          typeof s === 'string' ? s : (s?.title || s?.file_name || 'Unknown')
        ).join(', ');
        const sourceLines = doc.splitTextToSize(`Sources: ${sourceNames}`, maxWidth);
        sourceLines.forEach((line) => {
          if (yPos > 280) {
            doc.addPage();
            yPos = 20;
          }
          doc.text(line, margin, yPos);
          yPos += 4;
        });
        doc.setTextColor(0);
      }
      
      yPos += 8;
    });
    
    // Save the PDF
    const fileName = `kn-chat-${activeConversation?.title?.replace(/[^a-z0-9]/gi, '-') || 'export'}-${Date.now()}.pdf`;
    doc.save(fileName);
  }, [activeMessages, activeConversation]);

  return (
    <div className={`chat-layout theme-${isDarkTheme ? 'dark' : 'light'}`}>
      <div className="chat-layout__body">
        <SideNav
          chats={chatHistory}
          activeChatId={effectiveActiveId}
          onNewChat={handleNewChat}
          onSelectChat={handleSelectChat}
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />
        <div className="chat">
          {showFilters && (
            <div className="chat__filters-panel">
              <ThemeFilter
                filters={filters}
                onFiltersChange={setFilters}
                onClose={() => setShowFilters(false)}
              />
            </div>
          )}
          <main className="chat__main">
            <div className="chat__toolbar">
              <button
                type="button"
                className={`chat__filter-btn ${activeFilterCount > 0 ? 'chat__filter-btn--active' : ''}`}
                onClick={() => setShowFilters((s) => !s)}
                aria-label="Toggle filters"
                title="Filter by theme"
              >
                <HiOutlineFilter />
                {activeFilterCount > 0 && (
                  <span className="chat__filter-badge">{activeFilterCount}</span>
                )}
              </button>
              <button
                type="button"
                className="chat__export-btn"
                onClick={handleExportPDF}
                disabled={activeMessages.length === 0}
                aria-label="Export conversation to PDF"
                title="Export to PDF"
              >
                <HiOutlineDownload />
                <span>Export PDF</span>
              </button>
              <button
                type="button"
                className="chat__onboarding-btn"
                onClick={handleShowOnboarding}
                aria-label="Show getting started guide"
                title="Getting Started Guide"
              >
                <HiOutlineAcademicCap />
                <span>Getting Started</span>
              </button>
            </div>
            <div className="chat__messages">
              {activeMessages.length === 0 && (
                <div className="chat__welcome" role="status">
                  <HiOutlineChat className="chat__welcome-icon" aria-hidden="true" />
                  <p>Send a message to get started.</p>
                  {activeFilterCount > 0 && (
                    <p className="chat__welcome-filters">
                      Filtering by {activeFilterCount} criteria
                    </p>
                  )}
                </div>
              )}
              {activeMessages.map((msg) => (
                <Message
                  key={msg.id}
                  id={msg.id}
                  role={msg.role}
                  content={msg.content}
                  sources={msg.sources}
                  latencySeconds={msg.latencySeconds}
                  sessionId={sessionId}
                />
              ))}
              {isLoading && (
                <div className="message message--assistant">
                  <span className="message__assistant-icon" aria-hidden="true">
                    <HiOutlineSparkles />
                  </span>
                  <div className="message__bubble">
                    <div className="message__typing" aria-live="polite">
                      <span className="message__dot" />
                      <span className="message__dot" />
                      <span className="message__dot" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} className="chat__scroll-anchor" aria-hidden="true" />
            </div>
            <ChatInput
              onSend={handleSend}
              disabled={isLoading}
              placeholder="Message Knowledge Navigator..."
            />
          </main>
        </div>
      </div>
      {showOnboarding && (
        <OnboardingModal
          onClose={handleOnboardingClose}
          onSelectQuery={handleOnboardingQuery}
          onSkip={handleOnboardingClose}
        />
      )}
    </div>
  );
}

export default Chat;
