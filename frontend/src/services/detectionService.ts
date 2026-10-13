import { apiRequest } from './apiClient';
import { DetectionSignal } from '../types';
import { mockStore } from '../mocks/mockStore';

export const detectionService = {
  async getSignals(params: { entity_id?: string; brand_id?: string } = {}): Promise<DetectionSignal[]> {
    try {
      const q = new URLSearchParams();
      if (params.entity_id) q.set('entity_id', params.entity_id);
      if (params.brand_id) q.set('brand_id', params.brand_id);
      return await apiRequest<DetectionSignal[]>(`/detection/signals?${q.toString()}`);
    } catch {
      let allSignals = Object.values(mockStore.assessments).flatMap((a) => a.signals || []);
      if (params.entity_id) {
        allSignals = allSignals.filter((s) => s.entity_id === params.entity_id);
      }
      return allSignals;
    }
  },

  async getModelInfo(): Promise<any> {
    try {
      return await apiRequest<any>('/detection/model');
    } catch {
      return {
        model_version: 'v1.4.0-heuristic',
        status: 'heuristic - unvalidated; requires human review',
        weights: {
          brand_logo: 0.30,
          impersonation: 0.30,
          url_risk: 0.25,
          behavior: 0.15,
        },
        severity_thresholds: {
          low: 0.0,
          medium: 0.40,
          high: 0.60,
          critical: 0.80,
        },
        confidence: {
          evidence_weight: 0.40,
          availability_weight: 0.30,
          corroboration_weight: 0.30,
          synthetic_cap: 0.40,
        },
      };
    }
  },

  async bulkAnalyze(brandId?: string, entityIds?: string[]): Promise<any> {
    try {
      return await apiRequest<any>('/detection/analyze', {
        method: 'POST',
        body: JSON.stringify({ brand_id: brandId, entity_ids: entityIds }),
      });
    } catch {
      const targetIds = entityIds || mockStore.entities.map((e) => e.id);
      const results = targetIds.map((id) => mockStore.analyzeEntity(id));
      return {
        analyzed: results.length,
        skipped: [],
        assessments: results,
      };
    }
  },
};
