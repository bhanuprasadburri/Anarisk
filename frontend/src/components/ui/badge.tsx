import React from 'react';
import { cn } from '../../lib/utils';

export type BadgeTone =
  | 'default'
  | 'primary'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'violet'
  | 'outline';

const tones: Record<BadgeTone, string> = {
  default: 'bg-line-soft text-muted border-line',
  primary: 'bg-brand-50 text-brand-700 border-brand-100',
  success: 'bg-success-100 text-success-600 border-success-100',
  warning: 'bg-warning-100 text-warning-600 border-warning-100',
  danger: 'bg-danger-100 text-danger-600 border-danger-100',
  info: 'bg-cyanx-100 text-cyanx-600 border-cyanx-100',
  violet: 'bg-violet-100 text-violet-600 border-violet-200',
  outline: 'bg-white text-ink-700 border-line',
};

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({ tone = 'default', dot, className, children, ...props }) => (
  <span
    className={cn(
      'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold',
      tones[tone],
      className
    )}
    {...props}
  >
    {dot && <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />}
    {children}
  </span>
);

const SEVERITY_TONE: Record<string, BadgeTone> = {
  critical: 'danger',
  high: 'danger',
  medium: 'warning',
  low: 'success',
  unknown: 'default',
};

const SEVERITY_DOT: Record<string, string> = {
  critical: 'bg-[#E11D48]',
  high: 'bg-danger',
  medium: 'bg-warning',
  low: 'bg-success',
  unknown: 'bg-faint',
};

export const SeverityBadge: React.FC<{ severity?: string | null; className?: string }> = ({
  severity,
  className,
}) => {
  const sev = (severity || 'unknown').toLowerCase();
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold capitalize',
        tones[SEVERITY_TONE[sev] || 'default'],
        className
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', SEVERITY_DOT[sev] || 'bg-faint')} />
      {sev}
    </span>
  );
};

const CASE_STATUS_TONE: Record<string, BadgeTone> = {
  detected: 'info',
  triaged: 'primary',
  under_review: 'violet',
  assigned: 'primary',
  escalated: 'danger',
  resolved: 'success',
};

export const CaseStatusBadge: React.FC<{ status?: string | null; className?: string }> = ({
  status,
  className,
}) => {
  const s = (status || 'detected').toLowerCase().replace(/\s+/g, '_');
  const label = s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <Badge tone={CASE_STATUS_TONE[s] || 'default'} className={className}>
      {label}
    </Badge>
  );
};

const PROVENANCE_TONE: Record<string, BadgeTone> = {
  collected: 'success',
  manual: 'primary',
  synthetic: 'warning',
};

export const ProvenanceBadge: React.FC<{ provenance?: string | null; className?: string }> = ({
  provenance,
  className,
}) => {
  const p = (provenance || 'manual').toLowerCase();
  const label = p === 'synthetic' ? 'Sample data' : p.charAt(0).toUpperCase() + p.slice(1);
  return (
    <Badge tone={PROVENANCE_TONE[p] || 'default'} className={className} title={
      p === 'synthetic'
        ? 'Synthetic demo data generated for evaluation — not a live threat'
        : p === 'collected'
        ? 'Ingested automatically by a collection connector'
        : 'Manually submitted by an analyst'
    }>
      {label}
    </Badge>
  );
};

export default Badge;
