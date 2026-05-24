import React from 'react';

const LOGO_SRC = process.env.PUBLIC_URL + '/kn-logo.png';

/**
 * Knowledge Navigator logo: uses the provided KN image (bird + text on black).
 */
function AppLogo({ size = 'medium', className = '' }) {
  const height = size === 'small' ? 28 : size === 'large' ? 48 : 36;
  return (
    <img
      src={LOGO_SRC}
      alt="KN"
      className={`kn-logo kn-logo--${size} ${className}`.trim()}
      height={height}
      width="auto"
      draggable={false}
    />
  );
}

export default AppLogo;
