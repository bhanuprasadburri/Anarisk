import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Node,
  Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  Network,
  RotateCw,
  Search,
  Plus,
  Briefcase,
  Layers,
  ChevronRight,
  ShieldAlert,
  Info,
  Filter,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { graphService } from '../services/graphService';
import { GraphResponse, ClusterSummary, GraphNode as IGraphNode } from '../types';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { formatScore } from '../lib/formatters';
import { getSeverityColor } from '../lib/utils';
import { RELATIONSHIP_LABELS } from '../lib/constants';

export const RiskGraphPage: React.FC = () => {
  const { activeBrand } = useAuth();
  const navigate = useNavigate();

  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [clusters, setClusters] = useState<ClusterSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Filters
  const [minRisk, setMinRisk] = useState<number>(0);
  const [selectedSeverity, setSelectedSeverity] = useState<string>('');

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const loadGraph = async () => {
    setIsLoading(true);
    try {
      const [g, c] = await Promise.all([
        graphService.getGraph({
          brand_id: activeBrand?.id,
          min_risk: minRisk > 0 ? minRisk : undefined,
          severity: selectedSeverity || undefined,
        }),
        graphService.getClusters(activeBrand?.id),
      ]);
      setGraphData(g);
      setClusters(c);

      // Convert nodes to ReactFlow nodes with layout positioning
      const nodeCount = g.nodes.length;
      const radius = Math.max(220, nodeCount * 45);
      const centerX = 400;
      const centerY = 320;

      const flowNodes: Node[] = g.nodes.map((n, idx) => {
        const angle = (idx / (nodeCount || 1)) * 2 * Math.PI;
        // Jitter or cluster offsets
        const clusterOffset = n.cluster_id ? (parseInt(n.cluster_id.replace(/\D/g, '') || '0') % 3) * 60 : 0;
        const x = centerX + (radius + clusterOffset) * Math.cos(angle);
        const y = centerY + (radius + clusterOffset) * Math.sin(angle);

        const colors = getSeverityColor(n.severity);

        return {
          id: n.id,
          position: { x, y },
          data: {
            label: (
              <div className="flex flex-col items-center p-1 text-center select-none">
                <span className="text-[10px] font-mono uppercase text-slate-400">
                  {n.entity_type}
                </span>
                <span className="text-xs font-bold text-slate-100 max-w-[130px] truncate">
                  {n.label}
                </span>
                <span className={`mt-1 px-1.5 py-0.2 rounded text-[10px] font-mono border ${colors.badge}`}>
                  {formatScore(n.risk_score)}
                </span>
              </div>
            ),
            raw: n,
          },
          style: {
            background: '#0d1424',
            border: `2px solid ${
              n.severity === 'critical'
                ? '#ef4444'
                : n.severity === 'high'
                ? '#f97316'
                : n.severity === 'medium'
                ? '#f59e0b'
                : '#3b82f6'
            }`,
            borderRadius: '12px',
            color: '#fff',
            width: 150,
            cursor: 'pointer',
            boxShadow: '0 4px 16px rgba(0,0,0,0.6)',
          },
        };
      });

      const flowEdges: Edge[] = g.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: RELATIONSHIP_LABELS[e.relationship_type] || e.relationship_type,
        animated: e.confidence > 0.8,
        style: { stroke: '#2dd4bf', strokeWidth: 2, opacity: Math.max(0.4, e.confidence) },
        labelStyle: { fill: '#94a3b8', fontSize: 10, fontFamily: 'monospace' },
        labelBgStyle: { fill: '#0a0f1d', fillOpacity: 0.9, stroke: '#1e293b' },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#2dd4bf' },
      }));

      setNodes(flowNodes);
      setEdges(flowEdges);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadGraph();
  }, [activeBrand, minRisk, selectedSeverity]);

  const handleDiscover = async () => {
    try {
      const res = await graphService.discoverRelationships(activeBrand?.id || 'b-001');
      alert(`Discovery complete: ${res.relationships_created || 0} new relationships correlated.`);
      loadGraph();
    } catch (err) {
      alert('Discovery error: ' + (err as Error).message);
    }
  };

  const handleCreateClusterCase = async (cluster: ClusterSummary) => {
    try {
      const c = await graphService.createCaseFromCluster(
        cluster.entity_ids,
        `Campaign Cluster: ${cluster.headline}`
      );
      alert(`Case ${c.case_number} opened for ${cluster.size} connected cluster entities.`);
      navigate(`/cases?id=${c.id}`);
    } catch (err) {
      alert('Failed to create case: ' + (err as Error).message);
    }
  };

  const selectedNode = useMemo(() => {
    if (!selectedNodeId || !graphData) return null;
    return graphData.nodes.find((n) => n.id === selectedNodeId);
  }, [selectedNodeId, graphData]);

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Correlated Risk Graph
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Multi-entity attack infrastructure graph linking domains, logos, accounts & APKs.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={handleDiscover}>
            <RotateCw className="mr-2 h-4 w-4 text-teal-400" />
            Discover Relationships
          </Button>
          <Button variant="teal" size="sm" onClick={() => loadGraph()}>
            <Network className="mr-2 h-4 w-4" />
            Refresh Graph
          </Button>
        </div>
      </div>

      {/* Filter toolbar */}
      <Card className="p-3">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-4 text-xs">
            <span className="font-mono text-slate-400 flex items-center gap-1.5">
              <Filter className="h-3.5 w-3.5" /> Graph Filters:
            </span>

            <div className="flex items-center gap-2">
              <label className="text-slate-400">Min Risk:</label>
              <input
                type="range"
                min="0"
                max="0.9"
                step="0.1"
                value={minRisk}
                onChange={(e) => setMinRisk(parseFloat(e.target.value))}
                className="w-24 accent-teal-500"
              />
              <span className="font-mono font-bold text-teal-400">{formatScore(minRisk)}</span>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-slate-400">Severity:</label>
              <select
                value={selectedSeverity}
                onChange={(e) => setSelectedSeverity(e.target.value)}
                className="rounded border border-slate-800 bg-slate-900 px-2 py-1 text-slate-300"
              >
                <option value="">All</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
            <span>Nodes: <strong className="text-slate-200">{graphData?.node_count || 0}</strong></span>
            <span>•</span>
            <span>Edges: <strong className="text-slate-200">{graphData?.edge_count || 0}</strong></span>
            <span>•</span>
            <span>Campaigns: <strong className="text-slate-200">{clusters.length}</strong></span>
          </div>
        </div>
      </Card>

      {/* Main Canvas + Sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 min-h-[580px]">
        {/* Canvas */}
        <div className="lg:col-span-3 rounded-2xl border border-slate-800 bg-[#070a12] relative overflow-hidden shadow-2xl h-[620px]">
          {isLoading ? (
            <div className="flex h-full items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-500 border-t-transparent" />
            </div>
          ) : (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={(_, node) => setSelectedNodeId(node.id)}
              fitView
              className="h-full w-full"
            >
              <Background color="#1e293b" gap={20} size={1} />
              <Controls />
            </ReactFlow>
          )}

          {/* Node Inspector Overlay if selected */}
          {selectedNode && (
            <div className="absolute top-4 right-4 z-20 w-72 rounded-xl border border-slate-700 bg-[#0d1424]/95 p-4 shadow-2xl backdrop-blur-md">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[10px] font-mono uppercase text-slate-400">
                    {selectedNode.entity_type}
                  </span>
                  <h4 className="font-semibold text-slate-100 text-sm">{selectedNode.label}</h4>
                </div>
                <button
                  onClick={() => setSelectedNodeId(null)}
                  className="text-slate-400 hover:text-white text-xs"
                >
                  ✕
                </button>
              </div>

              <div className="mt-3 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Risk Score:</span>
                  <span className="font-mono font-bold text-teal-400">
                    {formatScore(selectedNode.risk_score)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Severity:</span>
                  <span className="capitalize font-semibold text-red-400">
                    {selectedNode.severity}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Cluster:</span>
                  <span className="font-mono text-slate-300">
                    {selectedNode.cluster_id || 'Isolated'}
                  </span>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800 flex flex-col gap-2">
                <Button
                  variant="teal"
                  size="sm"
                  onClick={() => navigate(`/entities?id=${selectedNode.id}`)}
                >
                  Review Entity Details
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Right Sidebar: Threat Clusters */}
        <div className="space-y-4">
          <Card className="h-full flex flex-col justify-between">
            <div>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Layers className="h-4 w-4 text-teal-400" />
                  Identified Threat Clusters
                </CardTitle>
                <p className="text-xs text-slate-400">
                  Automated connected-component analysis detecting concerted impersonation rings.
                </p>
              </CardHeader>
              <CardContent className="space-y-3 pt-0 max-h-[460px] overflow-y-auto">
                {clusters.map((c) => (
                  <div
                    key={c.cluster_id}
                    className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2 hover:border-slate-700 transition-all"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-teal-300">
                        {c.cluster_id}
                      </span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-red-950 text-red-300 border border-red-800">
                        Max: {formatScore(c.max_risk_score)}
                      </span>
                    </div>

                    <p className="text-xs font-medium text-slate-200 leading-snug">
                      {c.headline}
                    </p>

                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span>{c.size} Linked Entities</span>
                      <span className="capitalize text-red-400">{c.max_severity}</span>
                    </div>

                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full text-xs h-7 mt-1 border-teal-500/30 text-teal-300 hover:bg-teal-950/40"
                      onClick={() => handleCreateClusterCase(c)}
                    >
                      <Briefcase className="mr-1.5 h-3 w-3" />
                      Create Cluster Case
                    </Button>
                  </div>
                ))}
              </CardContent>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

