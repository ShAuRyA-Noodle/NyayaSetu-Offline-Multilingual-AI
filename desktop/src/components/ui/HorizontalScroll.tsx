import { useEffect, useRef, ReactNode } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

interface HorizontalScrollProps {
  children: ReactNode;
  className?: string;
}

export default function HorizontalScroll({ children, className = '' }: HorizontalScrollProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const innerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    const inner = innerRef.current;
    if (!container || !inner) return;

    const totalWidth = inner.scrollWidth;
    const viewportWidth = container.offsetWidth;

    if (totalWidth <= viewportWidth) return;

    const tween = gsap.to(inner, {
      x: -(totalWidth - viewportWidth),
      ease: 'none',
      scrollTrigger: {
        trigger: container,
        start: 'top 20%',
        end: () => `+=${totalWidth - viewportWidth}`,
        scrub: 1,
        pin: true,
        anticipatePin: 1,
        invalidateOnRefresh: true,
      },
    });

    return () => {
      tween.kill();
      ScrollTrigger.getAll().forEach(st => {
        if (st.trigger === container) st.kill();
      });
    };
  }, []);

  return (
    <div ref={containerRef} className={`overflow-hidden ${className}`}>
      <div ref={innerRef} className="flex gap-6 will-change-transform">
        {children}
      </div>
    </div>
  );
}
