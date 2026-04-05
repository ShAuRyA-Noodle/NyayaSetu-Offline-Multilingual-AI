import React, { useEffect, useRef } from 'react';
import { useScrollContext } from '../providers/SmoothScrollProvider';

interface ScrollProgressProps {
  className?: string;
}

const ScrollProgress: React.FC<ScrollProgressProps> = ({ className = '' }) => {
  const barRef = useRef<HTMLDivElement>(null);
  const { scrollProgress } = useScrollContext();

  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduceMotion || !barRef.current) return;

    const progress = scrollProgress;
    barRef.current.style.transform = `scaleX(${progress})`;

    const opacity = progress < 0.05 ? progress / 0.05 :
                    progress > 0.95 ? (1 - progress) / 0.05 : 1;
    barRef.current.style.opacity = String(Math.max(0, Math.min(1, opacity)));
  }, [scrollProgress]);

  return (
    <div
      ref={barRef}
      className={`scroll-progress-bar ${className}`}
      role="progressbar"
      aria-label="Page scroll progress"
      aria-valuemin={0}
      aria-valuemax={100}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: '3px',
        background: 'linear-gradient(90deg, #C27B3A, #F59E0B, #2D4A7A)',
        transformOrigin: 'left',
        transform: 'scaleX(0)',
        willChange: 'transform',
        zIndex: 9990,
        pointerEvents: 'none',
        opacity: 0,
      }}
    />
  );
};

export default ScrollProgress;
