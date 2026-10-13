import {
  Brand,
  BrandReference,
  DigitalEntity,
  RiskAssessment,
  EvidenceRecord,
  GraphNode,
  GraphEdge,
  ClusterSummary,
  InvestigationCase,
  AuditLog,
  User,
  DashboardStats,
  MobileAppsSummary,
  CaseStatus,
  CaseNote,
  CaseEvent,
  CaseEscalation,
  CaseAssignment,
  PartnerType,
  ResolutionOutcome
} from '../types';

import {
  INITIAL_USER,
  INITIAL_BRAND,
  INITIAL_REFERENCES,
  INITIAL_ENTITIES,
  INITIAL_ASSESSMENTS,
  INITIAL_EVIDENCE,
  INITIAL_GRAPH_NODES,
  INITIAL_GRAPH_EDGES,
  INITIAL_CLUSTERS,
  INITIAL_CASES,
  INITIAL_AUDIT_LOGS,
} from './initialData';

class MockDataStore {
  currentUser: User = { ...INITIAL_USER };
  brands: Brand[] = [{ ...INITIAL_BRAND, references: [...INITIAL_REFERENCES] }];
  entities: DigitalEntity[] = [...INITIAL_ENTITIES];
  assessments: Record<string, RiskAssessment> = { ...INITIAL_ASSESSMENTS };
  evidence: EvidenceRecord[] = [...INITIAL_EVIDENCE];
  graphNodes: GraphNode[] = [...INITIAL_GRAPH_NODES];
  graphEdges: GraphEdge[] = [...INITIAL_GRAPH_EDGES];
  clusters: ClusterSummary[] = [...INITIAL_CLUSTERS];
  cases: InvestigationCase[] = [...INITIAL_CASES];
  auditLogs: AuditLog[] = [...INITIAL_AUDIT_LOGS];

  constructor() {
    this.loadFromStorage();
  }

