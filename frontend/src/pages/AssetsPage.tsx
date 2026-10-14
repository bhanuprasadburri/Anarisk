import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  AtSign,
  Globe,
  Image as ImageIcon,
  Loader2,
  MoreVertical,
  Network,
  Plus,
  RefreshCw,
  SearchX,
  SlidersHorizontal,
  Smartphone,
  Eye,
  Trash2,
} from 'lucide-react';
import { PageHeader } from '../components/ui/page-header';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Badge, ProvenanceBadge, SeverityBadge } from '../components/ui/badge';
import { Modal, ConfirmDialog } from '../components/ui/modal';
import { Column, DataTable, EmptyState, ErrorState, Pagination } from '../components/ui/table';
import { Dropdown } from '../components/ui/tabs';
import { FilterSelect, SearchInput, Tooltip } from '../components/ui/misc';
import { ScoreBar } from '../components/ui/score';
import { Field, Input, Label, Select } from '../components/ui/input';
import { useToast } from '../components/ui/toast';
import { useAuth } from '../hooks/useAuth';
import { entityService } from '../services/entityService';
import { ApiError } from '../services/apiClient';
import { DigitalEntity } from '../types';
import { ENTITY_TYPE_COLORS, ENTITY_TYPE_LABELS, SEVERITY_LABELS } from '../lib/constants';
import { formatDate, formatRelativeTime } from '../lib/formatters';
import { cn, truncate } from '../lib/utils';

/* ---------------- shared small bits ---------------- */

const TYPE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  social_profile: AtSign,
  website: Globe,
  domain: Network,
  image: ImageIcon,
  mobile_app: Smartphone,
};

export const EntityTypeChip: React.FC<{ type: string; size?: 'sm' | 'md' }> = ({ type, size = 'sm' }) => {
  const Icon = TYPE_ICONS[type] || Globe;
  const color = ENTITY_TYPE_COLORS[type] || '#4778F5';
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center justify-center rounded-xl',
        size === 'sm' ? 'h-8 w-8' : 'h-11 w-11'
      )}
      style={{ backgroundColor: `${color}1A`, color }}
      aria-hidden="true"
    >
      <Icon className={size === 'sm' ? 'h-4 w-4' : 'h-5 w-5'} />
    </span>
  );
};

/* ---------------- sort options ---------------- */

const SORT_OPTIONS = [
  { value: 'last_seen_at', label: 'Last Seen' },
  { value: 'risk_score', label: 'Risk Score' },
  { value: 'display_name', label: 'Name' },
  { value: 'first_seen_at', label: 'First Seen' },
];

const DEFAULT_SORT = 'last_seen_at';
const DEFAULT_ORDER: 'asc' | 'desc' = 'desc';
const PAGE_SIZES = [10, 20, 50, 100];

/* ---------------- add-asset attribute model ---------------- */

interface AttrRow {
  id: number;
  key: string;
  value: string;
}

const ATTR_HINTS: Record<string, Array<{ key: string; required?: boolean; hint: string }>> = {
  website: [
    { key: 'url', required: true, hint: 'https://example-clone.com' },
    { key: 'page_title', hint: 'Page title text' },
    { key: 'registered_at', hint: 'ISO date, e.g. 2024-01-15' },
  ],
  domain: [
    { key: 'domain', required: true, hint: 'example-clone.com' },
    { key: 'registered_at', hint: 'ISO date, e.g. 2024-01-15' },
  ],
  social_profile: [
    { key: 'handle', required: true, hint: '@username' },
    { key: 'bio', hint: 'Profile bio text' },
    { key: 'followers_count', hint: 'number, e.g. 1200' },
    { key: 'account_created_at', hint: 'ISO date, e.g. 2023-06-01' },
  ],
  mobile_app: [
    { key: 'package_id', required: true, hint: 'com.example.app' },
    { key: 'app_name', required: true, hint: 'App listing name' },
    { key: 'store', hint: 'google_play | app_store | other' },
    { key: 'publisher_name', hint: 'Publisher on the store' },
    { key: 'store_url', hint: 'https://… store listing' },
  ],
  image: [
    { key: 'phash', hint: '16 hex chars (or provide sha256)' },
    { key: 'sha256', hint: '64 hex chars' },
  ],
};

