import React from 'react';

/**
 * Genturix Logo - Native SVG Vector Icon
 * A shield with eye, key, and building elements
 * Uses the app's blue/teal color palette (based on logo)
 */
const GenturixLogo = ({ className = '', size = 40 }) => {
  return (
    <svg
      viewBox="0 0 100 120"
      width={size}
      height={size * 1.2}
      className={className}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Shield Outline */}
      <path
        d="M50 4 L92 20 L92 55 C92 80 72 100 50 116 C28 100 8 80 8 55 L8 20 Z"
        stroke="url(#tealGradient)"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      
      {/* Inner Shield Accent Line */}
      <path
        d="M50 12 L84 25 L84 54 C84 74 67 91 50 104 C33 91 16 74 16 54 L16 25 Z"
        stroke="#4A90A4"
        strokeWidth="1"
        strokeOpacity="0.3"
        fill="none"
      />
      
      {/* Eye - Outer */}
      <ellipse
        cx="50"
        cy="42"
        rx="22"
        ry="14"
        stroke="#4A90A4"
        strokeWidth="2.5"
        fill="none"
      />
      
      {/* Eye - Iris */}
      <circle
        cx="50"
        cy="42"
        r="10"
        stroke="#80CBDC"
        strokeWidth="2"
        fill="none"
      />
      
      {/* Eye - Pupil */}
      <circle
        cx="50"
        cy="42"
        r="5"
        fill="#4A90A4"
      />
      
      {/* Eye - Highlight */}
      <circle
        cx="53"
        cy="40"
        r="2"
        fill="white"
        fillOpacity="0.9"
      />
      
      {/* Key - Positioned right side */}
      <g transform="translate(62, 32)" stroke="#94A3B8" strokeWidth="1.5" fill="none">
        {/* Key Bow (ring) */}
        <circle cx="6" cy="6" r="5" />
        {/* Key Shank */}
        <line x1="6" y1="11" x2="6" y2="26" />
        {/* Key Bit */}
        <line x1="6" y1="22" x2="10" y2="22" />
        <line x1="6" y1="26" x2="12" y2="26" />
      </g>
      
      {/* Buildings - Left */}
      <g transform="translate(20, 68)">
        {/* Building 1 - Tall left */}
        <rect x="0" y="8" width="12" height="30" stroke="#4A90A4" strokeWidth="2" fill="none" rx="1" />
        {/* Window */}
        <rect x="4" y="14" width="4" height="4" fill="#94A3B8" fillOpacity="0.6" />
        <rect x="4" y="22" width="4" height="4" fill="#94A3B8" fillOpacity="0.6" />
        
        {/* Building 2 - Short */}
        <rect x="14" y="20" width="10" height="18" stroke="#4A90A4" strokeWidth="2" fill="none" rx="1" />
        {/* Window */}
        <rect x="17" y="26" width="4" height="4" fill="#94A3B8" fillOpacity="0.6" />
      </g>
      
      {/* Buildings - Right */}
      <g transform="translate(52, 68)">
        {/* Building 3 - Medium */}
        <rect x="0" y="14" width="12" height="24" stroke="#4A90A4" strokeWidth="2" fill="none" rx="1" />
        {/* Windows */}
        <rect x="3" y="20" width="3" height="3" fill="#94A3B8" fillOpacity="0.6" />
        <rect x="3" y="28" width="3" height="3" fill="#94A3B8" fillOpacity="0.6" />
        
        {/* Building 4 - Tall right */}
        <rect x="14" y="4" width="14" height="34" stroke="#4A90A4" strokeWidth="2" fill="none" rx="1" />
        {/* Windows */}
        <rect x="18" y="10" width="5" height="5" fill="#94A3B8" fillOpacity="0.6" />
        <rect x="18" y="20" width="5" height="5" fill="#94A3B8" fillOpacity="0.6" />
        <rect x="18" y="30" width="5" height="4" fill="#94A3B8" fillOpacity="0.6" />
      </g>
      
      {/* Gradient Definition - Teal/Blue based on logo */}
      <defs>
        <linearGradient id="tealGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#80CBDC" />
          <stop offset="50%" stopColor="#4A90A4" />
          <stop offset="100%" stopColor="#3A7B97" />
        </linearGradient>
      </defs>
    </svg>
  );
};

export default GenturixLogo;