  private loadFromStorage() {
    try {
      const saved = localStorage.getItem('nimbus_mock_store');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.cases && parsed.entities) {
          this.currentUser = parsed.currentUser || this.currentUser;
          this.brands = parsed.brands || this.brands;
          this.entities = parsed.entities || this.entities;
          this.assessments = parsed.assessments || this.assessments;
          this.evidence = parsed.evidence || this.evidence;
          this.graphNodes = parsed.graphNodes || this.graphNodes;
          this.graphEdges = parsed.graphEdges || this.graphEdges;
          this.clusters = parsed.clusters || this.clusters;
          this.cases = parsed.cases || this.cases;
          this.auditLogs = parsed.auditLogs || this.auditLogs;
        }
      }
    } catch {
      // fallback to initial memory state
    }
  }

  private saveToStorage() {
    try {
      localStorage.setItem(
        'nimbus_mock_store',
        JSON.stringify({
          currentUser: this.currentUser,
          brands: this.brands,
          entities: this.entities,
          assessments: this.assessments,
          evidence: this.evidence,
          graphNodes: this.graphNodes,
          graphEdges: this.graphEdges,
          clusters: this.clusters,
          cases: this.cases,
          auditLogs: this.auditLogs,
        })
      );
    } catch {
      // storage quota or disabled
    }
  }

  resetToDefaults() {
    this.currentUser = { ...INITIAL_USER };
    this.brands = [{ ...INITIAL_BRAND, references: [...INITIAL_REFERENCES] }];
    this.entities = [...INITIAL_ENTITIES];
    this.assessments = { ...INITIAL_ASSESSMENTS };
    this.evidence = [...INITIAL_EVIDENCE];
    this.graphNodes = [...INITIAL_GRAPH_NODES];
    this.graphEdges = [...INITIAL_GRAPH_EDGES];
    this.clusters = [...INITIAL_CLUSTERS];
    this.cases = [...INITIAL_CASES];
    this.auditLogs = [...INITIAL_AUDIT_LOGS];
    localStorage.removeItem('nimbus_mock_store');
  }

  addAuditLog(action: string, resourceType: string, resourceId: string, details: Record<string, any>) {
    const log: AuditLog = {
      id: `aud-${Date.now()}`,
      action,
      resource_type: resourceType,
      resource_id: resourceId,
      actor_email: this.currentUser.email,
      ip_address: '127.0.0.1',
      details,
      created_at: new Date().toISOString(),
    };
    this.auditLogs.unshift(log);
    this.saveToStorage();
  }

  // Dashboard calculations
  getDashboardStats(): DashboardStats {
    const totalEntities = this.entities.length;
    const highRisk = this.entities.filter(
      (e) => e.current_severity === 'high' || e.current_severity === 'critical'
    ).length;
    const unassessed = this.entities.filter((e) => !e.current_risk_score).length;
    const openCases = this.cases.filter((c) => c.status !== 'resolved').length;
    const escalatedCases = this.cases.filter((c) => c.status === 'escalated').length;
    const unassignedOpen = this.cases.filter((c) => c.status !== 'resolved' && !c.assigned_to).length;
    const resolvedCases = this.cases.filter((c) => c.status === 'resolved').length;

    const riskDistribution: Record<string, number> = {
      critical: this.entities.filter((e) => e.current_severity === 'critical').length,
      high: this.entities.filter((e) => e.current_severity === 'high').length,
      medium: this.entities.filter((e) => e.current_severity === 'medium').length,
      low: this.entities.filter((e) => e.current_severity === 'low').length,
      unknown: this.entities.filter((e) => e.current_severity === 'unknown' || !e.current_severity).length,
    };

    const entityTypeDistribution: Record<string, number> = {
      social_profile: this.entities.filter((e) => e.entity_type === 'social_profile').length,
      website: this.entities.filter((e) => e.entity_type === 'website').length,
      domain: this.entities.filter((e) => e.entity_type === 'domain').length,
      image: this.entities.filter((e) => e.entity_type === 'image').length,
      mobile_app: this.entities.filter((e) => e.entity_type === 'mobile_app').length,
    };

    const dataProvenance: Record<string, number> = {
      collected: this.entities.filter((e) => e.provenance === 'collected').length,
      manual: this.entities.filter((e) => e.provenance === 'manual').length,
      synthetic: this.entities.filter((e) => e.provenance === 'synthetic').length,
    };

    const caseStatusDistribution: Record<string, number> = {
      detected: this.cases.filter((c) => c.status === 'detected').length,
      triaged: this.cases.filter((c) => c.status === 'triaged').length,
      under_review: this.cases.filter((c) => c.status === 'under_review').length,
      assigned: this.cases.filter((c) => c.status === 'assigned').length,
      escalated: this.cases.filter((c) => c.status === 'escalated').length,
      resolved: this.cases.filter((c) => c.status === 'resolved').length,
    };

    const recentDetections = [...this.entities]
      .sort((a, b) => new Date(b.last_assessed_at || b.created_at).getTime() - new Date(a.last_assessed_at || a.created_at).getTime())
      .slice(0, 5);

    const topRiskEntities = [...this.entities]
      .sort((a, b) => (b.current_risk_score || 0) - (a.current_risk_score || 0))
      .slice(0, 5);

    const latestActivity = this.cases.flatMap((c) =>
      (c.events || []).map((ev) => ({
        case_id: c.id,
        case_number: c.case_number,
        case_title: c.title,
        event_type: ev.event_type,
        from_status: ev.from_status,
        to_status: ev.to_status,
        actor_id: ev.actor?.id,
        created_at: ev.created_at,
      }))
    ).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 10);

    return {
      totals: {
        monitored_entities: totalEntities,
        high_risk_entities: highRisk,
        unassessed_entities: unassessed,
        open_cases: openCases,
        escalated_cases: escalatedCases,
        unassigned_open_cases: unassignedOpen,
        resolved_cases: resolvedCases,
      },
      risk_distribution: riskDistribution,
      entity_type_distribution: entityTypeDistribution,
      data_provenance: dataProvenance,
      case_status_distribution: caseStatusDistribution,
      recent_detections: recentDetections,
      top_risk_entities: topRiskEntities,
      latest_activity: latestActivity,
    };
  }

  // Mobile apps summary
  getMobileAppsSummary(): MobileAppsSummary {
    const apps = this.entities
      .filter((e) => e.entity_type === 'mobile_app')
      .map((e) => {
        const at = e.attributes || {};
        const perms: string[] = at.permissions || [];
        const sensitivePerms = ['READ_SMS', 'RECEIVE_SMS', 'SEND_SMS', 'READ_CONTACTS', 'SYSTEM_ALERT_WINDOW', 'CAMERA', 'ACCESS_FINE_LOCATION'];
        return {
          ...e,
          app_name: at.app_name || e.display_name,
          package_id: at.package_id || 'unknown.package',
          store: at.store || 'other',
          publisher_name: at.publisher_name || 'Unknown Publisher',
          publisher_verified: false,
          store_url: at.store_url || e.source_url,
          permissions_status: (e.provenance === 'collected' ? 'collected_from_store_listing' : 'supplied_unverified') as any,
          permissions_count: perms.length,
          sensitive_permissions: perms.filter((p) => sensitivePerms.includes(p)),
          linked_websites: at.linked_websites || [],
        };
      });

    const severityDist: Record<string, number> = {
      critical: apps.filter((a) => a.current_severity === 'critical').length,
      high: apps.filter((a) => a.current_severity === 'high').length,
      medium: apps.filter((a) => a.current_severity === 'medium').length,
      low: apps.filter((a) => a.current_severity === 'low').length,
      unknown: apps.filter((a) => a.current_severity === 'unknown').length,
    };

    return {
      total_monitored: apps.length,
      high_risk_count: apps.filter((a) => a.current_severity === 'high' || a.current_severity === 'critical').length,
      severity_distribution: severityDist,
      apps,
    };
  }

  // Entity operations
  submitEntity(data: {
    brand_id: string;
    entity_type: any;
    display_name?: string;
    platform?: string;
    source_url?: string;
    attributes: Record<string, any>;
    analyze?: boolean;
  }): DigitalEntity {
    const id = `ent-${Date.now().toString(36)}`;
    const newEnt: DigitalEntity = {
      id,
      brand_id: data.brand_id,
      entity_type: data.entity_type,
      canonical_id: data.source_url || `${data.entity_type}:${Date.now()}`,
      display_name: data.display_name || 'New Entity Submission',
      platform: data.platform || null,
      source_url: data.source_url || null,
      provenance: 'manual',
      submission_count: 1,
      current_risk_score: null,
      current_confidence: null,
      current_severity: 'unknown',
      first_seen_at: new Date().toISOString(),
      last_seen_at: new Date().toISOString(),
      last_assessed_at: null,
      created_at: new Date().toISOString(),
      attributes: data.attributes || {},
      evidence_count: 0,
    };

    this.entities.unshift(newEnt);
    this.addAuditLog('entity:submit', 'digital_entity', id, { entity_type: data.entity_type, display_name: newEnt.display_name });

    if (data.analyze) {
      this.analyzeEntity(id);
    }

    this.saveToStorage();
    return newEnt;
  }

  analyzeEntity(entityId: string): RiskAssessment {
    const entity = this.entities.find((e) => e.id === entityId);
    if (!entity) throw new Error('Entity not found');

    const asmId = `asm-${Date.now()}`;
    const assessment: RiskAssessment = {
      id: asmId,
      entity_id: entityId,
      model_version: 'v1.4.0-heuristic',
      configured_weights: { brand_logo: 0.30, impersonation: 0.30, url_risk: 0.25, behavior: 0.15 },
      effective_weights: { brand_logo: 0.30, impersonation: 0.30, url_risk: 0.25, behavior: 0.15 },
      component_scores: { brand_logo: 0.85, impersonation: 0.80, url_risk: 0.75, behavior: 0.60 },
      risk_score: 0.78,
      confidence_score: 0.40,
      confidence_breakdown: {
        evidence_quality: 0.30,
        availability: 1.0,
        corroboration: 0.80,
      },
      severity: 'high',
      thresholds: { medium: 0.40, high: 0.60, critical: 0.80 },
      is_synthetic: entity.provenance === 'synthetic',
      assessed_at: new Date().toISOString(),
      signals: [
        {
          id: `sig-${Date.now()}-1`,
          entity_id: entityId,
          assessment_id: asmId,
          signal_type: 'brand_logo',
          status: 'ok',
          score: 0.85,
          explanation: 'Visual analysis identified matching elements with registered official logo references.',
          evidence_refs: [],
          metadata: { hamming_distance: 4 },
          created_at: new Date().toISOString(),
        },
        {
          id: `sig-${Date.now()}-2`,
          entity_id: entityId,
          assessment_id: asmId,
          signal_type: 'impersonation',
          status: 'ok',
          score: 0.80,
          explanation: 'Identity and handle analysis indicated high lexical proximity to brand name.',
          evidence_refs: [],
          metadata: { rapidfuzz_ratio: 84 },
          created_at: new Date().toISOString(),
        },
        {
          id: `sig-${Date.now()}-3`,
          entity_id: entityId,
          assessment_id: asmId,
          signal_type: 'url_risk',
          status: 'ok',
          score: 0.75,
          explanation: 'Identified lookalike destination domain with suspicious registration keywords.',
          evidence_refs: [],
          metadata: { brand_in_host: true },
          created_at: new Date().toISOString(),
        },
        {
          id: `sig-${Date.now()}-4`,
          entity_id: entityId,
          assessment_id: asmId,
          signal_type: 'behavior',
          status: 'ok',
          score: 0.60,
          explanation: 'Account creation velocity and posting activity suggest automated coordination.',
          evidence_refs: [],
          metadata: { coordination_detected: true },
          created_at: new Date().toISOString(),
        },
      ],
    };

    this.assessments[entityId] = assessment;
    entity.current_risk_score = assessment.risk_score;
    entity.current_confidence = assessment.confidence_score;
    entity.current_severity = assessment.severity;
    entity.last_assessed_at = assessment.assessed_at;
    entity.latest_assessment = assessment;

    this.addAuditLog('entity:analyze', 'digital_entity', entityId, {
      risk_score: assessment.risk_score,
      severity: assessment.severity,
    });

    this.saveToStorage();
    return assessment;
  }

  // Case workflow operations
  createCase(brandId: string, title: string, entityIds: string[], summary?: string): InvestigationCase {
    const caseNum = `NN-2026-${(this.cases.length + 1).toString().padStart(6, '0')}`;
    const id = `case-${Date.now()}`;
    const now = new Date().toISOString();

    const newCase: InvestigationCase = {
      id,
      case_number: caseNum,
      brand_id: brandId,
      title,
      summary: summary || 'Investigation case created by security team.',
      status: 'detected',
      severity: 'high',
      confidence: 0.40,
      risk_score: 0.85,
      entity_count: entityIds.length,
      created_at: now,
      updated_at: now,
      created_by: {
        id: this.currentUser.id,
        email: this.currentUser.email,
        full_name: this.currentUser.full_name,
      },
      notes: [],
      events: [
        {
          id: `evt-${Date.now()}`,
          case_id: id,
          event_type: 'created',
          from_status: null,
          to_status: 'detected',
          actor: { id: this.currentUser.id, email: this.currentUser.email, full_name: this.currentUser.full_name },
          details: { entity_ids: entityIds },
          created_at: now,
        },
      ],
      escalations: [],
      assignments: [],
      allowed_transitions: ['triaged', 'under_review', 'resolved'],
      version: 1,
    };

    this.cases.unshift(newCase);
    this.addAuditLog('case:create', 'investigation_case', id, { case_number: caseNum, title });
    this.saveToStorage();
    return newCase;
  }

  updateCaseStatus(
    caseId: string,
    status: CaseStatus,
    comment?: string,
    resolutionOutcome?: ResolutionOutcome,
    resolutionSummary?: string
  ): InvestigationCase {
    const c = this.cases.find((item) => item.id === caseId);
    if (!c) throw new Error('Case not found');

    const fromStatus = c.status;
    c.status = status;
    c.updated_at = new Date().toISOString();

    if (status === 'resolved') {
      c.resolved_at = new Date().toISOString();
      c.resolution_outcome = resolutionOutcome || 'confirmed_threat_actioned';
      c.resolution_summary = resolutionSummary || comment || 'Resolved by security team';
      c.resolved_by = { id: this.currentUser.id, email: this.currentUser.email, full_name: this.currentUser.full_name };
    }

    const event: CaseEvent = {
      id: `evt-${Date.now()}`,
      case_id: caseId,
      event_type: status === 'resolved' ? 'resolved' : 'status_changed',
      from_status: fromStatus,
      to_status: status,
      actor: { id: this.currentUser.id, email: this.currentUser.email, full_name: this.currentUser.full_name },
      details: { comment: comment || `Status updated from ${fromStatus} to ${status}` },
      created_at: new Date().toISOString(),
    };
    c.events = c.events || [];
    c.events.unshift(event);

    this.addAuditLog('case:status', 'investigation_case', caseId, {
      from_status: fromStatus,
      to_status: status,
      comment,
    });

    this.saveToStorage();
    return c;
  }

  assignCase(caseId: string, assigneeId: string, note?: string): InvestigationCase {
    const c = this.cases.find((item) => item.id === caseId);
    if (!c) throw new Error('Case not found');

    const assignee = INITIAL_USER.id === assigneeId ? INITIAL_USER : {
      id: assigneeId,
      email: 'investigator2@nimbus.example',
      full_name: 'Ivan Analyst',
      role: 'investigator' as const,
      is_active: true,
      created_at: new Date().toISOString(),
    };

    c.assigned_to = {
      id: assignee.id,
      email: assignee.email,
      full_name: assignee.full_name,
    };

    if (c.status === 'under_review' || c.status === 'triaged' || c.status === 'detected') {
      c.status = 'assigned';
    }

    c.updated_at = new Date().toISOString();

    const asg: CaseAssignment = {
      id: `asg-${Date.now()}`,
      case_id: caseId,
      assignee: c.assigned_to,
      assigned_by_id: this.currentUser.id,
      assigned_at: new Date().toISOString(),
      note: note || 'Assigned via investigation workflow',
    };
    c.assignments = c.assignments || [];
    c.assignments.unshift(asg);

    const event: CaseEvent = {
      id: `evt-${Date.now()}`,
      case_id: caseId,
      event_type: 'assigned',
      to_status: c.status,
      actor: { id: this.currentUser.id, email: this.currentUser.email, full_name: this.currentUser.full_name },
      details: { assignee_email: assignee.email, note },
      created_at: new Date().toISOString(),
    };
    c.events = c.events || [];
    c.events.unshift(event);

    this.addAuditLog('case:assign', 'investigation_case', caseId, {
      assignee_email: assignee.email,
      note,
    });

    this.saveToStorage();
    return c;
  }

  escalateCase(
    caseId: string,
    partnerType: PartnerType,
    partnerContact: string,
    reason: string,
    requestedAction?: string
  ): InvestigationCase {
    const c = this.cases.find((item) => item.id === caseId);
    if (!c) throw new Error('Case not found');

    c.status = 'escalated';
    c.escalated_at = new Date().toISOString();
    c.escalation_summary = `Escalated to ${partnerType.toUpperCase()} partner (${partnerContact}): ${reason}`;
    c.updated_at = new Date().toISOString();

    const esc: CaseEscalation = {
      id: `esc-${Date.now()}`,
      case_id: caseId,
      partner_type: partnerType,
      partner_contact: partnerContact,
      reason,
      requested_action: requestedAction || null,
      created_by_id: this.currentUser.id,
      created_at: new Date().toISOString(),
    };
    c.escalations = c.escalations || [];
    c.escalations.unshift(esc);

    const event: CaseEvent = {
      id: `evt-${Date.now()}`,
      case_id: caseId,
      event_type: 'escalated',
      to_status: 'escalated',
      actor: { id: this.currentUser.id, email: this.currentUser.email, full_name: this.currentUser.full_name },
      details: { partner_type: partnerType, partner_contact: partnerContact, reason },
      created_at: new Date().toISOString(),
    };
    c.events = c.events || [];
    c.events.unshift(event);

    this.addAuditLog('case:escalate', 'investigation_case', caseId, {
      partner_type: partnerType,
      partner_contact: partnerContact,
      reason,
    });

    this.saveToStorage();
    return c;
  }

  addCaseNote(caseId: string, body: string): CaseNote {
    const c = this.cases.find((item) => item.id === caseId);
    if (!c) throw new Error('Case not found');

    const note: CaseNote = {
      id: `note-${Date.now()}`,
      case_id: caseId,
      author: {
        id: this.currentUser.id,
        email: this.currentUser.email,
        full_name: this.currentUser.full_name,
      },
      body,
      created_at: new Date().toISOString(),
    };

    c.notes = c.notes || [];
    c.notes.unshift(note);

    const event: CaseEvent = {
      id: `evt-${Date.now()}`,
      case_id: caseId,
      event_type: 'note_added',
      actor: { id: this.currentUser.id, email: this.currentUser.email, full_name: this.currentUser.full_name },
      details: { preview: body.substring(0, 100) },
      created_at: new Date().toISOString(),
    };
    c.events = c.events || [];
    c.events.unshift(event);

    this.addAuditLog('case:note', 'investigation_case', caseId, {
      note_length: body.length,
    });

    this.saveToStorage();
    return note;
  }
}

export const mockStore = new MockDataStore();
