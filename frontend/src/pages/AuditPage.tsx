import React, { useEffect, useState } from 'react';
import {
  History,
  Search,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { auditService } from '../services/auditService';
import { AuditLog } from '../types';
import { Card, CardContent } from '../components/ui/card';
import { formatDate } from '../lib/formatters';

export const AuditPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedRowId, setExpandedRowId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const loadLogs = async () => {
    setIsLoading(true);
    try {
      const res = await auditService.listLogs(100);
      setLogs(res);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  const filteredLogs = logs.filter((l) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      l.action.toLowerCase().includes(q) ||
      (l.resource_type && l.resource_type.toLowerCase().includes(q)) ||
      (l.actor_email && l.actor_email.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
            System Audit Trail
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Immutable, tamper-evident forensic log of all detections, status changes, assignments and partner handoffs.
          </p>
        </div>
      </div>

      {/* Search toolbar */}
      <Card className="p-3">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search audit actions, actors or targets..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-slate-800 bg-slate-900/80 py-1.5 pl-9 pr-4 text-sm text-slate-100 placeholder:text-slate-500 focus:border-teal-500 focus:outline-none"
          />
        </div>
      </Card>

      {/* Audit Log Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex min-h-[30vh] items-center justify-center">
              <div className="h-7 w-7 animate-spin rounded-full border-4 border-teal-500 border-t-transparent" />
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="p-12 text-center text-slate-400">No audit log records found.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-800 bg-slate-900/60 text-xs font-mono uppercase text-slate-400">
                  <tr>
                    <th className="py-3 pl-4">Timestamp</th>
                    <th className="py-3">Action</th>
                    <th className="py-3">Actor Email</th>
                    <th className="py-3">Resource Target</th>
                    <th className="py-3 pr-4 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-sans">
                  {filteredLogs.map((log) => {
                    const isExpanded = expandedRowId === log.id;
                    return (
                      <React.Fragment key={log.id}>
                        <tr
                          className="hover:bg-slate-800/30 transition-colors cursor-pointer"
                          onClick={() => setExpandedRowId(isExpanded ? null : log.id)}
                        >
                          <td className="py-3 pl-4 font-mono text-xs text-slate-400 whitespace-nowrap">
                            {formatDate(log.created_at)}
                          </td>
                          <td className="py-3">
                            <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-teal-950/60 text-teal-300 border border-teal-800/50">
                              {log.action}
                            </span>
                          </td>
                          <td className="py-3 text-xs text-slate-200">
                            {log.actor_email || 'System / Automated'}
                          </td>
                          <td className="py-3 font-mono text-xs text-slate-400">
                            {log.resource_type ? `${log.resource_type} (${log.resource_id?.slice(0, 8)}...)` : '—'}
                          </td>
                          <td className="py-3 pr-4 text-right">
                            <span className="text-slate-400 text-xs">
                              {isExpanded ? (
                                <ChevronDown className="h-4 w-4 inline" />
                              ) : (
                                <ChevronRight className="h-4 w-4 inline" />
                              )}
                            </span>
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr className="bg-black/30">
                            <td colSpan={5} className="p-4">
                              <div className="rounded-lg bg-slate-950 p-3 border border-slate-800">
                                <span className="text-[11px] font-mono text-slate-400 uppercase block mb-1">
                                  Audit Payload / Metadata:
                                </span>
                                <pre className="font-mono text-xs text-teal-300 overflow-x-auto whitespace-pre-wrap">
                                  {JSON.stringify(log.details || log, null, 2)}
                                </pre>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

