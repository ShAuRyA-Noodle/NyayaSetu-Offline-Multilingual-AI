import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

interface TextRevealProps {
  children: string;
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'p' | 'span';
  className?: string;
  splitBy?: 'word' | 'char';
  delay?: number;
  stagger?: number;
  duration?: number;
  once?: boolean;
}

export default function TextReveal({
  children,
  as: Tag = 'h2',
  className = '',
  splitBy = 'word',
  delay = 0,
  stagger = 0.05,
  duration = 0.6,
  once = true,
}: TextRevealProps) {
  const containerRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const spans = el.querySelectorAll('.text-reveal-unit');
    gsap.set(spans, { y: '100%', opacity: 0 });

    const tween = gsap.to(spans, {
      y: '0%',
      opacity: 1,
      duration,
      stagger,
      delay,
      ease: 'power3.out',
      scrollTrigger: {
        trigger: el,
        start: 'top 85%',
        once,
        toggleActions: once ? 'play none none none' : 'play reverse play reverse',
      },
    });

    return () => {
      tween.kill();
      ScrollTrigger.getAll().forEach(st => {
        if (st.trigger === el) st.kill();
      });
    };
  }, [children, delay, stagger, duration, once]);

  const units = splitBy === 'word' ? children.split(' ') : children.split('');
  const separator = splitBy === 'word' ? '\u00A0' : '';

  return (
    <Tag ref={containerRef as any} className={`${className}`}>
      {units.map((unit, i) => (
        <span key={i} className="inline-block overflow-hidden">
          <span className="text-reveal-unit inline-block">
            {unit}
            {i < units.length - 1 ? separator : ''}
          </span>
        </span>
      ))}
    </Tag>
  );
}
