import React, { useRef, useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';

interface GlassCardProps {
  children: React.ReactNode;
  variant?: 'default' | 'saffron' | 'green' | 'subtle' | 'mitti' | 'haldi' | 'neel';
  className?: string;
  onClick?: () => void;
  animate?: boolean;
  delay?: number;
  tilt?: boolean;
  textured?: boolean;
  shimmer?: boolean;
  hoverLift?: boolean;
}

const variantClasses: Record<string, string> = {
  default: 'village-card',
  saffron: 'village-card-mitti',
  green: 'village-card-neel',
  subtle: 'village-card-subtle',
  mitti: 'village-card-mitti',
  haldi: 'village-card-haldi',
  neel: 'village-card-neel',
};

const GlassCard: React.FC<GlassCardProps> = ({
  children,
  variant = 'default',
  className = '',
  onClick,
  animate = true,
  delay = 0,
  tilt = false,
  textured = false,
  shimmer = false,
  hoverLift = true,
}) => {
  const tiltRef = useRef<HTMLDivElement>(null);
  const [mousePos, setMousePos] = useState({ x: 0.5, y: 0.5 });
  const [isHovered, setIsHovered] = useState(false);

  // Check for touch device — disable tilt on touch
  const isTouchDevice = typeof window !== 'undefined' && 'ontouchstart' in window;
  const shouldTilt = tilt && !isTouchDevice;

  const handleMove = useCallback((e: MouseEvent) => {
    if (!tiltRef.current || !shouldTilt) return;
    const el = tiltRef.current;
    const rect = el.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;

    setMousePos({ x, y });

    const maxTilt = 5;
    const tiltX = (x - 0.5) * maxTilt;
    const tiltY = -(y - 0.5) * maxTilt;

    el.style.transform = `perspective(800px) rotateY(${tiltX}deg) rotateX(${tiltY}deg) scale3d(1.015, 1.015, 1.015)`;
  }, [shouldTilt]);

  const handleLeave = useCallback(() => {
    if (!tiltRef.current) return;
    tiltRef.current.style.transform = 'perspective(800px) rotateY(0deg) rotateX(0deg) scale3d(1, 1, 1)';
    setIsHovered(false);
  }, []);

  const handleEnter = useCallback(() => {
    setIsHovered(true);
  }, []);

  useEffect(() => {
    if (!shouldTilt || !tiltRef.current) return;
    const el = tiltRef.current;

    el.style.transformStyle = 'preserve-3d';
    el.style.transition = 'transform 0.2s cubic-bezier(0.25, 1, 0.5, 1)';

    el.addEventListener('mousemove', handleMove);
    el.addEventListener('mouseleave', handleLeave);
    el.addEventListener('mouseenter', handleEnter);
    return () => {
      el.removeEventListener('mousemove', handleMove);
      el.removeEventListener('mouseleave', handleLeave);
      el.removeEventListener('mouseenter', handleEnter);
    };
  }, [shouldTilt, handleMove, handleLeave, handleEnter]);

  const classes = `${variantClasses[variant] || variantClasses.default} ${textured ? 'grain-overlay' : ''} ${shimmer ? 'hover-shimmer' : ''} ${className}`;

  // Light reflection gradient that follows mouse
  const lightReflection = shouldTilt && isHovered ? (
    <div
      className="absolute inset-0 rounded-2xl pointer-events-none z-10 opacity-50"
      style={{
        background: `radial-gradient(circle at ${mousePos.x * 100}% ${mousePos.y * 100}%, rgba(255,255,255,0.08) 0%, transparent 50%)`,
        transition: 'background 0.1s ease-out',
      }}
    />
  ) : null;

  if (!animate) {
    return (
      <div
        ref={shouldTilt ? tiltRef : undefined}
        className={`relative overflow-hidden ${classes}`}
        onClick={onClick}
        data-cursor={shouldTilt ? 'expand' : undefined}
      >
        {lightReflection}
        {children}
      </div>
    );
  }

  return (
    <motion.div
      ref={shouldTilt ? (tiltRef as any) : undefined}
      className={`relative overflow-hidden ${classes}`}
      onClick={onClick}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.45,
        delay,
        ease: [0.25, 1, 0.5, 1],
      }}
      whileHover={hoverLift && !shouldTilt ? { y: -3 } : undefined}
      data-cursor={shouldTilt ? 'expand' : undefined}
      style={{ willChange: 'transform' }}
    >
      {lightReflection}
      {children}
    </motion.div>
  );
};

export default GlassCard;
