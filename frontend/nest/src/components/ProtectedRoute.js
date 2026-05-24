import React from 'react';
import { useNavigate } from 'react-router-dom';
import { HiOutlineShieldExclamation } from 'react-icons/hi';
import { useAuth } from '../context/AuthContext';

function UnauthorizedDialog({ onClose }) {
  return (
    <div className="unauthorized-overlay" role="dialog" aria-modal="true">
      <div className="unauthorized-dialog">
        <HiOutlineShieldExclamation className="unauthorized-icon" />
        <h2 className="unauthorized-title">You are not authorized to view this page!</h2>
        <p className="unauthorized-message">
          Only admin users can access the Staff Portal. Please contact an administrator if you believe you should have access.
        </p>
        <button type="button" className="unauthorized-btn" onClick={onClose}>
          Go to Public Portal
        </button>
      </div>
    </div>
  );
}

function ProtectedRoute({ children, requireAdmin = false }) {
  const { user, loading, loginUrl } = useAuth();
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="protected-route-loading">
        <div className="protected-route-spinner"></div>
        <p>Checking authentication...</p>
      </div>
    );
  }

  if (!user) {
    // Redirect to Google login
    window.location.href = loginUrl;
    return (
      <div className="protected-route-loading">
        <div className="protected-route-spinner"></div>
        <p>Redirecting to login...</p>
      </div>
    );
  }

  // Check admin access if required
  if (requireAdmin && !user.is_admin) {
    return (
      <UnauthorizedDialog onClose={() => navigate('/')} />
    );
  }

  return children;
}

export default ProtectedRoute;
