import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { HiOutlineMenuAlt3, HiOutlineLogin, HiOutlineLogout, HiOutlineChartBar, HiOutlineGlobe, HiOutlineFolder, HiOutlineSun, HiOutlineMoon, HiOutlineExternalLink } from 'react-icons/hi';
import { getApiBase, useAuth } from '../context/AuthContext';

function AppHeader({ onMenuClick, sidebarOpen, showMenuAsLinkToHome = false, isDarkTheme = true, onToggleTheme }) {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const isPublicPortal = pathname === '/';
  const { user, loading, loginUrl, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    setDropdownOpen(false);
    await fetch(`${getApiBase()}/api/auth/logout`, { method: 'POST', credentials: 'include' });
    logout();
    navigate('/', { replace: true });
  };

  return (
    <header className="app-header">
      {isPublicPortal ? (
        <div className="app-header__menu app-header__menu--spacer" aria-hidden="true" />
      ) : showMenuAsLinkToHome ? (
        <Link
          to="/"
          className="app-header__menu app-header__menu--link"
          aria-label="Back to public portal"
        >
          <HiOutlineMenuAlt3 className="app-header__menu-icon" aria-hidden="true" />
        </Link>
      ) : (
        <button
          type="button"
          className="app-header__menu"
          onClick={onMenuClick}
          aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
          aria-expanded={sidebarOpen}
        >
          <HiOutlineMenuAlt3 className="app-header__menu-icon" aria-hidden="true" />
        </button>
      )}
      <h1 className="app-header__title">
        <span className="app-header__title-suffix">Knowledge Navigator</span>
      </h1>
      <div className="app-header__actions">
        {isPublicPortal ? (
          <Link to="/staff" className="app-header__dashboard" aria-label="Staff Portal">
            <HiOutlineExternalLink className="app-header__dashboard-icon" aria-hidden="true" />
            <span>Staff Portal</span>
          </Link>
        ) : (
          <Link to="/" className="app-header__dashboard" aria-label="Public Portal">
            <HiOutlineGlobe className="app-header__dashboard-icon" aria-hidden="true" />
            <span>Public Portal</span>
          </Link>
        )}
        {!loading && (
          user ? (
            <div className="app-header__user-wrap" ref={dropdownRef}>
              <button
                type="button"
                className="app-header__user-trigger"
                onClick={() => setDropdownOpen((o) => !o)}
                aria-expanded={dropdownOpen}
                aria-haspopup="true"
                aria-label="Account menu"
              >
                {user.picture && (
                  <img
                    src={user.picture}
                    alt=""
                    className="app-header__avatar"
                    width={28}
                    height={28}
                  />
                )}
                <span className="app-header__name">{user.name || user.email || 'Signed in'}</span>
              </button>
              {dropdownOpen && (
                <div className="app-header__dropdown" role="menu">
                  <Link
                    to="/drive-monitor"
                    className="app-header__dropdown-item"
                    role="menuitem"
                    onClick={() => setDropdownOpen(false)}
                  >
                    <HiOutlineFolder className="app-header__dropdown-icon" aria-hidden="true" />
                    <span>Manage Drive</span>
                  </Link>
                  <Link
                    to="/dashboard"
                    className="app-header__dropdown-item"
                    role="menuitem"
                    onClick={() => setDropdownOpen(false)}
                  >
                    <HiOutlineChartBar className="app-header__dropdown-icon" aria-hidden="true" />
                    <span>Dashboard</span>
                  </Link>
                  {onToggleTheme && (
                    <button
                      type="button"
                      className="app-header__dropdown-item"
                      role="menuitem"
                      onClick={() => {
                        onToggleTheme();
                        setDropdownOpen(false);
                      }}
                      aria-label={isDarkTheme ? 'Switch to light mode' : 'Switch to dark mode'}
                    >
                      {isDarkTheme ? (
                        <HiOutlineSun className="app-header__dropdown-icon" aria-hidden="true" />
                      ) : (
                        <HiOutlineMoon className="app-header__dropdown-icon" aria-hidden="true" />
                      )}
                      <span>{isDarkTheme ? 'Light mode' : 'Dark mode'}</span>
                    </button>
                  )}
                  <button
                    type="button"
                    className="app-header__dropdown-item app-header__dropdown-item--danger"
                    role="menuitem"
                    onClick={handleLogout}
                  >
                    <HiOutlineLogout className="app-header__dropdown-icon" aria-hidden="true" />
                    <span>Sign Out</span>
                  </button>
                </div>
              )}
            </div>
          ) : (
            <a href={loginUrl} className="app-header__login" aria-label="Sign in with Google">
              <HiOutlineLogin className="app-header__login-icon" aria-hidden="true" />
              <span>Login</span>
            </a>
          )
        )}
      </div>
    </header>
  );
}

export default AppHeader;
