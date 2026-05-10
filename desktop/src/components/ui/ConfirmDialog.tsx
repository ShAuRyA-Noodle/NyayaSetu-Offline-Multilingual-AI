import React, { useState, useCallback, useRef } from 'react';
import { AlertTriangle, Info, X } from 'lucide-react';
import AnimatedModal from './AnimatedModal';

/* ============================================================
   ConfirmDialog — themed replacement for native confirm() / prompt()
   ============================================================
   Usage:
     const { confirm, prompt, ConfirmHost } = useDialog();
     const ok = await confirm({ title, message, tone: 'danger' });
     const value = await prompt({ title, message, placeholder });
     // mount <ConfirmHost /> once at the page root
   ============================================================ */

export type DialogTone = 'info' | 'warning' | 'danger';

export interface ConfirmOptions {
  title: string;
  message?: string;
  confirmText?: string;
  cancelText?: string;
  tone?: DialogTone;
}

export interface PromptOptions extends ConfirmOptions {
  placeholder?: string;
  defaultValue?: string;
  multiline?: boolean;
  required?: boolean;
}

type DialogState =
  | { kind: 'confirm'; options: ConfirmOptions; resolve: (v: boolean) => void }
  | { kind: 'prompt'; options: PromptOptions; resolve: (v: string | null) => void }
  | null;

const toneStyles: Record<DialogTone, { ring: string; icon: string; btn: string }> = {
  info:    { ring: 'border-[#0D92F4]/25', icon: 'text-[#77CDFF]', btn: 'bg-[#0D92F4] hover:bg-[#0a7ed6]' },
  warning: { ring: 'border-amber-500/25', icon: 'text-amber-400',  btn: 'bg-amber-600 hover:bg-amber-700' },
  danger:  { ring: 'border-[#F95454]/30', icon: 'text-[#F95454]',  btn: 'bg-[#C62E2E] hover:bg-[#a62525]' },
};

export function useDialog() {
  const [state, setState] = useState<DialogState>(null);
  const [inputValue, setInputValue] = useState('');
  const inputRef = useRef<HTMLTextAreaElement | HTMLInputElement | null>(null);

  const confirm = useCallback((options: ConfirmOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      setState({ kind: 'confirm', options, resolve });
    });
  }, []);

  const prompt = useCallback((options: PromptOptions): Promise<string | null> => {
    setInputValue(options.defaultValue || '');
    return new Promise((resolve) => {
      setState({ kind: 'prompt', options, resolve });
    });
  }, []);

  const close = useCallback(
    (result: boolean | string | null) => {
      if (!state) return;
      if (state.kind === 'confirm') (state.resolve as (v: boolean) => void)(result === true);
      else (state.resolve as (v: string | null) => void)(result as string | null);
      setState(null);
      setInputValue('');
    },
    [state]
  );

  const ConfirmHost: React.FC = () => {
    if (!state) return null;
    const { options } = state;
    const tone = options.tone || (state.kind === 'prompt' ? 'info' : 'warning');
    const ts = toneStyles[tone];

    const Icon = tone === 'info' ? Info : AlertTriangle;
    const isPrompt = state.kind === 'prompt';
    const promptOpts = isPrompt ? (options as PromptOptions) : null;

    const onSubmit = () => {
      if (isPrompt) {
        if (promptOpts?.required && !inputValue.trim()) return;
        close(inputValue);
      } else {
        close(true);
      }
    };

    return (
      <AnimatedModal isOpen={true} onClose={() => close(isPrompt ? null : false)} maxWidth="max-w-md">
        <div
          className={`village-card rounded-2xl shadow-2xl overflow-hidden border ${ts.ring}`}
          role="dialog"
          aria-modal="true"
          aria-labelledby="dialog-title"
        >
          <div className="p-5 sm:p-6">
            <div className="flex items-start gap-4">
              <div className={`flex-shrink-0 w-10 h-10 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center`}>
                <Icon className={`w-5 h-5 ${ts.icon}`} />
              </div>
              <div className="flex-1 min-w-0">
                <h3 id="dialog-title" className="text-base font-semibold text-kora-100 mb-1 leading-snug">
                  {options.title}
                </h3>
                {options.message && (
                  <p className="text-sm text-slate-400 leading-relaxed">{options.message}</p>
                )}
              </div>
              <button
                type="button"
                onClick={() => close(isPrompt ? null : false)}
                className="flex-shrink-0 p-1.5 -mt-1 -mr-1 rounded-lg hover:bg-white/[0.06] text-slate-500 hover:text-slate-300 transition-colors"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {isPrompt && (
              <div className="mt-4">
                {promptOpts?.multiline ? (
                  <textarea
                    ref={inputRef as React.Ref<HTMLTextAreaElement>}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder={promptOpts.placeholder}
                    rows={4}
                    autoFocus
                    className="village-input w-full px-3 py-2 rounded-lg text-sm text-kora-100 resize-y"
                  />
                ) : (
                  <input
                    ref={inputRef as React.Ref<HTMLInputElement>}
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder={promptOpts?.placeholder}
                    autoFocus
                    onKeyDown={(e) => { if (e.key === 'Enter') onSubmit(); }}
                    className="village-input w-full px-3 py-2 rounded-lg text-sm text-kora-100"
                  />
                )}
              </div>
            )}
          </div>

          <div className="border-t border-white/[0.06] bg-white/[0.02] p-3 flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => close(isPrompt ? null : false)}
              className="px-4 py-2 rounded-lg text-sm font-medium text-slate-300 hover:text-slate-100 hover:bg-white/[0.06] transition-colors"
            >
              {options.cancelText || 'Cancel'}
            </button>
            <button
              type="button"
              onClick={onSubmit}
              disabled={isPrompt && promptOpts?.required && !inputValue.trim()}
              className={`px-4 py-2 rounded-lg text-sm font-semibold text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${ts.btn}`}
            >
              {options.confirmText || (isPrompt ? 'Submit' : 'Confirm')}
            </button>
          </div>
        </div>
      </AnimatedModal>
    );
  };

  return { confirm, prompt, ConfirmHost };
}

export default useDialog;
