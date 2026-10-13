import { apiRequest } from './apiClient';
import { GraphResponse, ClusterSummary, RelatedEntity, InvestigationCase } from '../types';
import { mockStore } from '../mocks/mockStore';

export const graphService = {
  async getGraph(params: {
    brand_id?: string;
    entity_type?: string;
    min_risk?: number;
    severity?: string;
  } = {}): Promise<GraphResponse> {
    try {
      const q = new URLSearchParams();
      if (params.brand_id) q.set('brand_id', params.brand_id);
      if (params.entity_type) q.set('entity_type', params.entity_type);
      if (params.min_risk !== undefined) q.set('min_risk', params.min_risk.toString());
      if (params.severity) q.set('severity', params.severity);

      return await apiRequest<GraphResponse>(`/graph?${q.toString()}`);
    } catch {
      let nodes = [...mockStore.graphNodes];
      if (params.entity_type) {
        nodes = nodes.filter((n) => n.entity_type === params.entity_type);
      }
      if (params.severity) {
        nodes = nodes.filter((n) => n.severity === params.severity);
      }
      if (params.min_risk !== undefined) {
        nodes = nodes.filter((n) => (n.risk_score || 0) >= params.min_risk!);
      }

      const nodeIds = new Set(nodes.map((n) => n.id));
      const edges = mockStore.graphEdges.filter(
        (e) => nodeIds.has(e.source) && nodeIds.has(e.target)
      );

      return {
        nodes,
        edges,
        node_count: nodes.length,
        edge_count: edges.length,
        cluster_count: mockStore.clusters.length,
      };
    }
  },

  async getClusters(brandId?: string): Promise<ClusterSummary[]> {
    try {
      const q = brandId ? `?brand_id=${brandId}` : '';
      return await apiRequest<ClusterSummary[]>(`/graph/clusters${q}`);
    } catch {
      return mockStore.clusters;
    }
  },

  async createCaseFromCluster(entityIds: string[], title?: string): Promise<InvestigationCase> {
    try {
      return await apiRequest<InvestigationCase>('/graph/clusters/case', {
        method: 'POST',
        body: JSON.stringify({ entity_ids: entityIds, title }),
      });
    } catch {
      const brandId = mockStore.brands[0]?.id || 'b-001';
      const c = mockStore.createCase(
        brandId,
        title || `Campaign Cluster Investigation (${entityIds.length} entities)`,
        entityIds,
        'Case opened from connected risk graph cluster.'
      );
      return c;
    }
  },

  async discoverRelationships(brandId: string): Promise<any> {
    try {
      return await apiRequest<any>('/graph/discover', {
        method: 'POST',
        body: JSON.stringify({ brand_id: brandId }),
      });
    } catch {
      mockStore.addAuditLog('graph:discover', 'brand', brandId, {
        relationships_found: mockStore.graphEdges.length,
      });
      return {
        pairs_compared: 10,
        relationships_created: 5,
        relationships_existing: 5,
      };
    }
  },

  async rebuildGraph(): Promise<any> {
    try {
      return await apiRequest<any>('/graph/rebuild', { method: 'POST' });
    } catch {
      return {
        nodes: mockStore.graphNodes.length,
        edges: mockStore.graphEdges.length,
        components: mockStore.clusters.length,
      };
    }
  },

  async getRelatedEntities(entityId: string): Promise<RelatedEntity[]> {
    try {
      return await apiRequest<RelatedEntity[]>(`/graph/entities/${entityId}/related`);
    } catch {
      // Find connected neighbors in mock
      const connected = mockStore.graphEdges
        .filter((e) => e.source === entityId || e.target === entityId)
        .map((e) => {
          const neighborId = e.source === entityId ? e.target : e.source;
          const node = mockStore.graphNodes.find((n) => n.id === neighborId)!;
          return {
            entity: node,
            distance: 1,
            path_confidence: e.confidence,
            via: [e.relationship_type],
          };
        })
        .filter((item) => !!item.entity);

      return connected;
    }
  },
};
