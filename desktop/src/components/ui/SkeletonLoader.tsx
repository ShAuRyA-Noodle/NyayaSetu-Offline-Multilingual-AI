import React from 'react';

interface SkeletonLoaderProps {
  variant?: 'text' | 'card' | 'avatar' | 'chart' | 'table-row' | 'circle';
  width?: string | number;
  height?: string | number;
  count?: number;
  className?: string;
}

const variantStyles: Record<string, React.CSSProperties> = {
  text: { height: '16px', borderRadius: '6px' },
  card: { height: '180px', borderRadius: '16px' },
  avatar: { width: '40px', height: '40px', borderRadius: '50%' },
  chart: { height: '200px', borderRadius: '12px' },
  'table-row': { height: '48px', borderRadius: '8px' },
  circle: { width: '48px', height: '48px', borderRadius: '50%' },
};

const textWidths = ['100%', '85%', '92%', '78%', '95%', '88%'];

const SkeletonLoader: React.FC<SkeletonLoaderProps> = ({
  variant = 'text',
  width,
  height,
  count = 1,
  className = '',
}) => {
  const baseStyle = variantStyles[variant] || variantStyles.text;

  return (
    <div className={`space-y-3 ${className}`} role="status" aria-label="Loading content">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="skeleton"
          style={{
            ...baseStyle,
            width: width || (variant === 'text' ? textWidths[i % textWidths.length] : '100%'),
            height: height || baseStyle.height,
          }}
        />
      ))}
      <span className="sr-only">Loading...</span>
    </div>
  );
};

export default SkeletonLoader;
