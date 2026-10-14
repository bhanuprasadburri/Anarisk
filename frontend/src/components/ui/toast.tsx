import React, { createContext, useCallback, useContext, useState } from 'react';
import { createPortal } from 'react-dom';
import { CheckCircle2, XCircle, Info, X } from 'lucide-react';
import { cn } from '../../lib/utils';

export type ToastTone = 'success' | 'error' | 'info';

export interface ToastItem {
  id: number;
  tone: ToastTone;
  title: string;
  description?: string;
}

interface ToastContextType {
  toasts: ToastItem[];
  toast: {
    success: (title: string, description?: string) => void;
    error: (title: string, description?: string) => void;
    info: (title: string, description?: string) => void;
  };
  dismiss: (id: number) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

let nextId = 1;

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  const push = useCallback(
    (tone: ToastTone, title: string, description?: string) => {
      const id = nextId++;
      setToasts((t) => [...t.slice(-4), { id, tone, title, description }]);
      setTimeout(() => dismiss(id), tone === 'error' ? 7000 : 4500);
    },
    [dismiss]
  );

  const value: ToastContextType = {
    toasts,
    toast: {
      success: (title, description) => push('success', title, description),
      error: (title, description) => push('error', title, description),
      info: (title, description) => push('info', title, description),
    },
    dismiss,
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} dismiss={dismiss} />
    </ToastContext.Provider>
  );
};

const icons: Record<ToastTone, React.ReactNode> = {
  success: <CheckCircle2 className="text-success" style={{ width: 18, height: 18 }} />,
  error: <XCircle className="text-danger" style={{ width: 18, height: 18 }} />,
  info: <Info className="text-brand-500" style={{ width: 18, height: 18 }} />,
};

const borders: Record<ToastTone, string> = {
  success: 'border-l-success',
  error: 'border-l-danger',
  info: 'border-l-brand-500',
};

const ToastContainer: React.FC<{ toasts: ToastItem[]; dismiss: (id: number) => void }> = ({
  toasts,
  dismiss,
}) => {
  if (toasts.length === 0) return null;
  return createPortal(
    <div
      aria-live="polite"
      className="pointer-events-none fixed bottom-5 right-5 z-[60] flex w-full max-w-sm flex-col gap-2.5"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          className={cn(
            'pointer-events-auto flex items-start gap-3 rounded-xl border border-line border-l-4 bg-surface p-3.5 shadow-popover animate-fade-in',
            borders[t.tone]
          )}
        >
          <div className="mt-0.5 shrink-0">{icons[t.tone]}</div>
          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-bold text-ink">{t.title}</p>
            {t.description && <p className="mt-0.5 text-xs leading-relaxed text-muted">{t.description}</p>}
          </div>
          <button
            onClick={() => dismiss(t.id)}
            aria-label="Dismiss notification"
            className="shrink-0 rounded p-1 text-faint transition-colors hover:bg-line-soft hover:text-ink"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
    </div>,
    document.body
  );
};

export const useToast = (): ToastContextType => {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within a ToastProvider');
  return ctx;
};
