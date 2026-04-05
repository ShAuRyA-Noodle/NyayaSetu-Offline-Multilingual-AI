import React, { useRef, useEffect } from 'react';
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
}) => {
  const tiltRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!tilt || !tiltRef.current) return;
    const el = tiltRef.current;
    const maxTilt = 6;

    el.style.transformStyle = 'preserve-3d';
    el.style.transition = 'transform 0.15s ease-out';

    const handleMove = (e: MouseEvent) => {
      const rect = el.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      el.style.transform = `perspective(800px) rotateY(${x * maxTilt}deg) rotateX(${-y * maxTilt}deg) scale3d(1.02, 1.02, 1.02)`;
    };

    const handleLeave = () => {
      el.style.transform = 'perspective(800px) rotateY(0deg) rotateX(0deg) scale3d(1, 1, 1)';
    };

    el.addEventListener('mousemove', handleMove);
    el.addEventListener('mouseleave', handleLeave);
    return () => {
      el.removeEventListener('mousemove', handleMove);
      el.removeEventListener('mouseleave', handleLeave);
    };
  }, [tilt]);

  const classes = `${variantClasses[variant] || variantClasses.default} ${textured ? 'grain-overlay' : ''} ${className}`;

  if (!animate) {
    return (
      <div ref={tilt ? tiltRef : undefined} className={classes} onClick={onClick} data-cursor={tilt ? 'expand' : undefined}>
        {children}
      </div>
    );
  }

  return (
    <motion.div
      ref={tilt ? (tiltRef as any) : undefined}
      className={classes}
      onClick={onClick}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: 'easeOut' }}
      data-cursor={tilt ? 'expand' : undefined}
    >
      {children}
    </motion.div>
  );
};

export default GlassCard;
