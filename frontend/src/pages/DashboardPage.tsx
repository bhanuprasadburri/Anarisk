import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldAlert,
  AlertTriangle,
  Briefcase,
  Network,
  Smartphone,
  ExternalLink,
  ArrowRight,
  TrendingUp,
  Globe,
  Radio,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { dashboardService } from '../services/dashboardService';
import { entityService } from '../services/entityService';
import { DashboardStats, MobileAppsSummary, DigitalEntity } from '../types';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { formatScore } from '../lib/formatters';
import { getSeverityColor } from '../lib/utils';
import { ENTITY_TYPE_LABELS, PROVENANCE_BADGES } from '../lib/constants';

export const DashboardPage: React.FC = () => {
  const { activeBrand } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [mobileApps, setMobileApps] = useState<MobileAppsSummary | null>(null);
  const [recentEntities, setRecentEntities] = useState<DigitalEntity[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const [statsData, appsData, entitiesData] = await Promise.all([
          dashboardService.getStats(activeBrand?.id),
          dashboardService.getMobileApps(activeBrand?.id),
          entityService.listEntities({ page_size: 5 }),
        ]);
        setStats(statsData);
        setMobileApps(appsData);
        setRecentEntities(entitiesData.items);
      } catch (err) {
        console.error('Failed to load dashboard data', err);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [activeBrand]);

  if (isLoading || !stats) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-500 border-t-transparent" />
          <p className="text-sm font-mono text-slate-400">Loading risk intelligence...</p>
        </div>
      </div>
    );
  }

  const criticalCount = stats.risk_distribution?.critical || 0;
  const highCount = stats.risk_distribution?.high || 0;

  return (
    <div className="space-y-8 pb-12">
      {/* Top Banner */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Risk Intelligence Center
            </h1>
            <span className="flex items-center gap-1 text-xs font-mono px-2 py-0.5 rounded-full bg-teal-500/10 text-teal-300 border border-teal-500/30">
              <Radio className="h-3 w-3 animate-pulse text-teal-400" />
              Active Monitoring
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-400">
            Digital surface monitoring, multi-signal threat detection & coordinated attack graphs for{' '}
            <span className="font-semibold text-slate-200">{activeBrand?.name || 'AcmeBank'}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => navigate('/graph')}>
            <Network className="mr-2 h-4 w-4 text-teal-400" />
            Explore Graph
          </Button>
          <Button variant="teal" size="sm" onClick={() => navigate('/cases')}>
            <Briefcase className="mr-2 h-4 w-4" />
            Manage Cases ({stats.totals.open_cases})
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {/* Card 1: Tracked Entities */}
        <Card className="hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400">
              Monitored Entities
            </span>
            <div className="rounded-lg bg-teal-500/10 p-2 text-teal-400">
              <Globe className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight text-white">
              {stats.totals.monitored_entities}
            </span>
            <span className="text-xs text-slate-400 font-mono">active records</span>
          </div>
          <p className="mt-2 text-xs text-slate-400">
            Across social, web domains, and mobile store listings
          </p>
        </Card>

        {/* Card 2: Critical Threats */}
        <Card className="hover:border-red-900/60 transition-all border-red-900/30 bg-gradient-to-br from-[#0d1424] to-red-950/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-red-300">
              Active Threats (Crit / High)
            </span>
            <div className="rounded-lg bg-red-500/20 p-2 text-red-400">
              <AlertTriangle className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight text-red-400">
              {stats.totals.high_risk_entities}
            </span>
            <span className="text-xs text-red-300/70 font-mono">
              ({criticalCount} crit, {highCount} high)
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-400">
            Exceeding calibrated detection thresholds
          </p>
        </Card>

        {/* Card 3: Connected Clusters */}
        <Card className="hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400">
              Escalated to Partners
            </span>
            <div className="rounded-lg bg-indigo-500/10 p-2 text-indigo-400">
              <Network className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight text-white">
              {stats.totals.escalated_cases}
            </span>
            <span className="text-xs text-indigo-300 font-mono">handoffs active</span>
          </div>
          <p className="mt-2 text-xs text-slate-400">
            Registrar / App Store / Legal takedown actions
          </p>
        </Card>

        {/* Card 4: Open Investigations */}
        <Card className="hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400">
              Investigation Workflow
            </span>
            <div className="rounded-lg bg-cyan-500/10 p-2 text-cyan-400">
              <Briefcase className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight text-white">
              {stats.totals.open_cases}
            </span>
            <span className="text-xs text-slate-400 font-mono">
              / {stats.totals.resolved_cases} resolved
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-400">
            Human-in-the-loop review with audit trail
          </p>
        </Card>
      </div>

      {/* Surface Breakdown & Mobile Apps */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left 2 Cols: Surface Distribution & Severity */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-teal-400" />
              Digital Attack Surface Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              {/* By Entity Type */}
              <div className="space-y-3">
                <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400">
                  By Surface Type
                </h4>
                <div className="space-y-2">
                  {Object.entries(stats.entity_type_distribution || {}).map(([type, count]) => (
                    <div key={type} className="flex items-center justify-between p-2 rounded-lg bg-slate-900/60 border border-slate-800/80">
                      <span className="text-sm font-medium text-slate-300">
                        {ENTITY_TYPE_LABELS[type] || type}
                      </span>
                      <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-teal-300">
                        {count}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* By Severity */}
              <div className="space-y-3">
                <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400">
                  By Risk Severity
                </h4>
                <div className="space-y-2">
                  {['critical', 'high', 'medium', 'low'].map((sev) => {
                    const count = stats.risk_distribution?.[sev] || 0;
                    const colors = getSeverityColor(sev);
                    return (
                      <div key={sev} className="flex items-center justify-between p-2 rounded-lg bg-slate-900/60 border border-slate-800/80">
                        <div className="flex items-center gap-2">
                          <span className={`h-2.5 w-2.5 rounded-full ${colors.indicator}`} />
                          <span className="text-sm capitalize font-medium text-slate-300">{sev}</span>
                        </div>
                        <span className={`font-mono text-xs font-semibold px-2 py-0.5 rounded border ${colors.badge}`}>
                          {count}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Right Col: Mobile Apps Summary */}
        <Card className="flex flex-col justify-between">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Smartphone className="h-5 w-5 text-amber-400" />
                Mobile App Surface
              </span>
              <span className="text-xs font-mono font-normal text-amber-400">
                {mobileApps?.high_risk_count || 0} Suspicious
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-xs text-slate-400 leading-relaxed">
              Third-party APK store listings & Google Play clones targeting brand customers. Permissions & publisher identities are flagged as supplied-unverified.
            </p>
            <div className="rounded-xl bg-amber-950/20 border border-amber-900/40 p-3 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-amber-200">Total Monitored Apps</span>
                <span className="font-mono font-bold text-amber-300">{mobileApps?.total_monitored || 1}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-red-300">Unverified Publisher Apps</span>
                <span className="font-mono font-bold text-red-400">{mobileApps?.high_risk_count || 1}</span>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="w-full justify-between"
              onClick={() => navigate('/entities?type=mobile_app')}
            >
              <span>View Mobile App Findings</span>
              <ArrowRight className="h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Recent Threats Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg">High-Risk Active Findings</CardTitle>
            <p className="text-xs text-slate-400 mt-1">
              Top identified impersonation targets requiring review or case escalation
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={() => navigate('/entities')}>
            View All Entities <ArrowRight className="ml-1.5 h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-800 text-xs font-mono uppercase text-slate-400">
                <tr>
                  <th className="pb-3 pl-2">Display Name / Target</th>
                  <th className="pb-3">Surface Type</th>
                  <th className="pb-3">Provenance</th>
                  <th className="pb-3">Risk Score</th>
                  <th className="pb-3">Severity</th>
                  <th className="pb-3 text-right pr-2">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {recentEntities.map((ent) => {
                  const colors = getSeverityColor(ent.current_severity);
                  const prov = PROVENANCE_BADGES[ent.provenance] || PROVENANCE_BADGES.synthetic;
                  return (
                    <tr key={ent.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3.5 pl-2">
                        <div className="font-medium text-slate-200">{ent.display_name}</div>
                        <div className="text-xs font-mono text-slate-400 truncate max-w-xs">
                          {ent.canonical_id}
                        </div>
                      </td>
                      <td className="py-3.5">
                        <span className="text-xs text-slate-300">
                          {ENTITY_TYPE_LABELS[ent.entity_type] || ent.entity_type}
                        </span>
                      </td>
                      <td className="py-3.5">
                        <span className={`inline-flex px-2 py-0.5 rounded text-[11px] font-mono border ${prov.color}`}>
                          {prov.label}
                        </span>
                      </td>
                      <td className="py-3.5 font-mono text-sm font-semibold">
                        {formatScore(ent.current_risk_score)}
                      </td>
                      <td className="py-3.5">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${colors.badge}`}>
                          <span className={`h-1.5 w-1.5 rounded-full ${colors.indicator}`} />
                          <span className="capitalize">{ent.current_severity}</span>
                        </span>
                      </td>
                      <td className="py-3.5 text-right pr-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/entities?id=${ent.id}`)}
                          className="h-8 text-teal-400 hover:text-teal-300"
                        >
                          Review <ExternalLink className="ml-1 h-3.5 w-3.5" />
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

