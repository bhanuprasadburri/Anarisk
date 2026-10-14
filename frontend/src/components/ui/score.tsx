import React from 'react';
import { cn } from '../../lib/utils';
import { Skeleton } from './misc';

export function severityColor(severity?: string | null): string {
  switch ((severity || 'unknown').toLowerCase()) {
    case 'critical':
      return '#E11D48';
    case 'high':
      return '#F04464';
    case 'medium':
      return '#F59E0B';
    case 'low':
      return '#10B981';
    default:
      return '#94A3B8';
  }
}

export function scoreSeverity(score: number | null | undefined): string {
  if (score === null || score === undefined) return 'unknown';
  if (score >= 0.8) return 'critical';
  if (score >= 0.6) return 'high';
  if (score >= 0.4) return 'medium';
  return 'low';
}

/* ---------------- ScoreRing ---------------- */

export interface ScoreRingProps {
  value: number | null | undefined; // 0..1
  label?: string;
  sublabel?: string;
  size?: number;
  thickness?: number;
  severity?: string; // overrides color derivation
  className?: string;
}

export const ScoreRing: React.FC<ScoreRingProps> = ({
  value,
  label,
  sublabel,
  size = 88,
  thickness = 8,
  severity,
  className,
}) => {
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  const pct = value === null || value === undefined ? 0 : Math.max(0, Math.min(1, value));
  const color = severityColor(severity || scoreSeverity(value));

  return (
    <div className={cn('relative inline-flex flex-col items-center', className)} style={{ width: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#EDF2FC" strokeWidth={thickness} />
        {value !== null && value !== undefined && (
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={thickness}
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={c * (1 - pct)}
            style={{ transition: 'stroke-dashoffset 0.6s ease' }}
          />
        )}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-bold tracking-tight text-ink" style={{ fontSize: size * 0.24 }}>
          {value === null || value === undefined ? '—' : value.toFixed(2)}
        </span>
        {sublabel && (
          <span className="text-[10px] font-semibold uppercase tracking-wide text-faint">{sublabel}</span>
        )}
      </div>
      {label && <span className="mt-2 text-[11px] font-bold uppercase tracking-wider text-faint">{label}</span>}
    </div>
  );
};

/* ---------------- ScoreBar ---------------- */

export const ScoreBar: React.FC<{
  value: number | null | undefined;
  severity?: string;
  className?: string;
  showLabel?: boolean;
}> = ({ value, severity, className, showLabel = true }) => {
  const pct = value === null || value === undefined ? 0 : Math.max(0, Math.min(1, value)) * 100;
  const color = severityColor(severity || scoreSeverity(value));
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="h-1.5 min-w-[64px] flex-1 overflow-hidden rounded-full bg-line-soft">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      {showLabel && (
        <span className="w-9 text-right text-[12px] font-bold tabular-nums" style={{ color }}>
          {value === null || value === undefined ? '—' : value.toFixed(2)}
        </span>
      )}
    </div>
  );
};

/* ---------------- MetricCard ---------------- */

export const DeltaBadge: React.FC<{ value: number | null | undefined; invert?: boolean }> = ({
  value,
  invert,
}) => {
  if (value === null || value === undefined || !isFinite(value)) return null;
  const positive = value >= 0;
  const good = invert ? !positive : positive;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[11px] font-bold',
        good ? 'bg-success-100 text-success-600' : 'bg-danger-100 text-danger-600'
      )}
    >
      {positive ? '↑' : '↓'} {Math.abs(value).toFixed(Math.abs(value) < 10 ? 0 : 0)}%
    </span>
  );
};
