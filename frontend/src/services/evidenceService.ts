import { apiRequest } from './apiClient';
import { EvidenceRecord, EvidenceKind } from '../types';
import { mockStore } from '../mocks/mockStore';

export const evidenceService = {
  async listEvidence(entityId?: string): Promise<EvidenceRecord[]> {
    try {
      const q = entityId ? `?entity_id=${entityId}` : '';
      return await apiRequest<EvidenceRecord[]>(`/evidence${q}`);
    } catch {
      if (entityId) {
        return mockStore.evidence.filter((ev) => ev.entity_id === entityId);
      }
      return mockStore.evidence;
    }
  },

  async createEvidence(payload: {
    entity_id: string;
    kind: EvidenceKind;
    title?: string;
    description?: string;
    url?: string;
    text_content?: string;
  }): Promise<EvidenceRecord> {
    try {
      return await apiRequest<EvidenceRecord>('/evidence', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    } catch {
      const ev: EvidenceRecord = {
        id: `ev-${Date.now().toString(36)}`,
        entity_id: payload.entity_id,
        kind: payload.kind,
        description: payload.description || payload.title || 'Evidence added by analyst',
        url: payload.url || null,
        created_at: new Date().toISOString(),
      };
      mockStore.evidence.unshift(ev);
      const ent = mockStore.entities.find((e) => e.id === payload.entity_id);
      if (ent) ent.evidence_count = (ent.evidence_count || 0) + 1;
      mockStore.addAuditLog('evidence:create', 'evidence_record', ev.id, {
        entity_id: payload.entity_id,
        kind: payload.kind,
      });
      return ev;
    }
  },

  async uploadImageEvidence(
    entityId: string,
    file: File,
    title?: string,
    description?: string
  ): Promise<EvidenceRecord> {
    try {
      const formData = new FormData();
      formData.append('entity_id', entityId);
      formData.append('file', file);
      if (title) formData.append('title', title);
      if (description) formData.append('description', description);

      return await apiRequest<EvidenceRecord>('/evidence/upload', {
        method: 'POST',
        body: formData,
      });
    } catch {
      const ev: EvidenceRecord = {
        id: `ev-${Date.now().toString(36)}`,
        entity_id: entityId,
        kind: 'screenshot',
        description: description || title || `Uploaded ${file.name}`,
        file_name: file.name,
        file_size: file.size,
        mime_type: file.type || 'image/png',
        perceptual_hash: 'd4b8e3a1f0c295be',
        sha256: '9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b',
        created_at: new Date().toISOString(),
      };
      mockStore.evidence.unshift(ev);
      const ent = mockStore.entities.find((e) => e.id === entityId);
      if (ent) ent.evidence_count = (ent.evidence_count || 0) + 1;
      mockStore.addAuditLog('evidence:upload', 'evidence_record', ev.id, {
        filename: file.name,
        size: file.size,
      });
      return ev;
    }
  },
};
