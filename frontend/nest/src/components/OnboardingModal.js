import React, { useState } from 'react';
import { HiOutlineAcademicCap, HiOutlineBriefcase, HiOutlineUserGroup, HiOutlineLightBulb, HiOutlineX, HiOutlineUserAdd } from 'react-icons/hi';
import { getApiBase, useAuth } from '../context/AuthContext';

const ROLES = [
  {
    id: 'new_staff',
    title: 'New Staff Member',
    description: 'Just joined NESsT and learning the ropes',
    icon: HiOutlineAcademicCap,
    starterQueries: [
      "What is NESsT?",
      "Tell me about NESsT's programs",
      "What does NESsT do?",
      "Summarize NESsT's work",
      "What documents are available?",
    ],
  },
  {
    id: 'investment_team',
    title: 'Investment Team',
    description: 'Working on portfolio and investment decisions',
    icon: HiOutlineBriefcase,
    starterQueries: [
      "Tell me about investments",
      "What is the investment process?",
      "How are enterprises selected?",
      "What are the investment criteria?",
      "Summarize portfolio information",
    ],
  },
  {
    id: 'program_support',
    title: 'Program & Enterprise Support',
    description: 'Supporting social enterprises with business development',
    icon: HiOutlineUserGroup,
    starterQueries: [
      "How does NESsT support enterprises?",
      "What services are provided to enterprises?",
      "Tell me about business development support",
      "What training is available?",
      "How do enterprises grow with NESsT?",
    ],
  },
  {
    id: 'donor_relations',
    title: 'Donor Relations & Reporting',
    description: 'Managing donor relationships and impact reporting',
    icon: HiOutlineLightBulb,
    starterQueries: [
      "How is impact measured?",
      "What are the key metrics?",
      "Tell me about reporting",
      "What is NESsT's social impact?",
      "Summarize impact data",
    ],
  },
];