const ATTR_DESCRIPTIONS: Record<string, string> = {
  website: 'A website needs a url; optionally add page_title.',
  domain: 'A domain needs a bare domain, e.g. evil-clone.com.',
  social_profile: 'A social profile needs a handle (and a platform above); optionally bio + followers_count.',
  mobile_app: 'A mobile app needs package_id and app_name; pick a store above.',
  image: 'An image needs a perceptual hash (phash) or a sha256 checksum.',
};

const REQUIRED_ATTR_KEYS: Record<string, string[]> = {
  website: ['url'],
  domain: ['domain'],
  social_profile: ['handle'],
  mobile_app: ['package_id', 'app_name'],
  image: [],
};

const NUMERIC_ATTR_KEYS = new Set(['followers_count', 'following_count']);
const LIST_ATTR_KEYS = new Set(['links', 'permissions', 'linked_websites', 'image_phashes', 'post_timestamps']);

/** Coerce a raw editor string into a JSON-ish value the API expects. */
function coerceAttrValue(key: string, raw: string): unknown {
  const trimmed = raw.trim();
  if (LIST_ATTR_KEYS.has(key)) return trimmed.split(',').map((s) => s.trim()).filter(Boolean);
  if (NUMERIC_ATTR_KEYS.has(key)) {
    const n = Number(trimmed);
    return Number.isFinite(n) ? Math.max(0, Math.trunc(n)) : trimmed;
  }
  if (/^[[{].*[\]}]$/.test(trimmed) || trimmed === 'true' || trimmed === 'false' || /^-?\d+(\.\d+)?$/.test(trimmed)) {
    try {
      return JSON.parse(trimmed);
    } catch {
      /* keep as string */
    }
  }
  return trimmed;
}

function formatApiDetails(details: unknown): string[] {
  if (!Array.isArray(details)) return [];
  return details
    .map((d: any) => {
      const field = d?.field || (Array.isArray(d?.loc) ? d.loc.join('.') : '');
      const msg = d?.message || d?.msg || '';
      return field && msg ? `${field}: ${msg}` : msg || field;
    })
    .filter(Boolean);
}

/* ---------------- page ---------------- */

