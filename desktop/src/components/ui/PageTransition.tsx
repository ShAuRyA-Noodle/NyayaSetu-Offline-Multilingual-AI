import React from 'react';
import { motion, Variants, Transition } from 'framer-motion';

type TransitionVariant = 'default' | 'hero' | 'panel' | 'fade';

interface PageTransitionProps {
  children: React.ReactNode;
  className?: string;
  variant?: TransitionVariant;
}

// Easing curves (matching CSS tokens)
const easeOutQuart = [0.25, 1, 0.5, 1] as const;
const easeOutQuint = [0.22, 1, 0.36, 1] as const;

// Transition variants
const variants: Record<TransitionVariant, {
  variants: Variants;
  transition: Transition;
  exitTransition?: Transition;
}> = {
  // Default: slide up with blur-clear
  default: {
    variants: {
      initial: { opacity: 0, y: 30, filter: 'blur(6px)' },
      animate: { opacity: 1, y: 0, filter: 'blur(0px)' },
      exit: { opacity: 0, y: -15, filter: 'blur(4px)' },
    },
    transition: {
      duration: 0.5,
      ease: [...easeOutQuart],
    },
    exitTransition: {
      duration: 0.35, // Exit faster than enter
      ease: [...easeOutQuart],
    },
  },

  // Hero: scale + fade for impactful pages (Login, Dashboard)
  hero: {
    variants: {
      initial: { opacity: 0, scale: 0.96, filter: 'blur(8px)' },
      animate: { opacity: 1, scale: 1, filter: 'blur(0px)' },
      exit: { opacity: 0, scale: 1.02, filter: 'blur(6px)' },
    },
    transition: {
      duration: 0.6,
      ease: [...easeOutQuint],
    },
    exitTransition: {
      duration: 0.4,
      ease: [...easeOutQuart],
    },
  },

  // Panel: slide from right (for detail views, modals)
  panel: {
    variants: {
      initial: { opacity: 0, x: 40 },
      animate: { opacity: 1, x: 0 },
      exit: { opacity: 0, x: -20 },
    },
    transition: {
      duration: 0.45,
      ease: [...easeOutQuart],
    },
    exitTransition: {
      duration: 0.3,
      ease: [...easeOutQuart],
    },
  },

  // Fade: simple crossfade
  fade: {
    variants: {
      initial: { opacity: 0 },
      animate: { opacity: 1 },
      exit: { opacity: 0 },
    },
    transition: {
      duration: 0.3,
      ease: [...easeOutQuart],
    },
  },
};

const PageTransition: React.FC<PageTransitionProps> = ({
  children,
  className = '',
  variant = 'default',
}) => {
  const config = variants[variant];

  // Check reduced motion
  const reduceMotion = typeof window !== 'undefined'
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : false;

  if (reduceMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      className={className}
      initial="initial"
      animate="animate"
      exit="exit"
      variants={config.variants}
      transition={config.transition}
      // Use faster exit transition when exiting
      style={{ willChange: 'auto' }}
    >
      {children}
    </motion.div>
  );
};

export default PageTransition;
