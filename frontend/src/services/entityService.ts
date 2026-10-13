import { apiRequest } from './apiClient';
import { DigitalEntity, PaginatedResponse, RiskAssessment } from '../types';
import { mockStore } from '../mocks/mockStore';

export const entityService = {
  async listEntities(params: {
    brand_id?: string;
    entity_type?: string;
    severity?: string;
    search?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<PaginatedResponse<DigitalEntity>> {
    try {
      const q = new URLSearchParams();
      if (params.brand_id) q.set('brand_id', params.brand_id);
      if (params.entity_type) q.set('entity_type', params.entity_type);
      if (params.severity) q.set('severity', params.severity);
      if (params.search) q.set('search', params.search);
      if (params.page) q.set('page', params.page.toString());
      if (params.page_size) q.set('page_size', params.page_size.toString());

      return await apiRequest<PaginatedResponse<DigitalEntity>>(`/entities?${q.toString()}`);
    } catch {
      let filtered = [...mockStore.entities];
      if (params.brand_id) {
        filtered = filtered.filter((e) => e.brand_id === params.brand_id);
      }
      if (params.entity_type) {
        filtered = filtered.filter((e) => e.entity_type === params.entity_type);
      }
      if (params.severity) {
        filtered = filtered.filter((e) => e.current_severity === params.severity);
      }
      if (params.search) {
        const s = params.search.toLowerCase();
        filtered = filtered.filter(
          (e) =>
            e.display_name.toLowerCase().includes(s) ||
            e.canonical_id.toLowerCase().includes(s) ||
            (e.platform && e.platform.toLowerCase().includes(s))
        );
      }

      const page = params.page || 1;
      const pageSize = params.page_size || 20;
      const start = (page - 1) * pageSize;
      const items = filtered.slice(start, start + pageSize);

      return {
        items,
        total: filtered.length,
        page,
        page_size: pageSize,
        pages: Math.ceil(filtered.length / pageSize),
      };
    }
  },

  async getEntity(entityId: string): Promise<DigitalEntity> {
    try {
      return await apiRequest<DigitalEntity>(`/entities/${entityId}`);
    } catch {
      const e = mockStore.entities.find((item) => item.id === entityId);
      if (!e) throw new Error('Entity not found');
      const assessment = mockStore.assessments[entityId];
      return {
        ...e,
        latest_assessment: assessment || e.latest_assessment,
      };
    }
  },

  async submitEntity(payload: {
    brand_id: string;
    entity_type: any;
    display_name?: string;
    platform?: string;
    source_url?: string;
    attributes: Record<string, any>;
    analyze?: boolean;
  }): Promise<DigitalEntity> {
    try {
      const res = await apiRequest<{ entity: DigitalEntity; assessment?: RiskAssessment }>('/entities', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      return res.entity;
    } catch {
      return mockStore.submitEntity(payload);
    }
  },

  async analyzeEntity(entityId: string): Promise<RiskAssessment> {
    try {
      return await apiRequest<RiskAssessment>(`/entities/${entityId}/analyze`, {
        method: 'POST',
      });
    } catch {
      return mockStore.analyzeEntity(entityId);
    }
  },

  async inspectUrl(entityId: string, url: string): Promise<any> {
    try {
      return await apiRequest<any>(`/entities/${entityId}/inspect-url`, {
        method: 'POST',
        body: JSON.stringify({ url }),
      });
    } catch {
      return {
        inspected_url: url,
        status: 'simulated_ssrf_safe',
        response_code: 200,
        content_type: 'text/html',
        ip: '203.0.113.7',
        title: 'AcmeBank Phishing Portal Simulation',
        evidence_created: true,
      };
    }
  },
};
