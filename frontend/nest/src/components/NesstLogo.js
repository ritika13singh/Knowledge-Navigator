import React from 'react';

const LOGO_SRC = process.env.PUBLIC_URL + '/nesst-logo.png';

/**
 * NESst logo: uses the provided NESST image (bird + text on black).
 */
function NesstLogo({ size = 'medium', className = '' }) {
  const height = size === 'small' ? 28 : size === 'large' ? 48 : 36;
  return (
    <img
      src={LOGO_SRC}
      alt="NESST"
      className={`nesst-logo nesst-logo--${size} ${className}`.trim()}
      height={height}
      width="auto"
      draggable={false}
    />
  );
}

export default NesstLogo;
