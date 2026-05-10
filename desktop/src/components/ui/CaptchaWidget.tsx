import React, { useEffect, useRef, useState } from 'react';
import { ShieldCheck, AlertCircle } from 'lucide-react';
import captchaService from '../../services/captcha';

declare global {
  interface Window {
    turnstile?: {
      render: (
        el: HTMLElement,
        opts: {
          sitekey: string;
          theme?: 'light' | 'dark' | 'auto';
          callback?: (token: string) => void;
          'error-callback'?: () => void;
          'expired-callback'?: () => void;
          appearance?: 'always' | 'execute' | 'interaction-only';
        }
      ) => string;
      reset: (id?: string) => void;
      remove: (id?: string) => void;
    };
  }
}

interface CaptchaWidgetProps {
  onVerify: (token: string) => void;
  onError?: () => void;
}

const TURNSTILE_SCRIPT = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';

let scriptLoadPromise: Promise<void> | null = null;
function loadTurnstileScript(): Promise<void> {
  if (typeof window === 'undefined') return Promise.reject(new Error('SSR'));
  if (window.turnstile) return Promise.resolve();
  if (scriptLoadPromise) return scriptLoadPromise;

  scriptLoadPromise = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src^="${TURNSTILE_SCRIPT.split('?')[0]}"]`);
    if (existing) {
      existing.addEventListener('load', () => resolve());
      existing.addEventListener('error', () => reject(new Error('Turnstile script failed to load')));
      return;
    }
    const s = document.createElement('script');
    s.src = TURNSTILE_SCRIPT;
    s.async = true;
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error('Turnstile script failed to load'));
    document.head.appendChild(s);
  });
  return scriptLoadPromise;
}

const CaptchaWidget: React.FC<CaptchaWidgetProps> = ({ onVerify, onError }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const siteKey = import.meta.env.VITE_TURNSTILE_SITE_KEY as string | undefined;

  // Dev-mode bypass: no site key configured → emit a placeholder token.
  useEffect(() => {
    if (!siteKey) {
      const devToken = 'dev-skip';
      captchaService.setToken(devToken);
      onVerify(devToken);
    }
    return () => captchaService.clear();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteKey]);

  useEffect(() => {
    if (!siteKey) return;
    let cancelled = false;

    loadTurnstileScript()
      .then(() => {
        if (cancelled || !containerRef.current || !window.turnstile) return;
        try {
          widgetIdRef.current = window.turnstile.render(containerRef.current, {
            sitekey: siteKey,
            theme: 'dark',
            callback: (token: string) => {
              setError(null);
              captchaService.setToken(token);
              onVerify(token);
            },
            'error-callback': () => {
              setError('Captcha verification failed. Please try again.');
              captchaService.clear();
              onError?.();
            },
            'expired-callback': () => {
              captchaService.clear();
              setError('Captcha expired — please re-verify.');
            },
          });
        } catch (e) {
          setError('Could not load captcha. Please refresh.');
          onError?.();
        }
      })
      .catch(() => {
        setError('Could not load captcha service. Check your connection.');
        onError?.();
      });

    return () => {
      cancelled = true;
      if (window.turnstile && widgetIdRef.current) {
        try { window.turnstile.remove(widgetIdRef.current); } catch { /* noop */ }
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteKey]);

  if (!siteKey) {
    return (
      <div className="rounded-xl border border-amber-500/20 bg-amber-500/[0.06] p-3 flex items-start gap-2.5">
        <ShieldCheck className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
        <div className="min-w-0">
          <p className="text-xs font-semibold text-amber-300">DEV MODE — captcha skipped</p>
          <p className="text-[11px] text-amber-200/70 mt-0.5">
            Set <code className="font-mono">VITE_TURNSTILE_SITE_KEY</code> in your <code className="font-mono">.env</code> to enable Cloudflare Turnstile.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div ref={containerRef} className="cf-turnstile" />
      {error && (
        <div className="flex items-start gap-2 text-xs text-[#F95454]">
          <AlertCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
};

export default CaptchaWidget;