export const AssetsPage: React.FC = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { role, brands, activeBrand, hasPermission } = useAuth();

  /* ----- URL-backed state ----- */
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get('q') || '';
  const type = searchParams.get('type') || '';
  const severity = searchParams.get('severity') || '';
  const brand = searchParams.get('brand') || '';
  const sort = searchParams.get('sort') || DEFAULT_SORT;
  const order: 'asc' | 'desc' = searchParams.get('order') === 'asc' ? 'asc' : DEFAULT_ORDER;
  const page = Math.max(1, parseInt(searchParams.get('page') || '1', 10) || 1);
  const rawPageSize = parseInt(searchParams.get('page_size') || '20', 10);
  const pageSize = PAGE_SIZES.includes(rawPageSize) ? rawPageSize : 20;

  const updateParams = useCallback(
    (patch: Record<string, string | number | undefined>, resetPage = true) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          for (const [k, v] of Object.entries(patch)) {
            if (v === undefined || v === '') next.delete(k);
            else next.set(k, String(v));
          }
          if (resetPage && !('page' in patch)) next.delete('page');
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  const hasActiveFilters = !!(q || type || severity || brand);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const showFilters = filtersOpen || hasActiveFilters;

  const clearFilters = useCallback(() => {
    updateParams({ q: '', type: '', severity: '', brand: '' });
  }, [updateParams]);

  /* ----- data ----- */
  const [data, setData] = useState<{ items: DigitalEntity[]; total: number; page: number; pages: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    entityService
      .listEntities({
        q: q || undefined,
        entity_type: type || undefined,
        severity: severity || undefined,
        brand_id: brand || undefined,
        sort,
        order,
        page,
        page_size: pageSize,
      })
      .then((res) => {
        if (cancelled) return;
        setData({ items: res.items || [], total: res.total || 0, page: res.page || page, pages: res.pages || 1 });
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : 'We could not load your digital assets.');
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [q, type, severity, brand, sort, order, page, pageSize, reload]);

  const refetch = useCallback(() => setReload((r) => r + 1), []);

  /* ----- row actions ----- */
  const canDelete = hasPermission('entity:submit') || role === 'administrator';
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);
  const [deletingEntity, setDeletingEntity] = useState<DigitalEntity | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  const handleReanalyze = useCallback(
    async (entity: DigitalEntity) => {
      setAnalyzingId(entity.id);
      try {
        await entityService.analyzeEntity(entity.id);
        toast.success('Re-analysis complete', `${entity.display_name} has been re-scored.`);
        refetch();
      } catch (err) {
        toast.error('Re-analysis failed', err instanceof ApiError ? err.message : 'Unexpected error.');
      } finally {
        setAnalyzingId(null);
      }
    },
    [toast, refetch]
  );

  const handleDelete = useCallback(async () => {
    const entity = deletingEntity;
    if (!entity) return;
    setDeleteBusy(true);
    try {
      await entityService.deleteEntity(entity.id);
      toast.success('Asset deleted', `${entity.display_name} was removed.`);
      setDeletingEntity(null);
      refetch();
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Unexpected error.';
      toast.error(err instanceof ApiError && err.status === 403 ? 'Not allowed to delete' : 'Delete failed', msg);
      setDeletingEntity(null);
    } finally {
      setDeleteBusy(false);
    }
  }, [deletingEntity, toast, refetch]);

  /* ----- sorting ----- */
  const handleSortChange = useCallback(
    (key: string) => {
      if (sort === key) {
        updateParams({ order: order === 'asc' ? 'desc' : 'asc' });
      } else {
        updateParams({ sort: key, order: key === 'display_name' ? 'asc' : 'desc' });
      }
    },
    [sort, order, updateParams]
  );

  /* ----- add asset modal ----- */
  const rowIdRef = useRef(1);
  const [addOpen, setAddOpen] = useState(false);
  const [form, setForm] = useState({ brand_id: '', entity_type: '', display_name: '', platform: '', source_url: '' });
  const [attrRows, setAttrRows] = useState<AttrRow[]>([]);
  const [formErrors, setFormErrors] = useState<Record<string, string | null>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const openAddModal = useCallback(() => {
    setForm({
      brand_id: activeBrand?.id || brands[0]?.id || '',
      entity_type: '',
      display_name: '',
      platform: '',
      source_url: '',
    });
    setAttrRows([]);
    setFormErrors({});
    setSubmitError(null);
    setAddOpen(true);
  }, [activeBrand, brands]);

  const addAttrRow = useCallback((key = '') => {
    setAttrRows((rows) => [...rows, { id: rowIdRef.current++, key, value: '' }]);
  }, []);

  const updateAttrRow = useCallback((id: number, patch: Partial<AttrRow>) => {
    setAttrRows((rows) => rows.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  }, []);

  const removeAttrRow = useCallback((id: number) => {
    setAttrRows((rows) => rows.filter((r) => r.id !== id));
  }, []);

  const handleSubmit = useCallback(async () => {
    const errs: Record<string, string | null> = {};
    if (!form.brand_id) errs.brand_id = 'Select a brand.';
    if (!form.entity_type) errs.entity_type = 'Select an asset type.';
    if (!form.display_name.trim()) errs.display_name = 'Display name is required.';
    if (form.entity_type === 'social_profile' && !form.platform.trim()) {
      errs.platform = 'Platform is required for social profiles.';
    }
    if (form.source_url.trim() && !/^https?:\/\/\S+$/i.test(form.source_url.trim())) {
      errs.source_url = 'Must be a valid http(s) URL.';
    }
    const presentKeys = new Set(attrRows.filter((r) => r.key.trim() && r.value.trim()).map((r) => r.key.trim()));
    for (const rk of REQUIRED_ATTR_KEYS[form.entity_type] || []) {
      if (!presentKeys.has(rk)) {
        errs[`attr:${rk}`] = `The "${rk}" attribute is required for ${ENTITY_TYPE_LABELS[form.entity_type] || 'this asset type'}.`;
      }
    }
    if (form.entity_type === 'image' && !presentKeys.has('phash') && !presentKeys.has('sha256')) {
      errs['attr:phash'] = 'Provide a phash (16 hex chars) or a sha256 for image assets.';
    }
    setFormErrors(errs);
    if (Object.values(errs).some(Boolean)) return;

    const attributes: Record<string, unknown> = {};
    for (const row of attrRows) {
      const k = row.key.trim();
      if (!k || !row.value.trim()) continue;
      attributes[k] = coerceAttrValue(k, row.value);
    }

    setSubmitting(true);
    setSubmitError(null);
    try {
      // backend returns { entity, created, matches_official_reference, assessment } — surface `created` defensively
      const res = (await entityService.submitEntity({
        brand_id: form.brand_id,
        entity_type: form.entity_type,
        display_name: form.display_name.trim(),
        platform: form.platform.trim() || undefined,
        source_url: form.source_url.trim() || undefined,
        attributes,
        analyze: true,
      })) as { entity: DigitalEntity; created?: boolean };
      toast.success(
        res.created ? 'Asset added' : 'Asset updated',
        res.created
          ? `${res.entity.display_name} was saved and queued for analysis.`
          : 'Merged into the existing asset record and queued for analysis.'
      );
      setAddOpen(false);
      updateParams({}, true); // back to page 1
      refetch();
    } catch (err) {
      if (err instanceof ApiError && (err.status === 409 || err.status === 422)) {
        const details = formatApiDetails(err.details);
        setSubmitError(details.length ? `${err.message}. ${details.join(' · ')}` : err.message);
      } else {
        setSubmitError(err instanceof ApiError ? err.message : 'Unexpected error while saving the asset.');
      }
    } finally {
      setSubmitting(false);
    }
  }, [form, attrRows, toast, updateParams, refetch]);

  /* ----- table columns ----- */
  const columns: Column<DigitalEntity>[] = useMemo(
    () => [
      {
        key: 'display_name',
        header: 'Name / Identifier',
        sortable: true,
        className: 'min-w-[240px]',
        cell: (e) => (
          <div className="flex items-center gap-3">
            <EntityTypeChip type={e.entity_type} />
            <div className="min-w-0">
              <p className="truncate text-[13px] font-bold text-ink">{e.display_name}</p>
              <p className="truncate font-mono text-[11px] text-faint">{truncate(e.canonical_id, 38)}</p>
            </div>
          </div>
        ),
      },
      {
        key: 'type',
        header: 'Type',
        cell: (e) => (
          <Badge tone="outline">
            <span
              className="h-1.5 w-1.5 rounded-full"
              style={{ backgroundColor: ENTITY_TYPE_COLORS[e.entity_type] || '#4778F5' }}
            />
            {ENTITY_TYPE_LABELS[e.entity_type] || e.entity_type}
          </Badge>
        ),
      },
      {
        key: 'risk_score',
        header: 'Risk Score',
        sortable: true,
        className: 'min-w-[150px]',
        cell: (e) =>
          e.current_risk_score === null || e.current_risk_score === undefined ? (
            <span className="text-xs font-medium text-faint">Not assessed</span>
          ) : (
            <ScoreBar value={e.current_risk_score} severity={e.current_severity} />
          ),
      },
      {
        key: 'severity',
        header: 'Severity',
        cell: (e) => <SeverityBadge severity={e.current_severity} />,
      },
      {
        key: 'last_seen_at',
        header: 'Last Seen',
        sortable: true,
        cell: (e) => (
          <Tooltip content={formatDate(e.last_seen_at)}>
            <span className="whitespace-nowrap text-[13px] text-muted">{formatRelativeTime(e.last_seen_at)}</span>
          </Tooltip>
        ),
      },
      {
        key: 'provenance',
        header: 'Source',
        cell: (e) => <ProvenanceBadge provenance={e.provenance} />,
      },
      {
        key: 'actions',
        header: '',
        headerClassName: 'w-12',
        className: 'text-right',
        cell: (e) => (
          <div onClick={(ev) => ev.stopPropagation()}>
            <Dropdown
              align="right"
              trigger={({ open: ddOpen }) => (
                <button
                  aria-label={`Actions for ${e.display_name}`}
                  aria-haspopup="menu"
                  className={cn(
                    'rounded-lg p-1.5 transition-colors focus-ring',
                    ddOpen ? 'bg-brand-50 text-brand-600' : 'text-faint hover:bg-line-soft hover:text-ink'
                  )}
                >
                  <MoreVertical className="h-4 w-4" />
                </button>
              )}
              items={[
                {
                  label: 'View details',
                  icon: <Eye className="h-3.5 w-3.5" />,
                  onClick: () => navigate(`/entities/${e.id}`),
                },
                {
                  label: analyzingId === e.id ? 'Re-analyzing…' : 'Re-analyze',
                  icon:
                    analyzingId === e.id ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <RefreshCw className="h-3.5 w-3.5" />
                    ),
                  disabled: analyzingId !== null,
                  onClick: () => void handleReanalyze(e),
                },
                ...(canDelete
                  ? [
                      {
                        label: 'Delete',
                        icon: <Trash2 className="h-3.5 w-3.5" />,
                        danger: true,
                        separatorBefore: true,
                        onClick: () => setDeletingEntity(e),
                      },
                    ]
                  : []),
              ]}
            />
          </div>
        ),
      },
    ],
    [navigate, analyzingId, canDelete, handleReanalyze]
  );

  /* ----- derived UI bits ----- */
  const brandOptions = useMemo(() => brands.map((b) => ({ value: b.id, label: b.name })), [brands]);
  const typeOptions = useMemo(
    () => Object.entries(ENTITY_TYPE_LABELS).map(([value, label]) => ({ value, label })),
    []
  );
  const severityOptions = useMemo(
    () => Object.entries(SEVERITY_LABELS).map(([value, label]) => ({ value, label })),
    []
  );

  const emptyState = hasActiveFilters ? (
    <EmptyState
      icon={<SearchX className="h-6 w-6" />}
      title="No assets found"
      description="No digital assets match the current search and filters. Try a broader search or clear the filters."
      action={
        <div className="flex items-center gap-2.5">
          <Button variant="outline" size="sm" onClick={clearFilters}>
            Clear filters
          </Button>
          <Button size="sm" icon={<Plus className="h-4 w-4" />} onClick={openAddModal}>
            Add Asset
          </Button>
        </div>
      }
    />
  ) : (
    <EmptyState
      icon={<Globe className="h-6 w-6" />}
      title="No assets yet"
      description="Add your first digital asset — a profile, website, domain, image or mobile app — to start monitoring for brand abuse."
      action={
        <Button icon={<Plus className="h-4 w-4" />} onClick={openAddModal}>
          Add your first asset
        </Button>
      }
    />
  );

  return (
    <div>
      <PageHeader
        title="Digital Assets"
        description="Explore and manage your monitored digital assets."
        actions={
          <>
            <Button
              variant="outline"
              icon={<SlidersHorizontal className="h-4 w-4" />}
              onClick={() => setFiltersOpen((v) => !v)}
              aria-expanded={showFilters}
            >
              Filter
            </Button>
            <Button icon={<Plus className="h-4 w-4" />} onClick={openAddModal}>
              Add Asset
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center">
            <SearchInput
              value={q}
              onChange={(v) => updateParams({ q: v })}
              placeholder="Search by name, URL, domain, or identifier…"
              debounceMs={300}
              className="w-full sm:w-96"
            />
            {hasActiveFilters && (
              <Button variant="ghost" size="sm" onClick={clearFilters}>
                Clear filters
              </Button>
            )}
          </div>
          {showFilters && (
            <div className="flex flex-wrap items-center gap-2.5 rounded-2xl border border-line bg-surface p-3 shadow-card">
              <FilterSelect
                label="Entity type"
                allLabel="All types"
                value={type}
                options={typeOptions}
                onChange={(v) => updateParams({ type: v })}
              />
              <FilterSelect
                label="Risk severity"
                allLabel="All severities"
                value={severity}
                options={severityOptions}
                onChange={(v) => updateParams({ severity: v })}
              />
              <FilterSelect
                label="Brand"
                allLabel="All brands"
                value={brand}
                options={brandOptions}
                onChange={(v) => updateParams({ brand: v })}
              />
              <FilterSelect
                label="Sort by"
                allLabel="Sort By"
                value={sort}
                options={SORT_OPTIONS}
                onChange={(v) =>
                  updateParams({ sort: v || DEFAULT_SORT, order: (v || DEFAULT_SORT) === 'display_name' ? 'asc' : 'desc' })
                }
              />
            </div>
          )}
        </div>
      </PageHeader>

      <Card>
        {error ? (
          <div className="px-5 py-10">
            <ErrorState title="Could not load assets" message={error} onRetry={refetch} />
          </div>
        ) : (
          <>
            <DataTable<DigitalEntity>
              columns={columns}
              rows={data?.items || []}
              rowKey={(e) => e.id}
              sort={sort}
              order={order}
              onSortChange={handleSortChange}
              onRowClick={(e) => navigate(`/entities/${e.id}`)}
              loading={loading}
              emptyState={emptyState}
            />
            {data && (data.pages > 1 || data.total > 0) && (
              <div className="border-t border-line-soft">
                <Pagination
                  page={data.page}
                  pages={data.pages}
                  total={data.total}
                  onPageChange={(p) => updateParams({ page: p }, false)}
                  pageSize={pageSize}
                  onPageSizeChange={(s) => updateParams({ page_size: s })}
                />
              </div>
            )}
          </>
        )}
      </Card>

      {/* ----- Add asset modal ----- */}
      <Modal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        title="Add Asset"
        description="Submit a profile, website, domain, image or mobile app for monitoring. Duplicates merge into the existing record."
        size="lg"
        closeOnBackdrop={false}
        footer={
          <>
            <Button variant="outline" onClick={() => setAddOpen(false)} disabled={submitting}>
              Cancel
            </Button>
            <Button type="submit" form="add-asset-form" loading={submitting}>
              {submitting ? 'Saving…' : 'Add & Analyze'}
            </Button>
          </>
        }
      >
        <form
          id="add-asset-form"
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            void handleSubmit();
          }}
        >
          {submitError && (
            <div className="rounded-xl border border-danger-200 bg-danger-100/60 px-3.5 py-2.5 text-[13px] font-medium text-danger-600">
              {submitError}
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Brand" required error={formErrors.brand_id} htmlFor="asset-brand">
              <Select
                id="asset-brand"
                value={form.brand_id}
                invalid={!!formErrors.brand_id}
                onChange={(e) => setForm((f) => ({ ...f, brand_id: e.target.value }))}
              >
                <option value="">Select a brand…</option>
                {brands.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </Select>
            </Field>

            <Field label="Entity type" required error={formErrors.entity_type} htmlFor="asset-type">
              <Select
                id="asset-type"
                value={form.entity_type}
                invalid={!!formErrors.entity_type}
                onChange={(e) => {
                  setForm((f) => ({ ...f, entity_type: e.target.value }));
                  setFormErrors((er) => ({ ...er, entity_type: null }));
                }}
              >
                <option value="">Select a type…</option>
                {Object.entries(ENTITY_TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
            </Field>

            <Field label="Display name" required error={formErrors.display_name} htmlFor="asset-name">
              <Input
                id="asset-name"
                value={form.display_name}
                className={cn(formErrors.display_name && 'border-danger')}
                placeholder="e.g. AcmeBank Support"
                onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
              />
            </Field>

            <Field
              label="Platform"
              required={form.entity_type === 'social_profile'}
              error={formErrors.platform}
              hint={form.entity_type === 'social_profile' ? 'Required for social profiles.' : 'Optional.'}
              htmlFor="asset-platform"
            >
              <Input
                id="asset-platform"
                value={form.platform}
                className={cn(formErrors.platform && 'border-danger')}
                placeholder="e.g. x, instagram, tiktok"
                onChange={(e) => setForm((f) => ({ ...f, platform: e.target.value }))}
              />
            </Field>
          </div>

          <Field
            label="Source URL"
            error={formErrors.source_url}
            hint="Optional. Must be a valid http(s) URL if provided."
            htmlFor="asset-url"
          >
            <Input
              id="asset-url"
              type="url"
              value={form.source_url}
              className={cn(formErrors.source_url && 'border-danger')}
              placeholder="https://…"
              onChange={(e) => setForm((f) => ({ ...f, source_url: e.target.value }))}
            />
          </Field>

          <div className="rounded-xl border border-line-soft bg-bg/60 p-3.5">
            <div className="mb-2.5 flex items-center justify-between gap-3">
              <Label className="mb-0">Attributes</Label>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                icon={<Plus className="h-3.5 w-3.5" />}
                onClick={() => addAttrRow()}
              >
                Add attribute
              </Button>
            </div>

            {form.entity_type && ATTR_HINTS[form.entity_type] && (
              <p className="mb-2.5 text-xs text-faint">{ATTR_DESCRIPTIONS[form.entity_type]}</p>
            )}

            {attrRows.length === 0 ? (
              <p className="mb-2.5 text-xs text-faint">
                No attributes yet. Add key/value pairs below — suggested keys for the selected asset type appear
                underneath.
              </p>
            ) : (
              <div className="space-y-2">
                {attrRows.map((row, i) => {
                  const rowError = formErrors[`attr:${row.key.trim()}`];
                  return (
                    <div key={row.id}>
                      <div className="flex items-center gap-2">
                        <Input
                          value={row.key}
                          placeholder="key"
                          aria-label={`Attribute ${i + 1} key`}
                          className="h-9 flex-1 font-mono text-[13px]"
                          onChange={(e) => updateAttrRow(row.id, { key: e.target.value })}
                        />
                        <Input
                          value={row.value}
                          placeholder="value"
                          aria-label={`Attribute ${i + 1} value`}
                          className="h-9 flex-[1.6] text-[13px]"
                          onChange={(e) => updateAttrRow(row.id, { value: e.target.value })}
                        />
                        <button
                          type="button"
                          aria-label={`Remove attribute ${i + 1}`}
                          onClick={() => removeAttrRow(row.id)}
                          className="shrink-0 rounded-lg p-1.5 text-faint transition-colors hover:bg-danger-100 hover:text-danger focus-ring"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                      {rowError && <p className="mt-1 text-xs font-medium text-danger">{rowError}</p>}
                    </div>
                  );
                })}
              </div>
            )}

            {form.entity_type && ATTR_HINTS[form.entity_type] && (
              <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-line-soft pt-3">
                <span className="text-xs text-faint">Suggested keys:</span>
                {ATTR_HINTS[form.entity_type].map((h) => (
                  <button
                    type="button"
                    key={h.key}
                    title={h.hint}
                    onClick={() => addAttrRow(h.key)}
                    className="rounded-full border border-line bg-white px-2.5 py-1 text-[11px] font-semibold text-ink-700 transition-colors hover:border-brand-200 hover:text-brand-700 focus-ring"
                  >
                    {h.key}
                    {h.required && <span className="ml-0.5 text-danger">*</span>}
                  </button>
                ))}
              </div>
            )}
          </div>
        </form>
      </Modal>

      {/* ----- delete confirm ----- */}
      <ConfirmDialog
        open={!!deletingEntity}
        onClose={() => setDeletingEntity(null)}
        onConfirm={handleDelete}
        loading={deleteBusy}
        destructive
        title="Delete asset"
        confirmLabel="Delete"
        message={
          <>
            Delete <span className="font-semibold text-ink">{deletingEntity?.display_name}</span> and its linked evidence?
            This cannot be undone. Linked cases keep their history.
          </>
        }
      />
    </div>
  );
};

export default AssetsPage;
