import React from 'react';
import { motion, Variants, Transition } from 'framer-motion';

type TransitionVariant = 'default' | 'hero' | 'panel' | 'fade';

interface PageTransitionProps {
  children: React.ReactNode;
  className?: string;
  variant?: TransitionVariant;
}

const easeOutQuint = [0.22, 1, 0.36, 1] as const;

const variants: Record<TransitionVariant, {
  variants: Variants;
  transition: Transition;
}> = {
  default: {
    variants: {
      initial: { opacity: 0, y: 24, scale: 0.99 },
      animate: { opacity: 1, y: 0, scale: 1 },
      exit: { opacity: 0, y: -12, scale: 0.995 },
    },
    transition: {
      duration: 0.45,
      ease: [...easeOutQuint],
    },
  },
  hero: {
    variants: {
      initial: { opacity: 0, scale: 0.96 },
      animate: { opacity: 1, scale: 1 },
      exit: { opacity: 0, scale: 1.02 },
    },
    transition: {
      duration: 0.5,
      ease: [...easeOutQuint],
    },
  },
  panel: {
    variants: {
      initial: { opacity: 0, x: 40 },
      animate: { opacity: 1, x: 0 },
      exit: { opacity: 0, x: -20 },
    },
    transition: {
      duration: 0.5,
      ease: [...easeOutQuint],
    },
  },
  fade: {
    variants: {
      initial: { opacity: 0 },
      animate: { opacity: 1 },
      exit: { opacity: 0 },
    },
    transition: {
      duration: 0.4,
      ease: [...easeOutQuint],
    },
  },
};

const PageTransition: React.FC<PageTransitionProps> = ({
  children,
  className = '',
  variant = 'default',
}) => {
  const config = variants[variant];

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
    >
      {children}
    </motion.div>
  );
};

export default PageTransition;
