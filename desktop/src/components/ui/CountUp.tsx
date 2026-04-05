import React, { useEffect, useRef, useState, useCallback } from 'react';

interface CountUpProps {
  end: number;
  start?: number;
  duration?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  separator?: string;
  className?: string;
  triggerOnScroll?: boolean;
}

function easeOutQuart(t: number): number {
  return 1 - Math.pow(1 - t, 4);
}

function formatNumber(num: number, decimals: number, separator: string): string {
  const fixed = num.toFixed(decimals);
  if (!separator) return fixed;

  const [intPart, decPart] = fixed.split('.');
  const formatted = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, separator);
  return decPart ? `${formatted}.${decPart}` : formatted;
}

const CountUp: React.FC<CountUpProps> = ({
  end,
  start = 0,
  duration = 1200,
  decimals = 0,
  prefix = '',
  suffix = '',
  separator = ',',
  className = '',
  triggerOnScroll = true,
}) => {
  const [displayValue, setDisplayValue] = useState(start);
  const [hasStarted, setHasStarted] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  const rafRef = useRef<number>(0);

  const reduceMotion = typeof window !== 'undefined'
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : false;

  const startAnimation = useCallback(() => {
    if (hasStarted || reduceMotion) {
      setDisplayValue(end);
      return;
    }
    setHasStarted(true);

    const startTime = performance.now();

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easedProgress = easeOutQuart(progress);
      const currentValue = start + (end - start) * easedProgress;

      setDisplayValue(currentValue);

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      }
    };

    rafRef.current = requestAnimationFrame(animate);
  }, [start, end, duration, hasStarted, reduceMotion]);

  useEffect(() => {
    if (!triggerOnScroll) {
      startAnimation();
      return;
    }

    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasStarted) {
          startAnimation();
          observer.disconnect();
        }
      },
      { threshold: 0.3 }
    );

    observer.observe(el);

    return () => {
      observer.disconnect();
      cancelAnimationFrame(rafRef.current);
    };
  }, [triggerOnScroll, startAnimation, hasStarted]);

  return (
    <span
      ref={ref}
      className={`tabular-nums ${className}`}
      style={{ fontVariantNumeric: 'tabular-nums' }}
    >
      {prefix}{formatNumber(displayValue, decimals, separator)}{suffix}
    </span>
  );
};

export default CountUp;
