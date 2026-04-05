import { useEffect, useRef, useCallback } from 'react';

type RevealMode = 'fadeUp' | 'fadeIn' | 'clipReveal' | 'scaleIn' | 'staggerChildren' | 'drawLine';

interface UseScrollRevealOptions {
  mode?: RevealMode;
  threshold?: number;
  delay?: number;
  duration?: number;
  staggerDelay?: number;
  once?: boolean;
  rootMargin?: string;
}

const STYLE_MAP: Record<RevealMode, { initial: Partial<CSSStyleDeclaration>; revealed: Partial<CSSStyleDeclaration> }> = {
  fadeUp: {
    initial: { opacity: '0', transform: 'translateY(30px)', transition: '' },
    revealed: { opacity: '1', transform: 'translateY(0)' },
  },
  fadeIn: {
    initial: { opacity: '0', transition: '' },
    revealed: { opacity: '1' },
  },
  clipReveal: {
    initial: { clipPath: 'inset(0 100% 0 0)', transition: '' },
    revealed: { clipPath: 'inset(0 0% 0 0)' },
  },
  scaleIn: {
    initial: { opacity: '0', transform: 'scale(0.92)', transition: '' },
    revealed: { opacity: '1', transform: 'scale(1)' },
  },
  staggerChildren: {
    initial: {},
    revealed: {},
  },
  drawLine: {
    initial: { strokeDashoffset: 'var(--path-length, 1000)', transition: '' },
    revealed: { strokeDashoffset: '0' },
  },
};

export function useScrollReveal<T extends HTMLElement = HTMLDivElement>(
  options: UseScrollRevealOptions = {}
) {
  const {
    mode = 'fadeUp',
    threshold = 0.15,
    delay = 0,
    duration = 600,
    staggerDelay = 40,
    once = true,
    rootMargin = '0px 0px -60px 0px',
  } = options;

  const ref = useRef<T>(null);
  const hasRevealed = useRef(false);

  const reduceMotion = typeof window !== 'undefined'
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : false;

  const applyStyles = useCallback(
    (element: HTMLElement, styles: Partial<CSSStyleDeclaration>) => {
      Object.entries(styles).forEach(([key, value]) => {
        if (value !== undefined) {
          (element.style as any)[key] = value;
        }
      });
    },
    []
  );

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    // If reduced motion, show everything immediately
    if (reduceMotion) {
      if (mode === 'staggerChildren') {
        const children = Array.from(el.children) as HTMLElement[];
        children.forEach((child) => {
          child.style.opacity = '1';
          child.style.transform = 'none';
        });
      }
      return;
    }

    const easing = 'cubic-bezier(0.25, 1, 0.5, 1)'; // ease-out-quart
    const styleConfig = STYLE_MAP[mode];

    // Apply initial styles
    if (mode === 'staggerChildren') {
      const children = Array.from(el.children) as HTMLElement[];
      children.forEach((child) => {
        child.style.opacity = '0';
        child.style.transform = 'translateY(20px)';
      });
    } else {
      applyStyles(el, styleConfig.initial);
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            if (once && hasRevealed.current) return;
            hasRevealed.current = true;

            if (mode === 'staggerChildren') {
              const children = Array.from(el.children) as HTMLElement[];
              children.forEach((child, i) => {
                const childDelay = delay + i * staggerDelay;
                child.style.transition = `opacity ${duration}ms ${easing} ${childDelay}ms, transform ${duration}ms ${easing} ${childDelay}ms`;
                requestAnimationFrame(() => {
                  child.style.opacity = '1';
                  child.style.transform = 'translateY(0)';
                });
              });
            } else {
              el.style.transition = Object.keys(styleConfig.revealed)
                .map((prop) => {
                  const cssProp = prop.replace(/([A-Z])/g, '-$1').toLowerCase();
                  return `${cssProp} ${duration}ms ${easing} ${delay}ms`;
                })
                .join(', ');
              requestAnimationFrame(() => {
                applyStyles(el, styleConfig.revealed);
              });
            }

            if (once) {
              observer.unobserve(el);
            }
          } else if (!once && hasRevealed.current) {
            // Reset for non-once mode
            hasRevealed.current = false;
            if (mode === 'staggerChildren') {
              const children = Array.from(el.children) as HTMLElement[];
              children.forEach((child) => {
                child.style.opacity = '0';
                child.style.transform = 'translateY(20px)';
              });
            } else {
              applyStyles(el, styleConfig.initial);
            }
          }
        });
      },
      { threshold, rootMargin }
    );

    observer.observe(el);

    return () => {
      observer.disconnect();
    };
  }, [mode, threshold, delay, duration, staggerDelay, once, rootMargin, reduceMotion, applyStyles]);

  return ref;
}

export default useScrollReveal;
