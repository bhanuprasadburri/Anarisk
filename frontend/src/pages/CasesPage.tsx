import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Briefcase,
  Search,
  Share2,
  Send,
  CheckCircle,
  ChevronRight,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { caseService } from '../services/caseService';
import {
  InvestigationCase,
  CaseStatus,
  CaseNote,
  CaseEvent,
  CaseEscalation,
  PartnerType,
  ResolutionOutcome,
} from '../types';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Modal } from '../components/ui/modal';
import { formatDate, formatRelativeTime } from '../lib/formatters';
import { getSeverityColor } from '../lib/utils';
import {
  CASE_STATUS_LABELS,
  RESOLUTION_OUTCOME_LABELS,
} from '../lib/constants';

export const CasesPage: React.FC = () => {
  const { activeBrand, user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [cases, setCases] = useState<InvestigationCase[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>(searchParams.get('status') || '');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');

  // Selected Case & Details
  const [selectedCase, setSelectedCase] = useState<InvestigationCase | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // Note form
  const [newNoteBody, setNewNoteBody] = useState('');

  // Escalation Modal
  const [isEscalateOpen, setIsEscalateOpen] = useState(false);
  const [escalateData, setEscalateData] = useState({
    partner_type: 'platform' as PartnerType,
    partner_contact: '',
    reason: '',
    requested_action: 'Domain suspension / DNS sinkhole',
  });

  // Resolve Modal
  const [isResolveOpen, setIsResolveOpen] = useState(false);
  const [resolveOutcome, setResolveOutcome] = useState<ResolutionOutcome>('confirmed_threat_actioned');
  const [resolveNotes, setResolveNotes] = useState('');

  const loadCases = async () => {
    setIsLoading(true);
    try {
      const res = await caseService.listCases({
        brand_id: activeBrand?.id,
        status: statusFilter || undefined,
        severity: severityFilter || undefined,
        search: searchQuery || undefined,
      });
      setCases(res.items);

      const targetId = searchParams.get('id');
      if (targetId) {
        const found = res.items.find((c) => c.id === targetId);
        if (found) {
          openCaseDetails(found);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCases();
  }, [activeBrand, statusFilter, severityFilter]);

  const openCaseDetails = async (c: InvestigationCase) => {
    setSelectedCase(c);
    setIsDetailOpen(true);
    try {
      const details = await caseService.getCase(c.id);
      setSelectedCase(details);
    } catch (err) {
      console.error(err);
    }
  };

  const handleStatusChange = async (newStatus: CaseStatus) => {
    if (!selectedCase) return;
    try {
      const updated = await caseService.updateStatus(
        selectedCase.id,
        newStatus,
        `Status transitioned by ${user?.full_name || 'investigator'}`
      );
      setSelectedCase(updated);
      loadCases();
    } catch (err) {
      alert('Failed to update status: ' + (err as Error).message);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCase || !newNoteBody.trim()) return;
    try {
      const n = await caseService.addNote(selectedCase.id, newNoteBody.trim());
      const updatedNotes = [...(selectedCase.notes || []), n];
      setSelectedCase({ ...selectedCase, notes: updatedNotes });
      setNewNoteBody('');
    } catch (err) {
      alert('Failed to add note: ' + (err as Error).message);
    }
  };

  const handleEscalateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCase) return;
    try {
      const updated = await caseService.escalate(
        selectedCase.id,
        escalateData.partner_type,
        escalateData.partner_contact,
        escalateData.reason,
        escalateData.requested_action
      );
      alert('Case escalated to partner successfully.');
      setIsEscalateOpen(false);
      setSelectedCase(updated);
      loadCases();
    } catch (err) {
      alert('Escalation failed: ' + (err as Error).message);
    }
  };

  const handleResolveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCase) return;
    try {
      const updated = await caseService.resolve(selectedCase.id, resolveOutcome, resolveNotes);
      alert('Case marked resolved.');
      setIsResolveOpen(false);
      setSelectedCase(updated);
      loadCases();
    } catch (err) {
      alert('Failed to resolve case: ' + (err as Error).message);
    }
  };

  const statuses: { key: string; label: string }[] = [
    { key: '', label: 'All Cases' },
    { key: 'detected', label: 'Detected' },
    { key: 'triaged', label: 'Triaged' },
    { key: 'under_review', label: 'Under Review' },
    { key: 'assigned', label: 'Assigned' },
    { key: 'escalated', label: 'Escalated' },
    { key: 'resolved', label: 'Resolved' },
  ];

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Investigation & Response Cases
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Explainable case reviews, cross-entity campaigns, partner handoffs and auditable resolution.
          </p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-1.5 border-b border-slate-800 pb-2">
        {statuses.map((s) => (
          <button
            key={s.key}
            onClick={() => setStatusFilter(s.key)}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
              statusFilter === s.key
                ? 'bg-teal-500/20 text-teal-300 border border-teal-500/40 shadow-sm'
                : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Search & Severity Toolbar */}
      <Card className="p-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search cases by number or keyword..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadCases()}
              className="w-full rounded-lg border border-slate-800 bg-slate-900/80 py-1.5 pl-9 pr-4 text-sm text-slate-100 placeholder:text-slate-500 focus:border-teal-500 focus:outline-none"
            />
          </div>

          <div className="flex items-center gap-3">
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-1.5 text-xs text-slate-300 outline-none focus:border-teal-500"
            >
              <option value="">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <Button variant="outline" size="sm" onClick={loadCases}>
              Search
            </Button>
          </div>
        </div>
      </Card>

      {/* Case List */}
      {isLoading ? (
        <div className="flex min-h-[40vh] items-center justify-center">
          <div className="h-7 w-7 animate-spin rounded-full border-4 border-teal-500 border-t-transparent" />
        </div>
      ) : cases.length === 0 ? (
        <Card className="p-12 text-center">
          <p className="text-slate-400">No investigation cases found.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {cases.map((c) => {
            const colors = getSeverityColor(c.severity);
            return (
              <Card
                key={c.id}
                className="hover:border-slate-700 cursor-pointer p-4 transition-all"
                onClick={() => openCaseDetails(c)}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2.5">
                      <span className="font-mono text-xs font-bold text-teal-400 bg-teal-950/60 border border-teal-800/80 px-2 py-0.5 rounded">
                        {c.case_number}
                      </span>
                      <h4 className="font-semibold text-slate-100 text-sm">{c.title}</h4>
                      <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border ${colors.badge}`}>
                        {c.severity.toUpperCase()}
                      </span>
                    </div>
                    {c.summary && (
                      <p className="text-xs text-slate-400 line-clamp-1">{c.summary}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-4 text-xs font-mono">
                    <span className="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-200 border border-slate-700 font-semibold capitalize">
                      {CASE_STATUS_LABELS[c.status] || c.status}
                    </span>
                    <span className="text-slate-400 text-right">
                      {formatRelativeTime(c.created_at)}
                    </span>
                    <ChevronRight className="h-4 w-4 text-slate-500" />
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Case Detail Modal */}
      {selectedCase && (
        <Modal
          isOpen={isDetailOpen}
          onClose={() => setIsDetailOpen(false)}
          title={`Case ${selectedCase.case_number}: ${selectedCase.title}`}
          description={`Created ${formatDate(selectedCase.created_at)}`}
          maxWidth="4xl"
        >
          <div className="space-y-6">
            {/* Action Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl bg-slate-900/90 border border-slate-800">
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-400">Current Status:</span>
                <span className="font-mono text-xs font-bold px-2.5 py-1 rounded bg-slate-800 text-teal-300 border border-slate-700 uppercase">
                  {selectedCase.status}
                </span>
                <span className="text-xs text-slate-400">
                  Assignee:{' '}
                  <strong className="text-slate-200">
                    {selectedCase.assigned_to?.full_name || 'Unassigned'}
                  </strong>
                </span>
              </div>

              {/* Status Transition buttons */}
              <div className="flex flex-wrap items-center gap-2">
                {selectedCase.status === 'detected' && (
                  <Button variant="outline" size="sm" onClick={() => handleStatusChange('triaged')}>
                    Mark Triaged
                  </Button>
                )}
                {selectedCase.status === 'triaged' && (
                  <Button variant="outline" size="sm" onClick={() => handleStatusChange('under_review')}>
                    Start Review
                  </Button>
                )}
                {selectedCase.status === 'under_review' && (
                  <Button variant="outline" size="sm" onClick={() => handleStatusChange('assigned')}>
                    Assign Owner
                  </Button>
                )}
                {selectedCase.status !== 'resolved' && (
                  <>
                    <Button variant="outline" size="sm" onClick={() => setIsEscalateOpen(true)}>
                      <Share2 className="mr-1.5 h-3.5 w-3.5 text-amber-400" />
                      Escalate to Partner
                    </Button>
                    <Button variant="teal" size="sm" onClick={() => setIsResolveOpen(true)}>
                      <CheckCircle className="mr-1.5 h-3.5 w-3.5" />
                      Resolve Case
                    </Button>
                  </>
                )}
              </div>
            </div>

            {/* Case Summary */}
            {selectedCase.summary && (
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-300">
                <span className="font-semibold text-slate-200 block mb-1">Investigation Objective:</span>
                {selectedCase.summary}
              </div>
            )}

            {/* Escalations if any */}
            {(selectedCase.escalations || []).length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-mono uppercase tracking-wider text-amber-400">
                  Partner Escalations ({(selectedCase.escalations || []).length})
                </h4>
                {(selectedCase.escalations || []).map((esc) => (
                  <div key={esc.id} className="p-3 rounded-lg bg-amber-950/20 border border-amber-900/50 text-xs">
                    <div className="flex items-center justify-between font-mono font-bold text-amber-300 mb-1">
                      <span>Escalated to: {esc.partner_type.toUpperCase()}</span>
                      <span className="text-[10px] text-slate-400">{formatDate(esc.created_at)}</span>
                    </div>
                    <p className="text-slate-300 mb-1">{esc.reason}</p>
                    {esc.requested_action && (
                      <p className="text-slate-400 text-[11px]">Action Requested: {esc.requested_action}</p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Investigator Notes */}
            <div className="space-y-3">
              <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400">
                Case Notes & Analysis ({(selectedCase.notes || []).length})
              </h4>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {(selectedCase.notes || []).map((n) => (
                  <div key={n.id} className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
                    <div className="flex justify-between text-[11px] text-slate-400 mb-1 font-mono">
                      <span>{n.author?.full_name || 'Investigator'}</span>
                      <span>{formatDate(n.created_at)}</span>
                    </div>
                    <p className="text-slate-200">{n.body}</p>
                  </div>
                ))}
              </div>

              {/* Add Note Form */}
              <form onSubmit={handleAddNote} className="flex gap-2">
                <input
                  type="text"
                  placeholder="Add investigator note..."
                  value={newNoteBody}
                  onChange={(e) => setNewNoteBody(e.target.value)}
                  className="flex-1 rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 outline-none focus:border-teal-500"
                />
                <Button type="submit" variant="outline" size="sm">
                  <Send className="h-3.5 w-3.5" />
                </Button>
              </form>
            </div>

            {/* Audit Timeline */}
            <div className="space-y-2">
              <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400">
                Audit Trail Events ({(selectedCase.events || []).length})
              </h4>
              <div className="space-y-1.5 max-h-36 overflow-y-auto font-mono text-[11px]">
                {(selectedCase.events || []).map((ev) => (
                  <div key={ev.id} className="flex items-center justify-between p-2 rounded bg-slate-900/40 border border-slate-800/60">
                    <span className="text-slate-300">{ev.event_type}</span>
                    <span className="text-slate-500">{formatDate(ev.created_at)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Modal>
      )}

      {/* Escalate Modal */}
      <Modal
        isOpen={isEscalateOpen}
        onClose={() => setIsEscalateOpen(false)}
        title="Escalate Case to External Partner"
        description="Record an outbound takedown request or legal referral"
      >
        <form onSubmit={handleEscalateSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Partner Type</label>
            <select
              value={escalateData.partner_type}
              onChange={(e) => setEscalateData({ ...escalateData, partner_type: e.target.value as PartnerType })}
              className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 outline-none focus:border-teal-500"
            >
              <option value="platform">Platform / Host / Registrar</option>
              <option value="legal">Corporate Legal Counsel</option>
              <option value="marketing">Brand Communications / Marketing</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Partner Contact / Channel</label>
            <input
              type="text"
              placeholder="abuse@registrar.example or ticket ref"
              value={escalateData.partner_contact}
              onChange={(e) => setEscalateData({ ...escalateData, partner_contact: e.target.value })}
              className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 outline-none focus:border-teal-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Reason for Escalation</label>
            <textarea
              required
              rows={2}
              placeholder="e.g. Active credential harvesting phishing site impersonating bank login..."
              value={escalateData.reason}
              onChange={(e) => setEscalateData({ ...escalateData, reason: e.target.value })}
              className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 outline-none focus:border-teal-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3">
            <Button type="button" variant="ghost" onClick={() => setIsEscalateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="teal">
              Confirm Escalation
            </Button>
          </div>
        </form>
      </Modal>

      {/* Resolve Modal */}
      <Modal
        isOpen={isResolveOpen}
        onClose={() => setIsResolveOpen(false)}
        title="Resolve Investigation Case"
        description="Categorize resolution outcome and archive findings"
      >
        <form onSubmit={handleResolveSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Resolution Outcome</label>
            <select
              value={resolveOutcome}
              onChange={(e) => setResolveOutcome(e.target.value as ResolutionOutcome)}
              className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 outline-none focus:border-teal-500"
            >
              {Object.entries(RESOLUTION_OUTCOME_LABELS).map(([k, label]) => (
                <option key={k} value={k}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Resolution Summary</label>
            <textarea
              rows={3}
              placeholder="Describe resolution actions taken and final state..."
              value={resolveNotes}
              onChange={(e) => setResolveNotes(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 outline-none focus:border-teal-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3">
            <Button type="button" variant="ghost" onClick={() => setIsResolveOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="teal">
              Resolve & Close Case
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

