import React, { useEffect, useRef, useState } from 'react';
import { cn } from '../../lib/utils';

/* ---------------- Tabs ---------------- */

export interface TabItem {
  id: string;
  label: React.ReactNode;
  icon?: React.ReactNode;
  count?: number;
  disabled?: boolean;
}

export interface TabsProps {
  items: TabItem[];
  value: string;
  onChange: (id: string) => void;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({ items, value, onChange, className }) => (
  <div className={cn('flex gap-1 overflow-x-auto border-b border-line scrollbar-thin', className)} role="tablist">
    {items.map((t) => {
      const active = t.id === value;
      return (
        <button
          key={t.id}
          role="tab"
          aria-selected={active}
          disabled={t.disabled}
          onClick={() => !t.disabled && onChange(t.id)}
          className={cn(
            'relative flex items-center gap-2 whitespace-nowrap px-4 py-2.5 text-[13px] font-semibold transition-colors focus-ring disabled:opacity-50',
            active ? 'text-brand-600' : 'text-muted hover:text-ink'
          )}
        >
          {t.icon}
          {t.label}
          {typeof t.count === 'number' && (
            <span
              className={cn(
                'rounded-full px-1.5 py-0.5 text-[11px] font-bold',
                active ? 'bg-brand-50 text-brand-600' : 'bg-line-soft text-muted'
              )}
            >
              {t.count}
            </span>
          )}
          {active && (
            <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-brand-gradient" />
          )}
        </button>
      );
    })}
  </div>
);

/* ---------------- Dropdown ---------------- */

export interface DropdownItem {
  label: React.ReactNode;
  onClick?: () => void;
  icon?: React.ReactNode;
  danger?: boolean;
  disabled?: boolean;
  separatorBefore?: boolean;
}

export interface DropdownProps {
  trigger: (props: { open: boolean }) => React.ReactNode;
  items: DropdownItem[];
  align?: 'left' | 'right';
  className?: string;
  header?: React.ReactNode;
  footer?: React.ReactNode;
}

export const Dropdown: React.FC<DropdownProps> = ({
  trigger,
  items,
  align = 'right',
  className,
  header,
  footer,
}) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div ref={ref} className={cn('relative', className)}>
      <div onClick={() => setOpen((v) => !v)}>{trigger({ open })}</div>
      {open && (
        <div
          role="menu"
          className={cn(
            'absolute z-40 mt-2 min-w-[220px] animate-scale-in rounded-xl border border-line bg-surface p-1.5 shadow-popover',
            align === 'right' ? 'right-0' : 'left-0'
          )}
        >
          {header && <div className="border-b border-line-soft px-3 py-2">{header}</div>}
          {items.map((item, i) => (
            <React.Fragment key={i}>
              {item.separatorBefore && <div className="my-1 h-px bg-line-soft" />}
              <button
                role="menuitem"
                disabled={item.disabled}
                onClick={() => {
                  if (item.disabled) return;
                  setOpen(false);
                  item.onClick?.();
                }}
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-[13px] font-medium transition-colors focus-ring disabled:opacity-40',
                  item.danger
                    ? 'text-danger hover:bg-danger-100'
                    : 'text-ink-700 hover:bg-brand-50 hover:text-brand-700'
                )}
              >
                {item.icon}
                {item.label}
              </button>
            </React.Fragment>
          ))}
          {footer && <div className="mt-1 border-t border-line-soft pt-1">{footer}</div>}
        </div>
      )}
    </div>
  );
};

export default Tabs;
