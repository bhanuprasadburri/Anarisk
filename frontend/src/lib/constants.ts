export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const ENTITY_TYPE_LABELS: Record<string, string> = {
  social_profile: 'Social Profile',
  website: 'Website',
  domain: 'Domain',
  image: 'Image',
  mobile_app: 'Mobile App',
};

export const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#f59e0b',
  low: '#3b82f6',
  unknown: '#64748b',
};

export const CASE_STATUS_LABELS: Record<string, string> = {
  detected: 'Detected',
  triaged: 'Triaged',
  under_review: 'Under Review',
  assigned: 'Assigned',
  escalated: 'Escalated',
  resolved: 'Resolved',
};

export const RELATIONSHIP_LABELS: Record<string, string> = {
  shares_image: 'Shares Visual / Logo',
  shares_domain: 'Links to Same Domain',
  similar_identity: 'Similar Identity / Name',
  same_infrastructure: 'Shared Infrastructure / IP',
  coordinated_behavior: 'Coordinated Activity',
};

export const SIGNAL_TYPE_LABELS: Record<string, string> = {
  brand_logo: 'Brand & Logo Similarity',
  impersonation: 'Impersonation & Bio Copying',
  url_risk: 'Suspicious Links & Domains',
  behavior: 'Account Age & Coordination',
};

export const RESOLUTION_OUTCOME_LABELS: Record<string, string> = {
  confirmed_threat_actioned: 'Confirmed Threat (Actioned)',
  confirmed_threat_monitoring: 'Confirmed Threat (Monitoring)',
  false_positive: 'False Positive',
  inconclusive: 'Inconclusive',
  duplicate: 'Duplicate Case',
};

export const PROVENANCE_BADGES: Record<string, { label: string; desc: string; color: string }> = {
  collected: {
    label: 'Collected',
    desc: 'Automated ingestion from active store/platform connector',
    color: 'bg-emerald-950/80 text-emerald-300 border-emerald-700/60',
  },
  manual: {
    label: 'Manual',
    desc: 'Manually submitted by security analyst',
    color: 'bg-indigo-950/80 text-indigo-300 border-indigo-700/60',
  },
  synthetic: {
    label: 'Synthetic Demo',
    desc: 'Fictional demo data generated for validation',
    color: 'bg-amber-950/80 text-amber-300 border-amber-700/60',
  },
};

export const DEMO_ACCOUNTS = [
  {
    role: 'administrator',
    email: 'admin@nimbus.example',
    name: 'Sarah Connor',
    label: 'Security Admin',
    desc: 'Full system visibility, user management, scoring configuration',
  },
  {
    role: 'investigator',
    email: 'investigator@nimbus.example',
    name: 'Alex Vance',
    label: 'Lead Investigator',
    desc: 'Entity review, graph exploration, case management & assignments',
  },
  {
    role: 'brand_owner',
    email: 'owner@nimbus.example',
    name: 'David Acme',
    label: 'Brand Owner (AcmeBank)',
    desc: 'Monitored brand overview, official asset management, threat view',
  },
  {
    role: 'partner',
    email: 'partner@nimbus.example',
    name: 'Elena Rostova',
    label: 'Legal / Partner',
    desc: 'Access to escalated cases only for external takedown action',
  },
];
