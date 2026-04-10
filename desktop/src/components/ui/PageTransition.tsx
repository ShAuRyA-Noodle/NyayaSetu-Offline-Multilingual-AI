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
  // Default: slide up — no blur (blur is expensive on every route change)
  default: {
    variants: {
      initial: { opacity: 0, y: 16 },
      animate: { opacity: 1, y: 0 },
      exit: { opacity: 0, y: -8 },
    },
    transition: {
      duration: 0.25,
      ease: [...easeOutQuart],
    },
    exitTransition: {
      duration: 0.18,
      ease: [...easeOutQuart],
    },
  },

  // Hero: scale + fade — no blur
  hero: {
    variants: {
      initial: { opacity: 0, scale: 0.97 },
      animate: { opacity: 1, scale: 1 },
      exit: { opacity: 0, scale: 1.01 },
    },
    transition: {
      duration: 0.3,
      ease: [...easeOutQuint],
    },
    exitTransition: {
      duration: 0.2,
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
