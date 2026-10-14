import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';

type Variant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success' | 'link';
type Size = 'sm' | 'md' | 'lg' | 'icon';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: React.ReactNode;
}

const variants: Record<Variant, string> = {
  primary:
    'bg-brand-gradient text-white shadow-sm hover:brightness-110 active:brightness-100 disabled:opacity-60',
  secondary:
    'bg-brand-50 text-brand-700 hover:bg-brand-100 disabled:opacity-60 border border-brand-100',
  outline:
    'bg-white text-ink-700 border border-line hover:bg-bg hover:border-brand-200 disabled:opacity-50 shadow-sm',
  ghost: 'text-muted hover:bg-line-soft hover:text-ink disabled:opacity-50',
  danger: 'bg-danger text-white hover:bg-danger-600 disabled:opacity-60 shadow-sm',
  success: 'bg-success text-white hover:bg-success-600 disabled:opacity-60 shadow-sm',
  link: 'text-brand-600 hover:text-brand-700 underline-offset-2 hover:underline p-0',
};

const sizes: Record<Size, string> = {
  sm: 'h-8 px-3 text-[13px] gap-1.5 rounded-lg',
  md: 'h-10 px-4 text-sm gap-2 rounded-xl',
  lg: 'h-11 px-6 text-sm gap-2 rounded-xl',
  icon: 'h-9 w-9 rounded-lg',
};

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  className,
  children,
  disabled,
  ...props
}) => {
  return (
    <button
      className={cn(
        'inline-flex select-none items-center justify-center font-semibold transition-all duration-150 focus-ring disabled:cursor-not-allowed',
        variants[variant],
        sizes[size],
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        icon
      )}
      {children}
    </button>
  );
};

export default Button;
