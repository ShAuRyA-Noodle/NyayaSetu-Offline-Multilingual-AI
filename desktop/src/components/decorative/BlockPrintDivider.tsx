import React from 'react';

interface BlockPrintDividerProps {
  className?: string;
  color?: string;
}

// Repeating block-print floral motif divider — Indian textile pattern
const BlockPrintDivider: React.FC<BlockPrintDividerProps> = ({
  className = '',
  color = '#C27B3A',
}) => (
  <div className={`w-full overflow-hidden ${className}`}>
    <svg
      width="100%"
      height="24"
      viewBox="0 0 400 24"
      preserveAspectRatio="xMidYMid slice"
      xmlns="http://www.w3.org/2000/svg"
      className="opacity-20 dark:opacity-10"
    >
      <defs>
        <pattern id="blockprint" x="0" y="0" width="48" height="24" patternUnits="userSpaceOnUse">
          {/* Central diamond */}
          <polygon points="24,2 34,12 24,22 14,12" fill="none" stroke={color} strokeWidth="0.8" />
          {/* Inner diamond */}
          <polygon points="24,6 30,12 24,18 18,12" fill="none" stroke={color} strokeWidth="0.5" />
          {/* Dot center */}
          <circle cx="24" cy="12" r="1.5" fill={color} opacity="0.5" />
          {/* Corner petals */}
          <circle cx="0" cy="0" r="4" fill="none" stroke={color} strokeWidth="0.5" />
          <circle cx="48" cy="0" r="4" fill="none" stroke={color} strokeWidth="0.5" />
          <circle cx="0" cy="24" r="4" fill="none" stroke={color} strokeWidth="0.5" />
          <circle cx="48" cy="24" r="4" fill="none" stroke={color} strokeWidth="0.5" />
          {/* Connecting lines */}
          <line x1="4" y1="0" x2="14" y2="12" stroke={color} strokeWidth="0.3" />
          <line x1="34" y1="12" x2="44" y2="0" stroke={color} strokeWidth="0.3" />
          <line x1="4" y1="24" x2="14" y2="12" stroke={color} strokeWidth="0.3" />
          <line x1="34" y1="12" x2="44" y2="24" stroke={color} strokeWidth="0.3" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#blockprint)" />
    </svg>
  </div>
);

export default BlockPrintDivider;
