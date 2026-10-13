import { apiRequest } from './apiClient';
import { AuditLog } from '../types';
import { mockStore } from '../mocks/mockStore';

export const auditService = {
  async listLogs(limit = 100): Promise<AuditLog[]> {
    try {
      return await apiRequest<AuditLog[]>(`/audit?limit=${limit}`);
    } catch {
      return mockStore.auditLogs.slice(0, limit);
    }
  },
};
