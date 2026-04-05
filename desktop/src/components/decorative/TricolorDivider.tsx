import React from 'react';

interface TricolorDividerProps {
  className?: string;
  width?: string;
}

// Kolam-style earthy divider — replaces tricolor lines
const TricolorDivider: React.FC<TricolorDividerProps> = ({ className = '', width = 'w-32' }) => (
  <div className={`${width} ${className}`}>
    <div className="kolam-divider" />
  </div>
);

export default TricolorDivider;
