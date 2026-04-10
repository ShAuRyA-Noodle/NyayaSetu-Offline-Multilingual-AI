import { useEffect, useRef } from 'react';

interface CustomCursorProps {
  enabled?: boolean;
}

export default function CustomCursor({ enabled = true }: CustomCursorProps) {
  const dotRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);
  const mouse = useRef({ x: 0, y: 0 });
  const ringPos = useRef({ x: 0, y: 0 });
  const rafRef = useRef<number>(0);
  const isVisible = useRef(true);
  // Track hover/expand state via refs to avoid React re-renders in the RAF loop
  const stateRef = useRef({ hovering: false, expanded: false });

  useEffect(() => {
    if (!enabled) {
      document.body.classList.remove('custom-cursor');
      return;
    }
    if (window.matchMedia('(pointer: coarse)').matches) return;

    document.body.classList.add('custom-cursor');

    const dot = dotRef.current;
    const ring = ringRef.current;
    if (!dot || !ring) return;

    const handleMouseMove = (e: MouseEvent) => {
      mouse.current.x = e.clientX;
      mouse.current.y = e.clientY;
      dot.style.transform = `translate(${e.clientX - 4}px, ${e.clientY - 4}px)`;
    };

    const handleMouseOver = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const interactive = target.closest('a, button, [role="button"], input, textarea, select, label, [data-cursor]');
      const prev = stateRef.current;

      if (interactive) {
        const cursorType = (interactive as HTMLElement).getAttribute('data-cursor');
        const next = { hovering: cursorType !== 'expand', expanded: cursorType === 'expand' };
        if (next.hovering !== prev.hovering || next.expanded !== prev.expanded) {
          stateRef.current = next;
          applyRingStyle();
        }
      } else if (prev.hovering || prev.expanded) {
        stateRef.current = { hovering: false, expanded: false };
        applyRingStyle();
      }
    };

    const applyRingStyle = () => {
      const { hovering, expanded } = stateRef.current;
      if (expanded) {
        ring.style.width = '80px';
        ring.style.height = '80px';
        ring.style.marginLeft = '-22px';
        ring.style.marginTop = '-22px';
        ring.style.border = 'none';
        ring.style.backgroundColor = 'rgba(194, 123, 58, 0.1)';
      } else if (hovering) {
        ring.style.width = '48px';
        ring.style.height = '48px';
        ring.style.marginLeft = '-6px';
        ring.style.marginTop = '-6px';
        ring.style.border = '2px solid #F59E0B';
        ring.style.backgroundColor = 'transparent';
      } else {
        ring.style.width = '36px';
        ring.style.height = '36px';
        ring.style.marginLeft = '0px';
        ring.style.marginTop = '0px';
        ring.style.border = '2px solid rgba(194, 123, 58, 0.5)';
        ring.style.backgroundColor = 'transparent';
      }
    };

    const onVisibilityChange = () => {
      isVisible.current = !document.hidden;
      if (isVisible.current) rafRef.current = requestAnimationFrame(animate);
    };

    const animate = () => {
      if (!isVisible.current) return;
      ringPos.current.x += (mouse.current.x - ringPos.current.x) * 0.15;
      ringPos.current.y += (mouse.current.y - ringPos.current.y) * 0.15;
      ring.style.transform = `translate(${ringPos.current.x - 18}px, ${ringPos.current.y - 18}px)`;
      rafRef.current = requestAnimationFrame(animate);
    };

    document.addEventListener('mousemove', handleMouseMove, { passive: true });
    document.addEventListener('mouseover', handleMouseOver, { passive: true });
    document.addEventListener('visibilitychange', onVisibilityChange);
    rafRef.current = requestAnimationFrame(animate);

    return () => {
      document.body.classList.remove('custom-cursor');
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseover', handleMouseOver);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      cancelAnimationFrame(rafRef.current);
    };
  }, [enabled]);

  if (!enabled) return null;

  return (
    <>
      {/* Dot — instant follow */}
      <div
        ref={dotRef}
        className="fixed top-0 left-0 pointer-events-none z-[9999] mix-blend-difference"
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          backgroundColor: '#C27B3A',
          willChange: 'transform',
        }}
      />
      {/* Ring — lerp follow, state changes via direct DOM */}
      <div
        ref={ringRef}
        className="fixed top-0 left-0 pointer-events-none z-[9998]"
        style={{
          width: 36,
          height: 36,
          borderRadius: '50%',
          border: '2px solid rgba(194, 123, 58, 0.5)',
          backgroundColor: 'transparent',
          transition: 'width 0.25s cubic-bezier(0.25,1,0.5,1), height 0.25s cubic-bezier(0.25,1,0.5,1), border-color 0.2s, background-color 0.2s, margin 0.25s cubic-bezier(0.25,1,0.5,1)',
          willChange: 'transform',
        }}
      />
    </>
  );
}
