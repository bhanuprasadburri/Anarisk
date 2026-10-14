import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function truncate(str: string | null | undefined, length: number): string {
  if (!str) return '';
  return str.length > length ? str.substring(0, length) + '…' : str;
}

/** Tailwind classes for a severity value (badge-style soft background). */
export function severityClasses(severity: string | null | undefined): string {
  switch ((severity || 'unknown').toLowerCase()) {
    case 'critical':
      return 'bg-[#FCE7EF] text-[#E11D48]';
    case 'high':
      return 'bg-danger-100 text-danger-600';
    case 'medium':
      return 'bg-warning-100 text-warning-600';
    case 'low':
      return 'bg-success-100 text-success-600';
    default:
      return 'bg-line-soft text-muted';
  }
}

export function severityText(severity: string | null | undefined): string {
  switch ((severity || 'unknown').toLowerCase()) {
    case 'critical':
      return 'text-[#E11D48]';
    case 'high':
      return 'text-danger-500';
    case 'medium':
      return 'text-warning-500';
    case 'low':
      return 'text-success-500';
    default:
      return 'text-muted';
  }
}

export function scoreTextClass(score: number | null | undefined): string {
  if (score === null || score === undefined) return 'text-muted';
  if (score >= 0.8) return 'text-[#E11D48]';
  if (score >= 0.6) return 'text-danger-500';
  if (score >= 0.4) return 'text-warning-500';
  return 'text-success-500';
}

export function severityOfScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return 'unknown';
  if (score >= 0.8) return 'critical';
  if (score >= 0.6) return 'high';
  if (score >= 0.4) return 'medium';
  return 'low';
}

/** Domain of an entity's "channel" for reports (grouped as Social / Web / App / Image). */
export function channelOfEntity(entityType: string): string {
  switch (entityType) {
    case 'social_profile':
      return 'Social';
    case 'website':
    case 'domain':
      return 'Web';
    case 'mobile_app':
      return 'App';
    case 'image':
      return 'Image';
    default:
      return 'Other';
  }
}
