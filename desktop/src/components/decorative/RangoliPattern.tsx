import React from 'react';

interface RangoliPatternProps {
  className?: string;
  opacity?: number;
}

// Kolam dot-and-line pattern — South Indian village floor art
const RangoliPattern: React.FC<RangoliPatternProps> = ({ className = '', opacity = 0.03 }) => (
  <svg
    className={`pointer-events-none ${className}`}
    width="100%"
    height="100%"
    xmlns="http://www.w3.org/2000/svg"
    style={{ opacity }}
  >
    <defs>
      <pattern id="kolam" x="0" y="0" width="120" height="120" patternUnits="userSpaceOnUse">
        {/* Dot grid */}
        {[0, 1, 2, 3, 4].map(row =>
          [0, 1, 2, 3, 4].map(col => (
            <circle
              key={`${row}-${col}`}
              cx={12 + col * 24}
              cy={12 + row * 24}
              r="2"
              fill="#C27B3A"
            />
          ))
        )}
        {/* Curved connecting lines */}
        <path
          d="M12,12 Q36,0 60,12 Q84,24 108,12"
          fill="none"
          stroke="#C27B3A"
          strokeWidth="0.8"
        />
        <path
          d="M12,36 Q36,24 60,36 Q84,48 108,36"
          fill="none"
          stroke="#D49A5E"
          strokeWidth="0.6"
        />
        <path
          d="M12,60 Q36,48 60,60 Q84,72 108,60"
          fill="none"
          stroke="#C27B3A"
          strokeWidth="0.8"
        />
        <path
          d="M12,84 Q36,72 60,84 Q84,96 108,84"
          fill="none"
          stroke="#D49A5E"
          strokeWidth="0.6"
        />
        <path
          d="M12,108 Q36,96 60,108 Q84,120 108,108"
          fill="none"
          stroke="#C27B3A"
          strokeWidth="0.8"
        />
        {/* Vertical curves */}
        <path
          d="M12,12 Q0,36 12,60 Q24,84 12,108"
          fill="none"
          stroke="#A66228"
          strokeWidth="0.5"
        />
        <path
          d="M60,12 Q48,36 60,60 Q72,84 60,108"
          fill="none"
          stroke="#A66228"
          strokeWidth="0.5"
        />
        <path
          d="M108,12 Q96,36 108,60 Q120,84 108,108"
          fill="none"
          stroke="#A66228"
          strokeWidth="0.5"
        />
      </pattern>
    </defs>
    <rect width="100%" height="100%" fill="url(#kolam)" />
  </svg>
);

export default RangoliPattern;
