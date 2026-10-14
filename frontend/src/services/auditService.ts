import { apiRequest, qs } from './apiClient';
import { AuditLog, PaginatedResponse } from '../types';

export const auditService = {
  async listAudit(params: {
    action?: string;
    resource_type?: string;
    resource_id?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<PaginatedResponse<AuditLog>> {
    return apiRequest<PaginatedResponse<AuditLog>>(`/audit${qs(params)}`);
  },
};
