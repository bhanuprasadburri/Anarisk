import { format, formatDistanceToNow, parseISO } from 'date-fns';

export function formatDate(dateStr: string | Date | null | undefined): string {
  if (!dateStr) return '—';
  try {
    const d = typeof dateStr === 'string' ? parseISO(dateStr) : dateStr;
    return format(d, 'MMM d, yyyy HH:mm');
  } catch {
    return String(dateStr);
  }
}

export function formatRelativeTime(dateStr: string | Date | null | undefined): string {
  if (!dateStr) return '—';
  try {
    const d = typeof dateStr === 'string' ? parseISO(dateStr) : dateStr;
    return formatDistanceToNow(d, { addSuffix: true });
  } catch {
    return String(dateStr);
  }
}

export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return 'N/A';
  return (score * 100).toFixed(0) + '%';
}

export function formatDecimalScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return 'N/A';
  return score.toFixed(2);
}

export function formatNumber(num: number | null | undefined): string {
  if (num === null || num === undefined) return '0';
  return new Intl.NumberFormat().format(num);
}
