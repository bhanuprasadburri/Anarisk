import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function truncate(str: string, length: number): string {
  if (!str) return '';
  return str.length > length ? str.substring(0, length) + '...' : str;
}

export function getSeverityColor(severity: string | undefined): {
  bg: string;
  text: string;
  border: string;
  badge: string;
  indicator: string;
} {
  switch (severity?.toLowerCase()) {
    case 'critical':
      return {
        bg: 'bg-red-500/10',
        text: 'text-red-400',
        border: 'border-red-500/30',
        badge: 'bg-red-950/80 text-red-300 border-red-700/60',
        indicator: 'bg-red-500',
      };
    case 'high':
      return {
        bg: 'bg-orange-500/10',
        text: 'text-orange-400',
        border: 'border-orange-500/30',
        badge: 'bg-orange-950/80 text-orange-300 border-orange-700/60',
        indicator: 'bg-orange-500',
      };
    case 'medium':
      return {
        bg: 'bg-amber-500/10',
        text: 'text-amber-400',
        border: 'border-amber-500/30',
        badge: 'bg-amber-950/80 text-amber-300 border-amber-700/60',
        indicator: 'bg-amber-500',
      };
    case 'low':
      return {
        bg: 'bg-blue-500/10',
        text: 'text-blue-400',
        border: 'border-blue-500/30',
        badge: 'bg-blue-950/80 text-blue-300 border-blue-700/60',
        indicator: 'bg-blue-500',
      };
    default:
      return {
        bg: 'bg-slate-500/10',
        text: 'text-slate-400',
        border: 'border-slate-500/30',
        badge: 'bg-slate-900 text-slate-400 border-slate-700',
        indicator: 'bg-slate-500',
      };
  }
}

export function getScoreColor(score: number | null | undefined): string {
  if (score === null || score === undefined) return 'text-slate-400';
  if (score >= 0.8) return 'text-red-400';
  if (score >= 0.6) return 'text-orange-400';
  if (score >= 0.4) return 'text-amber-400';
  return 'text-blue-400';
}
