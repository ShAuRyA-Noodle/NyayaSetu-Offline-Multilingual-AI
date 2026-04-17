import React, { useEffect, useRef } from 'react';
import { useScrollContext } from '../providers/SmoothScrollProvider';

const ScrollProgress: React.FC = () => {
  const barRef = useRef<HTMLDivElement>(null);
  const { scrollProgress } = useScrollContext();

  useEffect(() => {
    if (!barRef.current) return;
    barRef.current.style.transform = `scaleX(${scrollProgress})`;
    const opacity = scrollProgress < 0.02 ? 0 :
                    scrollProgress > 0.98 ? (1 - scrollProgress) / 0.02 : 0.8;
    barRef.current.style.opacity = String(Math.max(0, Math.min(1, opacity)));
  }, [scrollProgress]);

  return (
    <div
      ref={barRef}
      role="progressbar"
      aria-label="Scroll progress"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: '2px',
        background: 'linear-gradient(90deg, #0D92F4, #77CDFF, #0D92F4)',
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
