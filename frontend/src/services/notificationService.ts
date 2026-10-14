import { apiRequest, qs } from './apiClient';
import { NotificationItem, NotificationListResponse } from '../types';

export const notificationService = {
  async list(params: { unread_only?: boolean; page?: number; page_size?: number } = {}): Promise<NotificationListResponse> {
    return apiRequest<NotificationListResponse>(`/notifications${qs(params)}`);
  },

  async markRead(ids?: string[]): Promise<{ updated: number; unread_count: number }> {
    return apiRequest(`/notifications/read`, {
      method: 'POST',
      body: JSON.stringify(ids ? { ids } : {}),
    });
  },
};

export function notificationLink(item: NotificationItem): string | null {
  return item.link_url || null;
}
