import * as React from 'react';
import { cn } from '../../lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link' | 'teal';
  size?: 'default' | 'sm' | 'lg' | 'icon';
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => {
    const base = 'inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-teal-400 disabled:pointer-events-none disabled:opacity-50 cursor-pointer';

    const variants = {
      default: 'bg-teal-600 text-white shadow hover:bg-teal-500 active:bg-teal-700',
      destructive: 'bg-red-600 text-white shadow-sm hover:bg-red-500 active:bg-red-700',
      outline: 'border border-slate-700 bg-slate-900/50 text-slate-200 shadow-sm hover:bg-slate-800 hover:text-white hover:border-slate-600',
      secondary: 'bg-slate-800 text-slate-100 shadow-sm hover:bg-slate-700',
      ghost: 'text-slate-300 hover:bg-slate-800 hover:text-white',
      link: 'text-teal-400 underline-offset-4 hover:underline p-0 h-auto',
      teal: 'bg-gradient-to-r from-teal-500 to-cyan-500 text-slate-950 font-semibold shadow hover:from-teal-400 hover:to-cyan-400',
    };

    const sizes = {
      default: 'h-9 px-4 py-2',
      sm: 'h-8 rounded-md px-3 text-xs',
      lg: 'h-10 rounded-md px-8 text-base',
      icon: 'h-9 w-9 p-0',
    };

    return (
      <button
        className={cn(base, variants[variant], sizes[size], className)}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';

export { Button };
