import { apiRequest } from './apiClient';
import { DashboardStats, MobileAppsSummary } from '../types';
import { mockStore } from '../mocks/mockStore';

export const dashboardService = {
  async getStats(brandId?: string): Promise<DashboardStats> {
    try {
      const q = brandId ? `?brand_id=${brandId}` : '';
      return await apiRequest<DashboardStats>(`/dashboard/stats${q}`);
    } catch {
      return mockStore.getDashboardStats();
    }
  },

  async getMobileApps(brandId?: string, limit = 25): Promise<MobileAppsSummary> {
    try {
      const params = new URLSearchParams();
      if (brandId) params.set('brand_id', brandId);
      params.set('limit', limit.toString());
      const data = await apiRequest<any>(`/dashboard/mobile-apps?${params.toString()}`);
      return {
        total_monitored: data.total_monitored || data.rows?.length || 0,
        high_risk_count: data.high_risk_count || 0,
        severity_distribution: data.by_severity || {},
        apps: data.rows || [],
      };
    } catch {
      return mockStore.getMobileAppsSummary();
    }
  },
};
