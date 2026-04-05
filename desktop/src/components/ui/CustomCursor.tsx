import { useEffect, useRef, useState } from 'react';

interface CustomCursorProps {
  enabled?: boolean;
}

export default function CustomCursor({ enabled = true }: CustomCursorProps) {
  const dotRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);
  const mouse = useRef({ x: 0, y: 0 });
  const ringPos = useRef({ x: 0, y: 0 });
  const [isHovering, setIsHovering] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    if (!enabled) {
      document.body.classList.remove('custom-cursor');
      return;
    }

    // Check for touch device
    if (window.matchMedia('(pointer: coarse)').matches) return;

    document.body.classList.add('custom-cursor');

    const handleMouseMove = (e: MouseEvent) => {
      mouse.current.x = e.clientX;
      mouse.current.y = e.clientY;

      if (dotRef.current) {
        dotRef.current.style.transform = `translate(${e.clientX - 4}px, ${e.clientY - 4}px)`;
      }
    };

    const handleMouseOver = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const interactive = target.closest('a, button, [role="button"], input, textarea, select, label, [data-cursor]');

      if (interactive) {
        const cursorType = interactive.getAttribute('data-cursor');
        if (cursorType === 'expand') {
          setIsExpanded(true);
          setIsHovering(false);
        } else {
          setIsHovering(true);
          setIsExpanded(false);
        }
      } else {
        setIsHovering(false);
        setIsExpanded(false);
      }
    };

    const animate = () => {
      const lerp = 0.15;
      ringPos.current.x += (mouse.current.x - ringPos.current.x) * lerp;
      ringPos.current.y += (mouse.current.y - ringPos.current.y) * lerp;

      if (ringRef.current) {
        ringRef.current.style.transform = `translate(${ringPos.current.x - 18}px, ${ringPos.current.y - 18}px)`;
      }

      rafRef.current = requestAnimationFrame(animate);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseover', handleMouseOver);
    rafRef.current = requestAnimationFrame(animate);

    return () => {
      document.body.classList.remove('custom-cursor');
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseover', handleMouseOver);
      cancelAnimationFrame(rafRef.current);
    };
  }, [enabled]);

  if (!enabled) return null;

  return (
    <>
      {/* Dot */}
      <div
        ref={dotRef}
        className="fixed top-0 left-0 pointer-events-none z-[9999] mix-blend-difference"
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          backgroundColor: '#C27B3A',
          transition: isHovering ? 'width 0.3s, height 0.3s' : 'none',
          ...(isHovering && { width: 4, height: 4 }),
        }}
      />
      {/* Ring */}
      <div
        ref={ringRef}
        className="fixed top-0 left-0 pointer-events-none z-[9998]"
        style={{
          width: 36,
          height: 36,
          borderRadius: '50%',
          border: isExpanded ? 'none' : `2px solid ${isHovering ? '#F59E0B' : 'rgba(194, 123, 58, 0.5)'}`,
          backgroundColor: isExpanded ? 'rgba(194, 123, 58, 0.1)' : 'transparent',
          transition: 'width 0.4s cubic-bezier(0.25, 0.1, 0.25, 1), height 0.4s cubic-bezier(0.25, 0.1, 0.25, 1), border-color 0.3s, background-color 0.3s',
          ...(isHovering && { width: 48, height: 48, marginLeft: -6, marginTop: -6 }),
          ...(isExpanded && { width: 80, height: 80, marginLeft: -22, marginTop: -22 }),
        }}
      />
    </>
  );
}
