import React, { useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user, loading, loginUrl, refetchUser } = useAuth();
  const error = searchParams.get('error');

  useEffect(() => {
    if (user) navigate('/', { replace: true });
  }, [user, navigate]);

  useEffect(() => {
    refetchUser();
  }, [refetchUser]);

  if (loading) {
    return (
      <div className="login-page">
        <div className="login-page__card">
          <p className="login-page__subtitle">Checking session…</p>
        </div>
      </div>
    );
  }

  const errorMessages = {
    oauth_not_configured: 'Google sign-in is not configured. Contact support.',
    missing_code: 'Login was cancelled or failed.',
    invalid_state: 'Invalid session. Please try again.',
    server_config: 'Server configuration error. Try again later.',
    token_exchange: 'Could not complete sign-in. Try again.',
    no_access_token: 'Google did not return an access token. Try again.',
    userinfo: 'Could not load your profile. Try again.',
    no_user_id: 'Could not identify your account. Try again.',
    callback_error: 'Sign-in failed. Ensure the backend is running and redirect URI in Google Console matches http://localhost:8000/api/auth/callback.',
  };

  return (
    <div className="login-page">
      <div className="login-page__card">
        <h1 className="login-page__title">Sign in</h1>
        <p className="login-page__subtitle">
          Sign in with Google to use NESst with your account. You can still use the chat without signing in.
        </p>
        {error && (
          <p className="login-page__error" role="alert">
            {errorMessages[error] || 'Something went wrong. Please try again.'}
          </p>
        )}
        <div className="login-page__actions">
          <a
            href={loginUrl}
            className="login-page__google-btn"
            aria-label="Sign in with Google"
          >
            <svg className="login-page__google-icon" viewBox="0 0 24 24" aria-hidden="true">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Sign in with Google
          </a>
        </div>
        <p className="login-page__footer">
          <Link to="/" className="login-page__link">Back to chat</Link>
        </p>
      </div>
    </div>
  );
}

export default LoginPage;
