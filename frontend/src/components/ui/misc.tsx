import React, { useEffect, useRef, useState } from 'react';
import { Search, X, Copy, Check, ChevronDown } from 'lucide-react';
import { cn } from '../../lib/utils';
import { inputBase } from './input';

/* ---------------- Skeleton ---------------- */

export const Skeleton: React.FC<{ className?: string }> = ({ className }) => (
  <div className={cn('skeleton rounded-md', className)} />
);

export const TableSkeleton: React.FC<{ rows?: number }> = ({ rows = 6 }) => (
  <div className="space-y-3 p-5">
    {Array.from({ length: rows }).map((_, i) => (
      <Skeleton key={i} className="h-10 w-full" />
    ))}
  </div>
);

export const CardSkeleton: React.FC<{ className?: string }> = ({ className }) => (
  <div className={cn('rounded-2xl border border-line bg-surface p-5', className)}>
    <Skeleton className="h-4 w-32" />
    <Skeleton className="mt-4 h-8 w-24" />
    <Skeleton className="mt-3 h-3 w-40" />
  </div>
);

/* ---------------- Spinner ---------------- */

export const Spinner: React.FC<{ className?: string }> = ({ className }) => (
  <div
    className={cn(
      'h-5 w-5 animate-spin rounded-full border-2 border-brand-200 border-t-brand-500',
      className
    )}
    role="status"
    aria-label="Loading"
  />
);

/* ---------------- Page loading (full block) ---------------- */

export const LoadingBlock: React.FC<{ label?: string }> = ({ label = 'Loading…' }) => (
  <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3">
    <Spinner className="h-7 w-7" />
    <p className="text-[13px] font-medium text-muted">{label}</p>
  </div>
);

/* ---------------- SearchInput ---------------- */

export interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  autoFocus?: boolean;
  debounceMs?: number;
}

