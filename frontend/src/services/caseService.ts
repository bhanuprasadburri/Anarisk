import { apiRequest } from './apiClient';
import {
  InvestigationCase,
  CaseStatus,
  CaseNote,
  PartnerType,
  ResolutionOutcome,
  PaginatedResponse
} from '../types';
import { mockStore } from '../mocks/mockStore';

export const caseService = {
  async listCases(params: {
    status?: string;
    severity?: string;
    brand_id?: string;
    search?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<PaginatedResponse<InvestigationCase>> {
    try {
      const q = new URLSearchParams();
      if (params.status) q.set('status', params.status);
      if (params.severity) q.set('severity', params.severity);
      if (params.brand_id) q.set('brand_id', params.brand_id);
      if (params.search) q.set('search', params.search);
      if (params.page) q.set('page', params.page.toString());
      if (params.page_size) q.set('page_size', params.page_size.toString());

      return await apiRequest<PaginatedResponse<InvestigationCase>>(`/cases?${q.toString()}`);
    } catch {
      let filtered = [...mockStore.cases];
      if (params.status) {
        filtered = filtered.filter((c) => c.status === params.status);
      }
      if (params.severity) {
        filtered = filtered.filter((c) => c.severity === params.severity);
      }
      if (params.brand_id) {
        filtered = filtered.filter((c) => c.brand_id === params.brand_id);
      }
      if (params.search) {
        const s = params.search.toLowerCase();
        filtered = filtered.filter(
          (c) =>
            c.title.toLowerCase().includes(s) ||
            c.case_number.toLowerCase().includes(s) ||
            (c.summary && c.summary.toLowerCase().includes(s))
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

  async getCase(caseId: string): Promise<InvestigationCase> {
    try {
      return await apiRequest<InvestigationCase>(`/cases/${caseId}`);
    } catch {
      const c = mockStore.cases.find((item) => item.id === caseId);
      if (!c) throw new Error('Case not found');
      return c;
    }
  },

  async createCase(payload: {
    brand_id: string;
    title: string;
    summary?: string;
    entity_ids: string[];
  }): Promise<InvestigationCase> {
    try {
      return await apiRequest<InvestigationCase>('/cases', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    } catch {
      return mockStore.createCase(payload.brand_id, payload.title, payload.entity_ids, payload.summary);
    }
  },

  async updateStatus(
    caseId: string,
    status: CaseStatus,
    comment?: string,
    outcome?: ResolutionOutcome,
    summary?: string
  ): Promise<InvestigationCase> {
    try {
      return await apiRequest<InvestigationCase>(`/cases/${caseId}/status`, {
        method: 'POST',
        body: JSON.stringify({
          status,
          comment,
          resolution_outcome: outcome,
          resolution_summary: summary,
        }),
      });
    } catch {
      return mockStore.updateCaseStatus(caseId, status, comment, outcome, summary);
    }
  },

  async assign(caseId: string, assigneeId: string, note?: string): Promise<InvestigationCase> {
    try {
      return await apiRequest<InvestigationCase>(`/cases/${caseId}/assign`, {
        method: 'POST',
        body: JSON.stringify({ assignee_id: assigneeId, note }),
      });
    } catch {
      return mockStore.assignCase(caseId, assigneeId, note);
    }
  },

  async escalate(
    caseId: string,
    partnerType: PartnerType,
    partnerContact: string,
    reason: string,
    requestedAction?: string
  ): Promise<InvestigationCase> {
    try {
      return await apiRequest<InvestigationCase>(`/cases/${caseId}/escalate`, {
        method: 'POST',
        body: JSON.stringify({
          partner_type: partnerType,
          partner_contact: partnerContact,
          reason,
          requested_action: requestedAction,
        }),
      });
    } catch {
      return mockStore.escalateCase(caseId, partnerType, partnerContact, reason, requestedAction);
    }
  },

  async resolve(caseId: string, outcome: ResolutionOutcome, summary: string): Promise<InvestigationCase> {
    try {
      return await apiRequest<InvestigationCase>(`/cases/${caseId}/resolve`, {
        method: 'POST',
        body: JSON.stringify({ outcome, summary }),
      });
    } catch {
      return mockStore.updateCaseStatus(caseId, 'resolved', undefined, outcome, summary);
    }
  },

  async addNote(caseId: string, body: string): Promise<CaseNote> {
    try {
      return await apiRequest<CaseNote>(`/cases/${caseId}/notes`, {
        method: 'POST',
        body: JSON.stringify({ body }),
      });
    } catch {
      return mockStore.addCaseNote(caseId, body);
    }
  },
};
