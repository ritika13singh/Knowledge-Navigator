import React, { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import AppHeader from './AppHeader';

function AppLayout() {
  const { pathname } = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isDarkTheme, setIsDarkTheme] = useState(true);

  const isChat = pathname === '/staff';

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDarkTheme ? 'dark' : 'light');
  }, [isDarkTheme]);

  return (
    <div className="app-layout">
      <AppHeader
        onMenuClick={isChat ? () => setSidebarOpen((o) => !o) : undefined}
        sidebarOpen={sidebarOpen}
        showMenuAsLinkToHome={!isChat}
        isDarkTheme={isDarkTheme}
        onToggleTheme={() => setIsDarkTheme((d) => !d)}
      />
      <main className="app-layout__main">
        <Outlet context={{ sidebarOpen, setSidebarOpen, isDarkTheme }} />
      </main>
    </div>
  );
}

export default AppLayout;
