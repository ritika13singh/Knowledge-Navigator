import React, { useState, useEffect } from 'react';
import { HiOutlineFilter, HiOutlineX, HiOutlineTag, HiOutlineDocumentText, HiOutlineCalendar } from 'react-icons/hi';

const THEME_LABELS = {
  skills_employment: 'Skills & Employment',
  social_enterprise: 'Social Enterprise',
  impact_investment: 'Impact Investment',
  case_study: 'Case Study',
  regional_report: 'Regional Report',
  annual_report: 'Annual Report',
  policy_governance: 'Policy & Governance',
  shared_value: 'Shared Value',
  innovation_research: 'Innovation & Research',
  general: 'General',
};

const DOC_TYPE_LABELS = {
  report: 'Report',
  manual: 'Manual',
  case_study: 'Case Study',
  policy: 'Policy',
  training: 'Training',
  learning: 'Learning',
  presentation: 'Presentation',
  template: 'Template',
  other: 'Other',
};

function ThemeFilter({ filters, onFiltersChange, onClose }) {
  const [themes, setThemes] = useState([]);
  const [documentTypes, setDocumentTypes] = useState([]);
  const [themeSummary, setThemeSummary] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const themeKeys = Object.keys(THEME_LABELS);
    const docTypeKeys = Object.keys(DOC_TYPE_LABELS);

    const fetchData = async () => {
      try {
        const [themesRes, typesRes] = await Promise.all([
          fetch('/api/themes').catch(() => ({ ok: false })),
          fetch('/api/document-types').catch(() => ({ ok: false })),
        ]);
        if (themesRes.ok) {
          const data = await themesRes.json();
          const list = data.valid_themes || [];
          setThemes(list.length > 0 ? list : themeKeys);
          setThemeSummary(data.summary || []);
        } else {
          setThemes(themeKeys);
        }
        if (typesRes.ok) {
          const data = await typesRes.json();
          const list = data.valid_types || [];
          setDocumentTypes(list.length > 0 ? list : docTypeKeys);
        } else {
          setDocumentTypes(docTypeKeys);
        }
      } catch (err) {
        console.error('Failed to fetch filter options:', err);
        setThemes(themeKeys);
        setDocumentTypes(docTypeKeys);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleThemeToggle = (theme) => {
    const currentThemes = filters.themes || [];
    const newThemes = currentThemes.includes(theme)
      ? currentThemes.filter((t) => t !== theme)
      : [...currentThemes, theme];
    onFiltersChange({ ...filters, themes: newThemes });
  };

  const handleDocTypeChange = (e) => {
    onFiltersChange({ ...filters, documentType: e.target.value || null });
  };

  const handleDateChange = (field, value) => {
    onFiltersChange({ ...filters, [field]: value || null });
  };

  const handleInternalOnlyToggle = () => {
    onFiltersChange({ ...filters, internalOnly: !filters.internalOnly });
  };

  const clearFilters = () => {
    onFiltersChange({
      themes: [],
      documentType: null,
      dateFrom: null,
      dateTo: null,
      internalOnly: false,
    });
  };

  const activeFilterCount =
    (filters.themes?.length || 0) +
    (filters.documentType ? 1 : 0) +
    (filters.dateFrom ? 1 : 0) +
    (filters.dateTo ? 1 : 0) +
    (filters.internalOnly ? 1 : 0);

  const getThemeCount = (theme) => {
    const item = themeSummary.find((s) => s.theme === theme);
    return item ? item.count : 0;
  };

  if (loading) {
    return (
      <div className="theme-filter theme-filter--loading">
        <div className="theme-filter__header">
          <HiOutlineFilter className="theme-filter__icon" />
          <span>Loading filters...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="theme-filter">
      <div className="theme-filter__header">
        <div className="theme-filter__title">
          <HiOutlineFilter className="theme-filter__icon" />
          <span>Filter by Theme</span>
          {activeFilterCount > 0 && (
            <span className="theme-filter__badge">{activeFilterCount}</span>
          )}
        </div>
        <div className="theme-filter__actions">
          {activeFilterCount > 0 && (
            <button
              type="button"
              className="theme-filter__clear"
              onClick={clearFilters}
              title="Clear all filters"
            >
              Clear
            </button>
          )}
          {onClose && (
            <button
              type="button"
              className="theme-filter__close"
              onClick={onClose}
              aria-label="Close filters"
            >
              <HiOutlineX />
            </button>
          )}
        </div>
      </div>

      <div className="theme-filter__section">
        <div className="theme-filter__section-title">
          <HiOutlineTag className="theme-filter__section-icon" />
          <span>Themes</span>
        </div>
        <div className="theme-filter__chips">
          {themes.map((theme) => (
            <button
              key={theme}
              type="button"
              className={`theme-filter__chip ${
                filters.themes?.includes(theme) ? 'theme-filter__chip--active' : ''
              }`}
              onClick={() => handleThemeToggle(theme)}
            >
              {THEME_LABELS[theme] || theme}
              {getThemeCount(theme) > 0 && (
                <span className="theme-filter__chip-count">{getThemeCount(theme)}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="theme-filter__section">
        <div className="theme-filter__section-title">
          <HiOutlineDocumentText className="theme-filter__section-icon" />
          <span>Document Type</span>
        </div>
        <select
          className="theme-filter__select"
          value={filters.documentType || ''}
          onChange={handleDocTypeChange}
        >
          <option value="">All types</option>
          {documentTypes.map((type) => (
            <option key={type} value={type}>
              {DOC_TYPE_LABELS[type] || type}
            </option>
          ))}
        </select>
      </div>

      <div className="theme-filter__section">
        <div className="theme-filter__section-title">
          <HiOutlineCalendar className="theme-filter__section-icon" />
          <span>Date Range</span>
        </div>
        <div className="theme-filter__date-range">
          <input
            type="date"
            className="theme-filter__date"
            value={filters.dateFrom || ''}
            onChange={(e) => handleDateChange('dateFrom', e.target.value)}
            placeholder="From"
          />
          <span className="theme-filter__date-sep">to</span>
          <input
            type="date"
            className="theme-filter__date"
            value={filters.dateTo || ''}
            onChange={(e) => handleDateChange('dateTo', e.target.value)}
            placeholder="To"
          />
        </div>
      </div>

      <div className="theme-filter__section">
        <label className="theme-filter__checkbox-label">
          <input
            type="checkbox"
            checked={filters.internalOnly || false}
            onChange={handleInternalOnlyToggle}
          />
          <span>Internal documents only</span>
        </label>
      </div>
    </div>
  );
}

export default ThemeFilter;