export const SearchInput: React.FC<SearchInputProps> = ({
  value,
  onChange,
  placeholder = 'Search…',
  className,
  autoFocus,
  debounceMs = 0,
}) => {
  const [local, setLocal] = useState(value);
  const timer = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => setLocal(value), [value]);
  useEffect(() => () => timer.current && clearTimeout(timer.current), []);

  const emit = (v: string) => {
    if (debounceMs > 0) {
      clearTimeout(timer.current);
      timer.current = setTimeout(() => onChange(v), debounceMs);
    } else {
      onChange(v);
    }
  };

  return (
    <div className={cn('relative', className)}>
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
      <input
        type="search"
        value={local}
        autoFocus={autoFocus}
        onChange={(e) => {
          setLocal(e.target.value);
          emit(e.target.value);
        }}
        placeholder={placeholder}
        aria-label={placeholder}
        className={cn(inputBase, 'h-10 pl-9 pr-9 [&::-webkit-search-cancel-button]:hidden')}
      />
      {local && (
        <button
          onClick={() => {
            setLocal('');
            emit('');
          }}
          aria-label="Clear search"
          className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded p-1 text-faint hover:bg-line-soft hover:text-ink"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
};

/* ---------------- FilterSelect ---------------- */

export interface FilterSelectProps {
  value: string;
  onChange: (v: string) => void;
  options: Array<{ value: string; label: string }>;
  label?: string;
  className?: string;
  allLabel?: string;
}

export const FilterSelect: React.FC<FilterSelectProps> = ({
  value,
  onChange,
  options,
  label,
  className,
  allLabel = 'All',
}) => (
  <label className={cn('relative inline-block', className)}>
    {label && <span className="sr-only">{label}</span>}
    <select
      aria-label={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={cn(
        inputBase,
        'h-9 cursor-pointer appearance-none py-1.5 pl-3 pr-8 text-[13px] font-semibold',
        value ? 'border-brand-200 bg-brand-50 text-brand-700' : 'bg-white text-ink-700'
      )}
      style={{ height: '2.375rem' }}
    >
      <option value="">{allLabel}</option>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
    <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 opacity-60" />
  </label>
);

/* ---------------- DateRangeSelect ---------------- */

export type RangeKey = '24h' | '7d' | '30d' | '90d' | 'custom';

export interface DateRangeValue {
  key: RangeKey;
  from?: string; // yyyy-mm-dd
  to?: string;
}

export const RANGE_LABELS: Record<Exclude<RangeKey, 'custom'>, string> = {
  '24h': 'Last 24 hours',
  '7d': 'Last 7 days',
  '30d': 'Last 30 days',
  '90d': 'Last 90 days',
};

export function rangeToDates(range: DateRangeValue): { from?: string; to?: string } {
  if (range.key === 'custom') return { from: range.from, to: range.to };
  const now = new Date();
  const days = range.key === '24h' ? 1 : range.key === '7d' ? 7 : range.key === '30d' ? 30 : 90;
  const from = new Date(now.getTime() - (days - 1) * 24 * 3600 * 1000);
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return { from: iso(from), to: iso(now) };
}

export const DateRangeSelect: React.FC<{
  value: DateRangeValue;
  onChange: (v: DateRangeValue) => void;
  className?: string;
}> = ({ value, onChange, className }) => {
  const [open, setOpen] = useState(false);
  const [custom, setCustom] = useState<{ from: string; to: string }>({
    from: value.from || '',
    to: value.to || '',
  });
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  const label =
    value.key === 'custom'
      ? `${value.from || '…'} → ${value.to || '…'}`
      : RANGE_LABELS[value.key];

  return (
    <div ref={ref} className={cn('relative', className)}>
      <button
        onClick={() => setOpen((v) => !v)}
        className={cn(
          'inline-flex h-9.5 items-center gap-2 whitespace-nowrap rounded-xl border border-line bg-white px-3.5 text-[13px] font-semibold text-ink-700 shadow-sm transition-colors hover:border-brand-200 focus-ring',
          className
        )}
        style={{ height: '2.375rem' }}
        aria-haspopup="dialog"
        aria-expanded={open}
      >
        <svg className="h-3.5 w-3.5 text-brand-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="4" width="18" height="18" rx="2" />
          <path d="M16 2v4M8 2v4M3 10h18" />
        </svg>
        {label}
        <ChevronDown className="h-3.5 w-3.5 text-faint" />
      </button>
      {open && (
        <div className="absolute right-0 z-40 mt-2 w-64 animate-scale-in rounded-xl border border-line bg-surface p-2 shadow-popover">
          {(Object.keys(RANGE_LABELS) as Array<Exclude<RangeKey, 'custom'>>).map((k) => (
            <button
              key={k}
              onClick={() => {
                onChange({ key: k });
                setOpen(false);
              }}
              className={cn(
                'flex w-full items-center justify-between rounded-lg px-3 py-2 text-[13px] font-semibold transition-colors',
                value.key === k ? 'bg-brand-50 text-brand-700' : 'text-ink-700 hover:bg-line-soft'
              )}
            >
              {RANGE_LABELS[k]}
              {value.key === k && <Check className="h-3.5 w-3.5" />}
            </button>
          ))}
          <div className="mt-1 border-t border-line-soft px-2 pb-1 pt-2">
            <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-faint">Custom range</p>
            <div className="space-y-2">
              <input
                type="date"
                aria-label="From date"
                value={custom.from}
                onChange={(e) => setCustom((c) => ({ ...c, from: e.target.value }))}
                className={cn(inputBase, 'h-9 text-[13px]')}
              />
              <input
                type="date"
                aria-label="To date"
                value={custom.to}
                onChange={(e) => setCustom((c) => ({ ...c, to: e.target.value }))}
                className={cn(inputBase, 'h-9 text-[13px]')}
              />
              <button
                onClick={() => {
                  if (custom.from && custom.to) {
                    onChange({ key: 'custom', ...custom });
                    setOpen(false);
                  }
                }}
                disabled={!custom.from || !custom.to}
                className="w-full rounded-lg bg-brand-gradient px-3 py-1.5 text-[13px] font-semibold text-white disabled:opacity-50"
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

/* ---------------- CopyButton ---------------- */

export const CopyButton: React.FC<{ text: string; className?: string; label?: string }> = ({
  text,
  className,
  label,
}) => {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        });
      }}
      title={label || 'Copy'}
      aria-label={label || 'Copy to clipboard'}
      className={cn('rounded-md p-1 text-faint transition-colors hover:bg-line-soft hover:text-brand-600', className)}
    >
      {copied ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
};

/* ---------------- Tooltip (hover) ---------------- */

export const Tooltip: React.FC<{ content: React.ReactNode; children: React.ReactNode; className?: string }> = ({
  content,
  children,
  className,
}) => (
  <span className={cn('group/tooltip relative inline-flex', className)}>
    {children}
    <span className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-1.5 -translate-x-1/2 whitespace-nowrap rounded-lg bg-ink px-2.5 py-1.5 text-[11px] font-medium text-white opacity-0 shadow-popover transition-opacity group-hover/tooltip:opacity-100">
      {content}
    </span>
  </span>
);

/* ---------------- Avatar ---------------- */

export const Avatar: React.FC<{ name?: string; src?: string | null; size?: number; className?: string }> = ({
  name,
  src,
  size = 32,
  className,
}) => {
  const initials = (name || '?')
    .split(' ')
    .map((p) => p[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase();
  return src ? (
    <img
      src={src}
      alt={name || 'Avatar'}
      width={size}
      height={size}
      className={cn('rounded-full object-cover', className)}
      style={{ width: size, height: size }}
    />
  ) : (
    <span
      className={cn('inline-flex items-center justify-center rounded-full bg-brand-gradient font-bold text-white', className)}
      style={{ width: size, height: size, fontSize: size * 0.38 }}
      aria-label={name}
    >
      {initials}
    </span>
  );
};

/* ---------------- KeyValue ---------------- */

export const KeyValue: React.FC<{
  label: React.ReactNode;
  value: React.ReactNode;
  className?: string;
}> = ({ label, value, className }) => (
  <div className={cn('py-2.5', className)}>
    <dt className="text-[11px] font-bold uppercase tracking-wider text-faint">{label}</dt>
    <dd className="mt-1 text-[13px] font-medium text-ink">{value}</dd>
  </div>
);