function OnboardingModal({ onClose, onSelectQuery, onSkip }) {
  const { user } = useAuth();
  const [selectedRole, setSelectedRole] = useState(null);
  const [step, setStep] = useState('role'); // 'role', 'queries', or 'add_admin'
  const [adminEmail, setAdminEmail] = useState('');
  const [adminError, setAdminError] = useState('');
  const [adminSuccess, setAdminSuccess] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

  const handleRoleSelect = (role) => {
    setSelectedRole(role);
    setStep('queries');
  };

  const handleQueryClick = (query) => {
    onSelectQuery(query);
    onClose();
  };

  const handleBack = () => {
    setStep('role');
    setSelectedRole(null);
    setAdminEmail('');
    setAdminError('');
    setAdminSuccess('');
  };

  const handleAddAdminClick = () => {
    setStep('add_admin');
  };

  const validateEmail = (email) => {
    if (!email.trim()) {
      return 'Email is required';
    }
    if (!emailRegex.test(email.trim())) {
      return 'Please enter a valid email address';
    }
    return '';
  };

  const handleAddAdmin = async () => {
    const error = validateEmail(adminEmail);
    if (error) {
      setAdminError(error);
      return;
    }

    setIsSubmitting(true);
    setAdminError('');
    setAdminSuccess('');

    try {
      const apiBase = getApiBase();
      const res = await fetch(`${apiBase}/api/admin/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: adminEmail.trim().toLowerCase() }),
      });

      if (res.ok) {
        setAdminSuccess(`Successfully added ${adminEmail.trim()} as admin`);
        setAdminEmail('');
      } else {
        const data = await res.json().catch(() => ({}));
        setAdminError(data.detail || 'Failed to add admin user');
      }
    } catch (err) {
      setAdminError('Network error. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="onboarding-overlay" role="dialog" aria-modal="true" aria-labelledby="onboarding-title">
      <div className="onboarding-modal">
        <button
          type="button"
          className="onboarding-close"
          onClick={onSkip}
          aria-label="Close onboarding"
        >
          <HiOutlineX />
        </button>

        {step === 'role' ? (
          <>
            <div className="onboarding-header">
              <h2 id="onboarding-title" className="onboarding-title">
                Welcome to NESsT Knowledge Navigator
              </h2>
              <p className="onboarding-subtitle">
                Select your role to get personalized starter queries and discover relevant institutional knowledge faster.
              </p>
            </div>

            <div className="onboarding-roles">
              {ROLES.map((role) => {
                const IconComponent = role.icon;
                return (
                  <button
                    key={role.id}
                    type="button"
                    className="onboarding-role-card"
                    onClick={() => handleRoleSelect(role)}
                  >
                    <IconComponent className="onboarding-role-icon" />
                    <div className="onboarding-role-content">
                      <h3 className="onboarding-role-title">{role.title}</h3>
                      <p className="onboarding-role-desc">{role.description}</p>
                    </div>
                  </button>
                );
              })}
            </div>

            {user?.is_admin && (
              <div className="onboarding-admin-section">
                <button
                  type="button"
                  className="onboarding-admin-btn"
                  onClick={handleAddAdminClick}
                >
                  <HiOutlineUserAdd className="onboarding-admin-icon" />
                  <span>Add New Admin User</span>
                </button>
              </div>
            )}

            <div className="onboarding-footer">
              <button type="button" className="onboarding-skip" onClick={onSkip}>
                Skip for now
              </button>
            </div>
          </>
        ) : step === 'queries' ? (
          <>
            <div className="onboarding-header">
              <button type="button" className="onboarding-back" onClick={handleBack}>
                ← Back to roles
              </button>
              <h2 className="onboarding-title">
                Getting Started as {selectedRole?.title}
              </h2>
              <p className="onboarding-subtitle">
                Click any question below to start exploring NESsT's institutional knowledge:
              </p>
            </div>

            <div className="onboarding-queries">
              {selectedRole?.starterQueries.map((query, index) => (
                <button
                  key={index}
                  type="button"
                  className="onboarding-query-card"
                  onClick={() => handleQueryClick(query)}
                >
                  <span className="onboarding-query-number">{index + 1}</span>
                  <span className="onboarding-query-text">{query}</span>
                </button>
              ))}
            </div>

            <div className="onboarding-footer">
              <button type="button" className="onboarding-skip" onClick={onSkip}>
                I'll explore on my own
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="onboarding-header">
              <button type="button" className="onboarding-back" onClick={handleBack}>
                ← Back to roles
              </button>
              <h2 className="onboarding-title">
                Add New Admin User
              </h2>
              <p className="onboarding-subtitle">
                Enter the email address of the user you want to grant admin access to NESsT Staff Portal.
              </p>
            </div>

            <div className="onboarding-admin-form">
              <div className="onboarding-input-group">
                <label htmlFor="admin-email" className="onboarding-label">Email Address</label>
                <input
                  id="admin-email"
                  type="email"
                  className={`onboarding-input ${adminError ? 'onboarding-input--error' : ''}`}
                  placeholder="user@example.com"
                  value={adminEmail}
                  onChange={(e) => {
                    setAdminEmail(e.target.value);
                    setAdminError('');
                    setAdminSuccess('');
                  }}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddAdmin()}
                  disabled={isSubmitting}
                />
                {adminError && <p className="onboarding-error">{adminError}</p>}
                {adminSuccess && <p className="onboarding-success">{adminSuccess}</p>}
              </div>

              <div className="onboarding-admin-actions">
                <button
                  type="button"
                  className="onboarding-btn onboarding-btn--secondary"
                  onClick={handleBack}
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="onboarding-btn onboarding-btn--primary"
                  onClick={handleAddAdmin}
                  disabled={isSubmitting || !adminEmail.trim()}
                >
                  {isSubmitting ? 'Adding...' : 'Add Admin'}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default OnboardingModal;
