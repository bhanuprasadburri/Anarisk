import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Search,
  Filter,
  Plus,
  ShieldAlert,
  ChevronRight,
  FileText,
  Briefcase,
  Globe,
  Share2,
  Smartphone,
  Image as ImageIcon,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { entityService } from '../services/entityService';
import { evidenceService } from '../services/evidenceService';
import { caseService } from '../services/caseService';
import { DigitalEntity, RiskAssessment, EvidenceRecord, EntityType } from '../types';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Modal } from '../components/ui/modal';
import { formatScore, formatDate } from '../lib/formatters';
import { getSeverityColor } from '../lib/utils';
import {
  ENTITY_TYPE_LABELS,
  SIGNAL_TYPE_LABELS,
  PROVENANCE_BADGES,
} from '../lib/constants';

export const EntitiesPage: React.FC = () => {
  const { activeBrand } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [entities, setEntities] = useState<DigitalEntity[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [searchQuery, setSearchQuery] = useState(searchParams.get('q') || '');
  const [selectedType, setSelectedType] = useState<string>(searchParams.get('type') || '');
  const [selectedSeverity, setSelectedSeverity] = useState<string>(searchParams.get('severity') || '');

  // Selected Entity for Review Modal
  const [selectedEntity, setSelectedEntity] = useState<DigitalEntity | null>(null);
  const [selectedAssessment, setSelectedAssessment] = useState<RiskAssessment | null>(null);
  const [entityEvidence, setEntityEvidence] = useState<EvidenceRecord[]>([]);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // Ingestion Modal
  const [isIngestOpen, setIsIngestOpen] = useState(false);
  const [newEntity, setNewEntity] = useState({
    entity_type: 'social_profile' as EntityType,
    canonical_id: '',
    display_name: '',
    platform: 'Instagram',
    source_url: '',
  });

  const loadEntities = async () => {
    setIsLoading(true);
    try {
      const res = await entityService.listEntities({
        brand_id: activeBrand?.id,
        entity_type: selectedType || undefined,
        severity: selectedSeverity || undefined,
        search: searchQuery || undefined,
        page_size: 50,
      });
      setEntities(res.items);

      // Check if URL has entity id
      const targetId = searchParams.get('id');
      if (targetId) {
        const found = res.items.find((e) => e.id === targetId);
        if (found) {
          openReview(found);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadEntities();
  }, [activeBrand, selectedType, selectedSeverity]);

  const openReview = async (entity: DigitalEntity) => {
    setSelectedEntity(entity);
    setIsDetailOpen(true);
    try {
      const [ass, ev] = await Promise.all([
        entityService.analyzeEntity(entity.id),
        evidenceService.listEvidence(entity.id),
      ]);
      setSelectedAssessment(ass);
      setEntityEvidence(ev);
    } catch (err) {
      console.error(err);
    }
  };

  const handleIngestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await entityService.submitEntity({
        brand_id: activeBrand?.id || 'b-001',
        entity_type: newEntity.entity_type,
        display_name: newEntity.display_name,
        platform: newEntity.platform,
        source_url: newEntity.source_url,
        attributes: { canonical_id: newEntity.canonical_id },
        analyze: true,
      });
      setIsIngestOpen(false);
      loadEntities();
    } catch (err) {
      alert('Ingestion failed: ' + (err as Error).message);
    }
  };

  const handleCreateCase = async () => {
    if (!selectedEntity) return;
    try {
      const c = await caseService.createCase({
        brand_id: selectedEntity.brand_id,
        title: `Investigation: ${selectedEntity.display_name}`,
        entity_ids: [selectedEntity.id],
        summary: `Investigator initiated case for suspicious entity ${selectedEntity.canonical_id}`,
      });
      alert(`Case ${c.case_number} created successfully.`);
      setIsDetailOpen(false);
    } catch (err) {
      alert('Failed to open case: ' + (err as Error).message);
    }
  };

  const getEntityIcon = (type: EntityType) => {
    switch (type) {
      case 'social_profile':
        return Share2;
      case 'website':
      case 'domain':
        return Globe;
      case 'mobile_app':
        return Smartphone;
      case 'image':
        return ImageIcon;
      default:
        return FileText;
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Digital Surface & Monitored Entities
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Unified ingestion and inspection across social networks, lookalike domains, and rogue APK apps.
          </p>
        </div>
        <Button variant="teal" onClick={() => setIsIngestOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Ingest / Submit Entity
        </Button>
      </div>

      {/* Filter Toolbar */}
      <Card className="p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          {/* Search box */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by display name, domain or canonical ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadEntities()}
              className="w-full rounded-lg border border-slate-800 bg-slate-900/80 py-2 pl-9 pr-4 text-sm text-slate-100 placeholder:text-slate-500 focus:border-teal-500 focus:outline-none"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Entity Type Filter */}
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-300 outline-none focus:border-teal-500"
            >
              <option value="">All Surfaces</option>
              <option value="social_profile">Social Profile</option>
              <option value="website">Website</option>
              <option value="domain">Domain</option>
              <option value="mobile_app">Mobile App</option>
              <option value="image">Image</option>
            </select>

            {/* Severity Filter */}
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-300 outline-none focus:border-teal-500"
            >
              <option value="">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            <Button variant="outline" size="sm" onClick={loadEntities}>
              <Filter className="mr-1.5 h-3.5 w-3.5" /> Filter
            </Button>
          </div>
        </div>
      </Card>

      {/* Entities Grid/List */}
      {isLoading ? (
        <div className="flex min-h-[40vh] items-center justify-center">
          <div className="h-7 w-7 animate-spin rounded-full border-4 border-teal-500 border-t-transparent" />
        </div>
      ) : entities.length === 0 ? (
        <Card className="p-12 text-center">
          <p className="text-slate-400">No entities found matching your filters.</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {entities.map((ent) => {
            const Icon = getEntityIcon(ent.entity_type);
            const colors = getSeverityColor(ent.current_severity);
            const prov = PROVENANCE_BADGES[ent.provenance] || PROVENANCE_BADGES.synthetic;

            return (
              <Card
                key={ent.id}
                className="hover:border-slate-700 cursor-pointer flex flex-col justify-between"
                onClick={() => openReview(ent)}
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2.5">
                      <div className="rounded-lg bg-slate-800 p-2 text-slate-300">
                        <Icon className="h-4 w-4" />
                      </div>
                      <div>
                        <h4 className="font-semibold text-slate-100 text-sm leading-tight line-clamp-1">
                          {ent.display_name}
                        </h4>
                        <span className="text-[11px] font-mono text-slate-400">
                          {ent.platform || ent.entity_type}
                        </span>
                      </div>
                    </div>
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold border ${colors.badge}`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${colors.indicator}`} />
                      <span className="capitalize">{ent.current_severity}</span>
                    </span>
                  </div>

                  <p className="text-xs font-mono text-slate-400 bg-slate-900/60 p-2 rounded border border-slate-800/80 truncate mb-3">
                    {ent.canonical_id}
                  </p>
                </div>

                <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono border ${prov.color}`}>
                      {prov.label}
                    </span>
                    <span className="text-slate-500 font-mono">
                      Risk: <strong className="text-slate-200">{formatScore(ent.current_risk_score)}</strong>
                    </span>
                  </div>

                  <span className="text-teal-400 hover:text-teal-300 flex items-center font-medium">
                    Review <ChevronRight className="h-3.5 w-3.5 ml-0.5" />
                  </span>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Review Modal */}
      {selectedEntity && (
        <Modal
          isOpen={isDetailOpen}
          onClose={() => setIsDetailOpen(false)}
          title={`Entity Review: ${selectedEntity.display_name}`}
          description={`Canonical: ${selectedEntity.canonical_id}`}
          maxWidth="2xl"
        >
          <div className="space-y-6">
            {/* Meta bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-slate-900/80 border border-slate-800">
              <div className="flex items-center gap-3">
                <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${getSeverityColor(selectedEntity.current_severity).badge}`}>
                  Severity: {selectedEntity.current_severity.toUpperCase()}
                </span>
                <span className="font-mono text-xs text-slate-300">
                  Risk Score: <strong>{formatScore(selectedEntity.current_risk_score)}</strong>
                </span>
                <span className="font-mono text-xs text-slate-400">
                  Confidence: {formatScore(selectedEntity.current_confidence)}
                </span>
              </div>
              <Button variant="teal" size="sm" onClick={handleCreateCase}>
                <Briefcase className="mr-1.5 h-3.5 w-3.5" />
                Open Investigation Case
              </Button>
            </div>

            {/* 4 Explainable Signal Cards */}
            <div>
              <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-3">
                Detection Signal Families (Explainable AI)
              </h4>
              <div className="space-y-3">
                {selectedAssessment?.signals && selectedAssessment.signals.length > 0 ? (
                  selectedAssessment.signals.map((sig) => (
                    <div
                      key={sig.id || sig.signal_type}
                      className="p-3.5 rounded-xl bg-[#090e1a] border border-slate-800 space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold text-slate-200">
                          {SIGNAL_TYPE_LABELS[sig.signal_type] || sig.signal_type}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] font-mono px-2 py-0.5 rounded uppercase ${
                            sig.status === 'ok' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-slate-800 text-slate-400'
                          }`}>
                            {sig.status}
                          </span>
                          <span className="font-mono text-xs font-bold text-teal-400">
                            Score: {formatScore(sig.score)}
                          </span>
                        </div>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">
                        {sig.explanation}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400 italic">No signals evaluated for this entity.</p>
                )}
              </div>
            </div>

            {/* Evidence Records */}
            <div>
              <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-3">
                Evidence Records ({entityEvidence.length})
              </h4>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {entityEvidence.map((ev) => (
                  <div key={ev.id} className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-slate-300 uppercase font-mono text-[10px]">
                        Kind: {ev.kind}
                      </span>
                      <span className="text-slate-500 font-mono text-[10px]">
                        {formatDate(ev.created_at)}
                      </span>
                    </div>
                    {ev.description && <p className="text-slate-300 mb-1">{ev.description}</p>}
                    {ev.text_content && (
                      <pre className="p-2 rounded bg-black/40 font-mono text-[11px] text-slate-400 overflow-x-auto whitespace-pre-wrap">
                        {ev.text_content}
                      </pre>
                    )}
                    {ev.url && (
                      <a href={ev.url} target="_blank" rel="noreferrer" className="text-teal-400 underline font-mono text-[11px]">
                        {ev.url}
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Modal>
      )}

      {/* Manual Ingestion Modal */}
      <Modal
        isOpen={isIngestOpen}
        onClose={() => setIsIngestOpen(false)}
        title="Ingest / Submit Suspicious Entity"
        description="Add a digital entity for heuristic risk detection and graph correlation"
      >
        <form onSubmit={handleIngestSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Surface Type</label>
            <select
              value={newEntity.entity_type}
              onChange={(e) => setNewEntity({ ...newEntity, entity_type: e.target.value as EntityType })}
              className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 outline-none focus:border-teal-500"
            >
              <option value="social_profile">Social Profile</option>
              <option value="website">Website</option>
              <option value="domain">Domain</option>
              <option value="mobile_app">Mobile App</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Platform / Service</label>
            <input
              type="text"
              required
              placeholder="e.g. Instagram, Telegram, Google Play, Namecheap"
              value={newEntity.platform}
              onChange={(e) => setNewEntity({ ...newEntity, platform: e.target.value })}
              className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 outline-none focus:border-teal-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Display Name</label>
            <input
              type="text"
              required
              placeholder="e.g. AcmeBank Official Customer Support"
              value={newEntity.display_name}
              onChange={(e) => setNewEntity({ ...newEntity, display_name: e.target.value })}
              className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 outline-none focus:border-teal-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Canonical ID / Handle / Domain</label>
            <input
              type="text"
              required
              placeholder="e.g. @acmebank_support or acmebank-login.xyz"
              value={newEntity.canonical_id}
              onChange={(e) => setNewEntity({ ...newEntity, canonical_id: e.target.value })}
              className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 outline-none focus:border-teal-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Source URL (Optional)</label>
            <input
              type="url"
              placeholder="https://..."
              value={newEntity.source_url}
              onChange={(e) => setNewEntity({ ...newEntity, source_url: e.target.value })}
              className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 outline-none focus:border-teal-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3">
            <Button type="button" variant="ghost" onClick={() => setIsIngestOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="teal">
              Submit & Run Detection
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

