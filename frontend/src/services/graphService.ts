import { apiRequest, qs } from './apiClient';
import { GraphResponse, ClusterSummary, RelatedEntity } from '../types';

export const graphService = {
  async getGraph(params: {
    brand_id?: string;
    entity_type?: string[];
    severity?: string[];
    min_risk?: number;
    min_confidence?: number;
  } = {}): Promise<GraphResponse> {
    return apiRequest<GraphResponse>(`/graph${qs(params)}`);
  },

  async rebuild(brand_id?: string): Promise<{ created: number; removed: number }> {
    return apiRequest(`/graph/rebuild`, { method: 'POST', body: JSON.stringify({ brand_id }) });
  },

  async getClusters(params: { brand_id?: string; proposed_only?: boolean } = {}): Promise<{
    items: ClusterSummary[];
  }> {
    return apiRequest(`/graph/clusters${qs(params)}`);
  },

  async getNeighbors(entityId: string, depth = 1): Promise<GraphResponse> {
    return apiRequest<GraphResponse>(`/graph/entities/${entityId}/neighbors${qs({ depth })}`);
  },

  async getRelated(entityId: string, maxDepth = 3): Promise<{ items: RelatedEntity[] }> {
    return apiRequest(`/graph/entities/${entityId}/related${qs({ max_depth: maxDepth })}`);
  },

  async addRelationship(payload: {
    source_id: string;
    target_id: string;
    relationship_type: string;
    confidence: number;
    evidence_note?: string;
  }): Promise<unknown> {
    return apiRequest(`/graph/relationships`, { method: 'POST', body: JSON.stringify(payload) });
  },

  async discover(entityId: string): Promise<{ created: number; message: string }> {
    return apiRequest(`/graph/discover`, { method: 'POST', body: JSON.stringify({ entity_id: entityId }) });
  },
};
