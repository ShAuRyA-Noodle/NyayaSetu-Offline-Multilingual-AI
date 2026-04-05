import React from 'react';

interface ThemedSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const ThemedSpinner: React.FC<ThemedSpinnerProps> = ({ size = 'md', className = '' }) => {
  const sizeClass = size === 'sm' ? 'chakra-spinner chakra-spinner-sm' : size === 'lg' ? 'chakra-spinner chakra-spinner-lg' : 'chakra-spinner';
  return <div className={`${sizeClass} ${className}`} />;
};

export default ThemedSpinner;
