import * as React from 'react';
import { cn } from '../../lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline' | 'teal' | 'critical' | 'high' | 'medium' | 'low';
}

function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  const variants = {
    default: 'border-transparent bg-slate-800 text-slate-100',
    secondary: 'border-transparent bg-slate-800/80 text-slate-300',
    destructive: 'border-transparent bg-red-900/60 text-red-200 border-red-700/50',
    outline: 'text-slate-300 border-slate-700',
    teal: 'border-teal-500/30 bg-teal-950/70 text-teal-300',
    critical: 'border-red-500/40 bg-red-950/80 text-red-300',
    high: 'border-orange-500/40 bg-orange-950/80 text-orange-300',
    medium: 'border-amber-500/40 bg-amber-950/80 text-amber-300',
    low: 'border-blue-500/40 bg-blue-950/80 text-blue-300',
  };

  return (
    <div
      className={cn(
        'inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold tracking-wide transition-colors focus:outline-none',
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

export { Badge };
