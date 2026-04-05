import React, { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import gsap from 'gsap';

interface ThemedButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'saffron' | 'green' | 'outline' | 'ghost' | 'mitti' | 'haldi' | 'neel';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
  loading?: boolean;
  icon?: React.ReactNode;
  magnetic?: boolean;
}

const variantStyles: Record<string, string> = {
  saffron: 'btn-saffron text-white',
  green: 'btn-green text-white',
  mitti: 'btn-mitti text-white',
  haldi: 'btn-haldi text-white',
  neel: 'btn-neel text-white',
  outline: 'border-2 border-mitti-500 text-mitti-600 dark:text-mitti-400 hover:bg-mitti-50 dark:hover:bg-mitti-900/20',
  ghost: 'text-mitti-600 dark:text-mitti-400 hover:bg-mitti-50 dark:hover:bg-mitti-900/20',
};

const sizeStyles: Record<string, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
};

const ThemedButton: React.FC<ThemedButtonProps> = ({
  variant = 'mitti',
  size = 'md',
  children,
  loading = false,
  icon,
  magnetic = false,
  className = '',
  disabled,
  ...props
}) => {
  const magneticRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!magnetic || !magneticRef.current) return;
    const el = magneticRef.current;
    const strength = 0.3;

    const handleMove = (e: MouseEvent) => {
      const rect = el.getBoundingClientRect();
      const x = e.clientX - rect.left - rect.width / 2;
      const y = e.clientY - rect.top - rect.height / 2;
      gsap.to(el, { x: x * strength, y: y * strength, duration: 0.3, ease: 'power2.out' });
    };

    const handleLeave = () => {
      gsap.to(el, { x: 0, y: 0, duration: 0.5, ease: 'elastic.out(1, 0.3)' });
    };

    el.addEventListener('mousemove', handleMove);
    el.addEventListener('mouseleave', handleLeave);
    return () => {
      el.removeEventListener('mousemove', handleMove);
      el.removeEventListener('mouseleave', handleLeave);
    };
  }, [magnetic]);

  return (
    <motion.button
      ref={magnetic ? (magneticRef as any) : undefined}
      whileHover={{ scale: disabled || loading ? 1 : 1.02 }}
      whileTap={{ scale: disabled || loading ? 1 : 0.98 }}
      className={`
        inline-flex items-center justify-center gap-2 rounded-xl font-medium
        transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-mitti-500/40
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variantStyles[variant] || variantStyles.mitti} ${sizeStyles[size]} ${className}
      `}
      disabled={disabled || loading}
      {...(props as any)}
    >
      {loading ? (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ) : icon ? (
        icon
      ) : null}
      {children}
    </motion.button>
  );
};

export default ThemedButton;
