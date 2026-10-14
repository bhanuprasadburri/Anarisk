import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, CheckCheck, BellOff } from 'lucide-react';
import { notificationService } from '../../services/notificationService';
import { NotificationItem } from '../../types';
import { cn } from '../../lib/utils';
import { formatRelativeTime } from '../../lib/formatters';

const TYPE_ICONS: Record<string, string> = {
  high_risk_detection: '🚨',
  case_assigned: '👤',
  case_escalated: '🔺',
  case_created: '📁',
  case_status: '🔄',
  case_resolved: '✅',
  evidence_added: '📎',
  integration_sync: '🔌',
};

export const notificationsPopover = () => {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await notificationService.list({ page_size: 8 });
      setItems(res.items || []);
      setUnread(res.unread_count || 0);
    } catch {
      // keep previous state
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  const markAllRead = async () => {
    try {
      const res = await notificationService.markRead();
      setUnread(res.unread_count);
      setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      /* ignore */
    }
  };

  const onItemClick = async (n: NotificationItem) => {
    setOpen(false);
    if (!n.is_read) {
      try {
        const res = await notificationService.markRead([n.id]);
        setUnread(res.unread_count);
        setItems((prev) => prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)));
      } catch {
        /* ignore */
      }
    }
    if (n.link_url) navigate(n.link_url);
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => {
          setOpen((v) => !v);
          if (!open) load();
        }}
        aria-label={`Notifications${unread ? ` (${unread} unread)` : ''}`}
        aria-expanded={open}
        className="relative rounded-xl p-2.5 text-ink-500 transition-colors hover:bg-line-soft focus-ring"
      >
        <Bell className="h-[18px] w-[18px]" />
        {unread > 0 && (
          <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[9px] font-bold text-white">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-50 mt-2 w-[360px] animate-scale-in rounded-2xl border border-line bg-surface shadow-popover">
          <div className="flex items-center justify-between border-b border-line-soft px-4 py-3">
            <p className="text-[13px] font-bold text-ink">
              Notifications {unread > 0 && <span className="text-danger">· {unread} new</span>}
            </p>
            <button
              onClick={markAllRead}
              disabled={unread === 0}
              className="flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-semibold text-brand-600 hover:bg-brand-50 disabled:opacity-40"
            >
              <CheckCheck className="h-3.5 w-3.5" /> Mark all read
            </button>
          </div>
          <div className="max-h-[380px] overflow-y-auto scrollbar-thin p-1.5">
            {loading && items.length === 0 && (
              <div className="space-y-2 p-3">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="skeleton h-12 rounded-lg" />
                ))}
              </div>
            )}
            {!loading && items.length === 0 && (
              <div className="flex flex-col items-center gap-2 px-4 py-10 text-center">
                <BellOff className="h-6 w-6 text-faint" />
                <p className="text-[13px] font-semibold text-ink">You're all caught up</p>
                <p className="text-[11px] text-muted">Case assignments, escalations and high-risk detections appear here.</p>
              </div>
            )}
            {items.map((n) => (
              <button
                key={n.id}
                onClick={() => onItemClick(n)}
                className={cn(
                  'flex w-full items-start gap-3 rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-bg',
                  !n.is_read && 'bg-brand-50/60'
                )}
              >
                <span className="mt-0.5 text-base leading-none">{TYPE_ICONS[n.type] || '🔔'}</span>
                <span className="min-w-0 flex-1">
                  <span className={cn('block text-[12.5px] leading-snug', n.is_read ? 'font-medium text-ink-700' : 'font-bold text-ink')}>
                    {n.title}
                  </span>
                  {n.body && <span className="mt-0.5 block line-clamp-2 text-[11px] leading-snug text-muted">{n.body}</span>}
                  <span className="mt-1 block text-[10.5px] font-medium text-faint">{formatRelativeTime(n.created_at)}</span>
                </span>
                {!n.is_read && <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-brand-500" />}
              </button>
            ))}
          </div>
          <div className="border-t border-line-soft p-2">
            <button
              onClick={() => {
                setOpen(false);
                navigate('/settings?tab=notifications');
              }}
              className="w-full rounded-lg px-3 py-2 text-[12px] font-semibold text-brand-600 hover:bg-brand-50"
            >
              Notification settings →
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default notificationsPopover;
