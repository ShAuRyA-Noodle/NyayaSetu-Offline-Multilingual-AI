import React from 'react';

interface AshokaChakraProps {
  size?: number;
  className?: string;
  spinning?: boolean;
  color?: string;
}

// Warli-style sun motif — village folk art aesthetic
const AshokaChakra: React.FC<AshokaChakraProps> = ({
  size = 48,
  className = '',
  spinning = false,
  color = '#C27B3A',
}) => {
  const rays = Array.from({ length: 12 }, (_, i) => i * 30);

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      className={`${spinning ? 'animate-chakra-spin' : ''} ${className}`}
    >
      {/* Central circle */}
      <circle cx="50" cy="50" r="12" fill={color} opacity="0.9" />
      <circle cx="50" cy="50" r="18" fill="none" stroke={color} strokeWidth="1.5" opacity="0.6" />

      {/* Triangular rays — Warli sun style */}
      {rays.map((angle) => {
        const rad = (angle * Math.PI) / 180;
        const innerR = 20;
        const outerR = 42;
        const spread = 8;
        const tipX = 50 + outerR * Math.cos(rad);
        const tipY = 50 + outerR * Math.sin(rad);
        const leftX = 50 + innerR * Math.cos(rad - (spread * Math.PI) / 180);
        const leftY = 50 + innerR * Math.sin(rad - (spread * Math.PI) / 180);
        const rightX = 50 + innerR * Math.cos(rad + (spread * Math.PI) / 180);
        const rightY = 50 + innerR * Math.sin(rad + (spread * Math.PI) / 180);
        return (
          <polygon
            key={angle}
            points={`${tipX},${tipY} ${leftX},${leftY} ${rightX},${rightY}`}
            fill={color}
            opacity="0.7"
          />
        );
      })}

      {/* Outer ring of dots */}
      {rays.filter((_, i) => i % 2 === 0).map((angle) => {
        const rad = (angle * Math.PI) / 180;
        return (
          <circle
            key={`dot-${angle}`}
            cx={50 + 46 * Math.cos(rad)}
            cy={50 + 46 * Math.sin(rad)}
            r="1.5"
            fill={color}
            opacity="0.4"
          />
        );
      })}
    </svg>
  );
};

export default AshokaChakra;
