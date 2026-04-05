import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

type AnimationType = 'fadeUp' | 'fadeIn' | 'slideLeft' | 'slideRight' | 'scaleIn' | 'stagger';

interface ScrollAnimationOptions {
  type?: AnimationType;
  delay?: number;
  duration?: number;
  staggerAmount?: number;
  start?: string;
  once?: boolean;
}

export function useScrollAnimation<T extends HTMLElement>(options: ScrollAnimationOptions = {}) {
  const ref = useRef<T>(null);
  const {
    type = 'fadeUp',
    delay = 0,
    duration = 0.8,
    staggerAmount = 0.12,
    start = 'top 85%',
    once = true,
  } = options;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const toggleActions = once ? 'play none none none' : 'play reverse play reverse';

    if (type === 'stagger') {
      gsap.set(el.children, { opacity: 0, y: 30 });
      const tween = gsap.to(el.children, {
        opacity: 1,
        y: 0,
        duration,
        stagger: staggerAmount,
        ease: 'power3.out',
        delay,
        scrollTrigger: { trigger: el, start, once, toggleActions },
      });
      return () => {
        tween.kill();
        ScrollTrigger.getAll().forEach(st => {
          if (st.trigger === el) st.kill();
        });
      };
    }

    const fromVars: gsap.TweenVars = { opacity: 0 };
    const toVars: gsap.TweenVars = { opacity: 1, duration, delay, ease: 'power3.out' };

    switch (type) {
      case 'fadeUp': fromVars.y = 40; toVars.y = 0; break;
      case 'fadeIn': break;
      case 'slideLeft': fromVars.x = -60; toVars.x = 0; break;
      case 'slideRight': fromVars.x = 60; toVars.x = 0; break;
      case 'scaleIn': fromVars.scale = 0.9; toVars.scale = 1; break;
    }

    gsap.set(el, fromVars);
    const tween = gsap.to(el, {
      ...toVars,
      scrollTrigger: { trigger: el, start, once, toggleActions },
    });

    return () => {
      tween.kill();
      ScrollTrigger.getAll().forEach(st => {
        if (st.trigger === el) st.kill();
      });
    };
  }, [type, delay, duration, staggerAmount, start, once]);

  return ref;
}
