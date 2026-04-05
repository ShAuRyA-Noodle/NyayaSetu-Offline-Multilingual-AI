import { ReactNode, useEffect, useCallback, createContext, useContext, useRef, useState } from 'react';
import { ReactLenis, useLenis } from '@studio-freight/react-lenis';

interface ScrollContextValue {
  scrollY: number;
  scrollDirection: 'up' | 'down' | 'idle';
  scrollVelocity: number;
  scrollProgress: number;
}

const ScrollContext = createContext<ScrollContextValue>({
  scrollY: 0,
  scrollDirection: 'idle',
  scrollVelocity: 0,
  scrollProgress: 0,
});

export const useScrollContext = () => useContext(ScrollContext);

interface SmoothScrollProviderProps {
  children: ReactNode;
}

function ScrollTracker({ children }: { children: ReactNode }) {
  const [scrollData, setScrollData] = useState<ScrollContextValue>({
    scrollY: 0,
    scrollDirection: 'idle',
    scrollVelocity: 0,
    scrollProgress: 0,
  });

  const lastUpdate = useRef(0);
  const pendingData = useRef<ScrollContextValue | null>(null);
  const rafId = useRef(0);

  useLenis((lenis: any) => {
    const direction = lenis.direction > 0 ? 'down' : lenis.direction < 0 ? 'up' : 'idle';
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const progress = docHeight > 0 ? Math.min(lenis.scroll / docHeight, 1) : 0;

    const data: ScrollContextValue = {
      scrollY: lenis.scroll,
      scrollDirection: direction as 'up' | 'down' | 'idle',
      scrollVelocity: Math.abs(lenis.velocity || 0),
      scrollProgress: progress,
    };

    // Throttle React state updates to ~60ms to avoid re-rendering entire tree every frame
    const now = performance.now();
    if (now - lastUpdate.current > 60) {
      lastUpdate.current = now;
      setScrollData(data);
    } else {
      // Schedule a trailing update so final position is always correct
      pendingData.current = data;
      cancelAnimationFrame(rafId.current);
      rafId.current = requestAnimationFrame(() => {
        if (pendingData.current) {
          lastUpdate.current = performance.now();
          setScrollData(pendingData.current);
          pendingData.current = null;
        }
      });
    }
  });

  useEffect(() => {
    return () => cancelAnimationFrame(rafId.current);
  }, []);

  return (
    <ScrollContext.Provider value={scrollData}>
      {children}
    </ScrollContext.Provider>
  );
}

export default function SmoothScrollProvider({ children }: SmoothScrollProviderProps) {
  // Check for reduced motion preference
  const reduceMotion = typeof window !== 'undefined'
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : false;

  // Register GSAP ScrollTrigger proxy when Lenis instance is available
  const lenisSetup = useCallback(async () => {
    try {
      const { gsap } = await import('gsap');
      const { ScrollTrigger } = await import('gsap/ScrollTrigger');
      gsap.registerPlugin(ScrollTrigger);

      // ScrollTrigger will sync with Lenis via the RAF loop
      ScrollTrigger.defaults({
        scroller: window,
      });
    } catch {
      // GSAP not available, degrade gracefully
      console.debug('[NyayaSetu] GSAP ScrollTrigger not available, scroll animations will use CSS fallback');
    }
  }, []);

  useEffect(() => {
    lenisSetup();
  }, [lenisSetup]);

  if (reduceMotion) {
    // Skip smooth scrolling for users who prefer reduced motion
    return <ScrollTracker>{children}</ScrollTracker>;
  }

  return (
    <ReactLenis
      root
      options={{
        lerp: 0.12,
        duration: 1.0,
        smoothWheel: true,
        wheelMultiplier: 1.2,
        touchMultiplier: 1.5,
        syncTouch: false,
      }}
    >
      <ScrollTracker>{children}</ScrollTracker>
    </ReactLenis>
  );
}
