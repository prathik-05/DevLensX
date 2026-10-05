import React, { useState, useCallback, useMemo } from 'react';
import type { AnalysisResponse } from '../types';
import { 
  ReactFlow, 
  Controls, 
  Background, 
  useNodesState, 
  useEdgesState,
  MarkerType,
  BackgroundVariant
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { GitFork, Layers, Info, MousePointerClick, Search, Filter } from 'lucide-react';

interface KnowledgeGraphViewProps {
  data: AnalysisResponse;
  highlightedNodeId?: string | null;
}

const fallbackNodes = [
  // Controllers (Layer 1)
  { id: 'PaymentController', data: { label: 'PaymentController\n(Controller)', stereotype: 'Controller', file: 'com/devlensx/PaymentController.java', package: 'com.devlensx', incoming: 0 }, position: { x: 50, y: 50 }, className: 'bg-cyan-950 border-cyan-500 text-cyan-200 font-mono text-xs rounded-xl p-3 shadow-lg border-2' },
  { id: 'AccountController', data: { label: 'AccountController\n(Controller)', stereotype: 'Controller', file: 'com/devlensx/AccountController.java', package: 'com.devlensx', incoming: 0 }, position: { x: 320, y: 50 }, className: 'bg-cyan-950 border-cyan-500 text-cyan-200 font-mono text-xs rounded-xl p-3 shadow-lg border-2' },
  { id: 'AdminController', data: { label: 'AdminController\n(Controller)', stereotype: 'Controller', file: 'com/devlensx/AdminController.java', package: 'com.devlensx', incoming: 0 }, position: { x: 580, y: 50 }, className: 'bg-cyan-950 border-cyan-500 text-cyan-200 font-mono text-xs rounded-xl p-3 shadow-lg border-2' },

  // Services (Layer 2)
  { id: 'PaymentService', data: { label: 'PaymentService\n(Service)', stereotype: 'Service', file: 'com/devlensx/PaymentService.java', package: 'com.devlensx', incoming: 2 }, position: { x: 180, y: 220 }, className: 'bg-blue-950 border-blue-500 text-blue-200 font-mono text-xs rounded-xl p-3 shadow-lg border-2' },
  { id: 'AccountService', data: { label: 'AccountService\n(Service)', stereotype: 'Service', file: 'com/devlensx/AccountService.java', package: 'com.devlensx', incoming: 2 }, position: { x: 450, y: 220 }, className: 'bg-blue-950 border-blue-500 text-blue-200 font-mono text-xs rounded-xl p-3 shadow-lg border-2' },

  // Repositories (Layer 3)
  { id: 'PaymentRepository', data: { label: 'PaymentRepository\n(Repository)', stereotype: 'Repository', file: 'com/devlensx/PaymentRepository.java', package: 'com.devlensx', incoming: 1 }, position: { x: 180, y: 390 }, className: 'bg-indigo-950 border-indigo-500 text-indigo-200 font-mono text-xs rounded-xl p-3 shadow-lg border-2' },
  { id: 'AccountRepository', data: { label: 'AccountRepository\n(Repository)', stereotype: 'Repository', file: 'com/devlensx/AccountRepository.java', package: 'com.devlensx', incoming: 1 }, position: { x: 450, y: 390 }, className: 'bg-indigo-950 border-indigo-500 text-indigo-200 font-mono text-xs rounded-xl p-3 shadow-lg border-2' },

  // Entities (Layer 4)
  { id: 'Payment', data: { label: 'Payment\n(Entity)', stereotype: 'Entity', file: 'com/devlensx/Payment.java', package: 'com.devlensx', incoming: 1 }, position: { x: 180, y: 550 }, className: 'bg-emerald-950 border-emerald-500 text-emerald-200 font-mono text-xs rounded-xl p-3 shadow-lg border-2' },
  { id: 'Account', data: { label: 'Account\n(Entity)', stereotype: 'Entity', file: 'com/devlensx/Account.java', package: 'com.devlensx', incoming: 1 }, position: { x: 450, y: 550 }, className: 'bg-emerald-950 border-emerald-500 text-emerald-200 font-mono text-xs rounded-xl p-3 shadow-lg border-2' }
];

const fallbackEdges = [
  { id: 'e1', source: 'PaymentController', target: 'PaymentService', label: 'DEPENDS_ON', animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: '#06b6d4' }, style: { stroke: '#06b6d4', strokeWidth: 2 } },
  { id: 'e2', source: 'AccountController', target: 'AccountService', label: 'DEPENDS_ON', animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: '#06b6d4' }, style: { stroke: '#06b6d4', strokeWidth: 2 } },
  { id: 'e3', source: 'AdminController', target: 'PaymentService', label: 'DEPENDS_ON', animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: '#06b6d4' }, style: { stroke: '#06b6d4', strokeWidth: 2 } },
  { id: 'e4', source: 'PaymentService', target: 'AccountService', label: 'DEPENDS_ON', animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: '#3b82f6' }, style: { stroke: '#3b82f6', strokeWidth: 2 } },
  { id: 'e5', source: 'PaymentService', target: 'PaymentRepository', label: 'DEPENDS_ON', animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: '#3b82f6' }, style: { stroke: '#3b82f6', strokeWidth: 2 } },
  { id: 'e6', source: 'AccountService', target: 'AccountRepository', label: 'DEPENDS_ON', animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: '#3b82f6' }, style: { stroke: '#3b82f6', strokeWidth: 2 } },
  { id: 'e7', source: 'PaymentRepository', target: 'Payment', label: 'DEPENDS_ON', animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: '#6366f1' }, style: { stroke: '#6366f1', strokeWidth: 2 } },
  { id: 'e8', source: 'AccountRepository', target: 'Account', label: 'DEPENDS_ON', animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: '#6366f1' }, style: { stroke: '#6366f1', strokeWidth: 2 } }
];

export const KnowledgeGraphView: React.FC<KnowledgeGraphViewProps> = ({ data, highlightedNodeId }) => {
  const summary = data.repo_summary || { language: 'Java', framework: 'Spring Boot', controllers: 3, services: 3, repositories: 2, entities: 1 };
  const edgeStats = data.graph_edge_stats || { DEPENDS_ON: 9, EXTENDS: 0, IMPLEMENTS: 0 };
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [topNLimit, setTopNLimit] = useState<number>(30);

  // Dynamic Flow Node/Edge construction with Top-N & Search filtering
  const { flowNodes, flowEdges } = useMemo(() => {
    if (!data.knowledge_graph?.nodes || data.knowledge_graph.nodes.length === 0) {
      return { flowNodes: fallbackNodes, flowEdges: fallbackEdges };
    }

    let rawNodes = [...data.knowledge_graph.nodes];

    // Filter by Search Term if specified
    if (searchTerm.trim()) {
      rawNodes = rawNodes.filter(n => 
        n.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
        (n.package && n.package.toLowerCase().includes(searchTerm.toLowerCase()))
      );
    }

    // Top-N Coupling Sort
    rawNodes.sort((a, b) => (b.incoming_count || 0) - (a.incoming_count || 0));
    if (topNLimit > 0 && rawNodes.length > topNLimit) {
      rawNodes = rawNodes.slice(0, topNLimit);
    }

    const nodeIds = new Set(rawNodes.map(n => n.name));

    // Layer Layout Positions (Controller -> Service -> Repository -> Entity -> Other)
    const layerY: Record<string, number> = { Controller: 50, Service: 220, Repository: 390, Entity: 550, Other: 300, Test: 450 };
    const layerCount: Record<string, number> = { Controller: 0, Service: 0, Repository: 0, Entity: 0, Other: 0, Test: 0 };

    const nodesArr = rawNodes.map(n => {
      const st = n.stereotype in layerY ? n.stereotype : 'Other';
      const count = layerCount[st] || 0;
      layerCount[st] = count + 1;
      const xPos = 50 + (count % 6) * 220;
      const yPos = layerY[st] + Math.floor(count / 6) * 120;

      let colorClass = 'bg-[#12161F] border-[#1A202E] !text-[#E8EDF5] font-bold';
      let nodeTextColor = '#E8EDF5';
      if (st === 'Controller') { colorClass = 'bg-[#4FC3F7]/15 border-[#4FC3F7] !text-[#4FC3F7] font-bold'; nodeTextColor = '#4FC3F7'; }
      else if (st === 'Service') { colorClass = 'bg-[#66BB6A]/15 border-[#66BB6A] !text-[#66BB6A] font-bold'; nodeTextColor = '#66BB6A'; }
      else if (st === 'Repository') { colorClass = 'bg-[#AB47BC]/15 border-[#AB47BC] !text-[#AB47BC] font-bold'; nodeTextColor = '#AB47BC'; }
      else if (st === 'Entity') { colorClass = 'bg-[#FFA726]/15 border-[#FFA726] !text-[#FFA726] font-bold'; nodeTextColor = '#FFA726'; }
      else if (st === 'Security' || st === 'Risk') { colorClass = 'bg-[#EF5350]/15 border-[#EF5350] !text-[#EF5350] font-bold'; nodeTextColor = '#EF5350'; }

      const fileExt = summary.language === 'Python' ? '.py' : summary.language === 'TypeScript' ? '.tsx' : '.java';
      const fileNameLabel = n.name.endsWith('.java') || n.name.endsWith('.py') || n.name.endsWith('.tsx') || n.name.endsWith('.js') 
        ? n.name 
        : `${n.name}${fileExt}`;

      return {
        id: n.name,
        data: { label: `📄 ${fileNameLabel}\n[${n.stereotype}]`, stereotype: n.stereotype, file: n.file || fileNameLabel, package: n.package, incoming: n.incoming_count },
        position: { x: xPos, y: yPos },
        className: `${colorClass} font-mono text-xs rounded-xl p-3 shadow-lg border-2 cursor-pointer`,
        style: { color: nodeTextColor, fontWeight: 700 }
      };
    });

    const rawEdges = (data.knowledge_graph.edges || []).filter(e => nodeIds.has(e.source) && nodeIds.has(e.target));
    const neighborIds = new Set<string>();
    if (highlightedNodeId) {
      neighborIds.add(highlightedNodeId);
      for (const e of rawEdges) {
        if (e.source === highlightedNodeId) neighborIds.add(e.target);
        if (e.target === highlightedNodeId) neighborIds.add(e.source);
      }
    }

    const nodesArrDimmed = nodesArr.map(n => {
      if (!highlightedNodeId) return n;
      const isNeighbor = neighborIds.has(n.id);
      return {
        ...n,
        style: {
          ...n.style,
          opacity: isNeighbor ? 1 : 0.28,
          // highlighted node gets ring
          ...(n.id === highlightedNodeId ? { borderWidth: 3, boxShadow: '0 0 0 3px rgba(56,189,248,0.5)' } : {}),
        },
        className: n.className + (isNeighbor ? '' : ' opacity-60'),
      };
    });

    const edgesArr = rawEdges.map((e, idx) => {
      const isHighlighted = highlightedNodeId ? (e.source === highlightedNodeId || e.target === highlightedNodeId) : true;
      return {
        id: `edge-${idx}`,
        source: e.source,
        target: e.target,
        label: e.type,
        animated: isHighlighted,
        markerEnd: { type: MarkerType.ArrowClosed, color: isHighlighted ? '#38bdf8' : '#475569' },
        style: { stroke: isHighlighted ? '#38bdf8' : '#475569', strokeWidth: isHighlighted ? 2 : 1, opacity: isHighlighted || !highlightedNodeId ? 1 : 0.25 },
      };
    });

    return { flowNodes: nodesArrDimmed, flowEdges: edgesArr };
  }, [data, searchTerm, topNLimit, highlightedNodeId]);

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

  React.useEffect(() => {
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [flowNodes, flowEdges, setNodes, setEdges]);

  const onNodeClick = useCallback((_: any, node: any) => {
    setSelectedNode(node);
  }, []);

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="bg-slate-900/90 p-6 rounded-2xl border border-slate-800 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center space-x-2">
            <GitFork className="w-5 h-5 text-cyan-400" />
            <span>Interactive Knowledge Graph Workspace (React Flow Canvas)</span>
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Visual Cypher graph relationships: DEPENDS_ON ({edgeStats.DEPENDS_ON || 9} edges). Zoom, pan, drag, and click nodes to inspect dependencies.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs text-slate-400 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
          <MousePointerClick className="w-4 h-4 text-cyan-400" />
          <span>Click any node to highlight connections</span>
        </div>
      </div>

      {/* Dynamic Layer & Stereotype Breakdown Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/90 p-4 rounded-xl border border-slate-800 text-center">
          <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-1">Controllers / APIs</div>
          <div className="text-2xl font-bold text-cyan-400">{summary.controllers ?? 0}</div>
        </div>
        <div className="bg-slate-900/90 p-4 rounded-xl border border-slate-800 text-center">
          <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-1">Services / Logic</div>
          <div className="text-2xl font-bold text-blue-400">{summary.services ?? 0}</div>
        </div>
        <div className="bg-slate-900/90 p-4 rounded-xl border border-slate-800 text-center">
          <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-1">Repositories / Data</div>
          <div className="text-2xl font-bold text-indigo-400">{summary.repositories ?? 0}</div>
        </div>
        <div className="bg-slate-900/90 p-4 rounded-xl border border-slate-800 text-center">
          <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-1">Entities & Models</div>
          <div className="text-2xl font-bold text-emerald-400">{summary.entities ?? 0}</div>
        </div>
      </div>

      {/* Canvas Search & Coupling Scale Filter Toolbar */}
      <div className="bg-slate-900/90 p-4 rounded-xl border border-slate-800 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-2 bg-slate-950 px-3 py-2 rounded-xl border border-slate-800 w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search class or package..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent text-xs text-white placeholder-slate-500 focus:outline-none w-full"
          />
        </div>

        <div className="flex items-center space-x-3 text-xs text-slate-300">
          <Filter className="w-4 h-4 text-cyan-400" />
          <span>Canvas Node Scale:</span>
          <select
            value={topNLimit}
            onChange={(e) => setTopNLimit(Number(e.target.value))}
            className="bg-slate-950 border border-slate-800 text-white rounded-lg px-3 py-1.5 focus:outline-none"
          >
            <option value={30}>Top 30 Connected Nodes (Fast Default)</option>
            <option value={50}>Top 50 Connected Nodes</option>
            <option value={100}>Top 100 Connected Nodes</option>
            <option value={0}>Show All Nodes (Full Graph)</option>
          </select>
        </div>
      </div>

      {/* High Contrast Custom Node & Edge Styles */}
      <style>{`
        .react-flow__node, .react-flow__node * {
          color: #ffffff !important;
          font-weight: 700 !important;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
        }
        .react-flow__node-default, .react-flow__node-input, .react-flow__node-output {
          background: #090d16 !important;
          border: 2px solid #38bdf8 !important;
          border-radius: 12px !important;
          padding: 10px 14px !important;
          box-shadow: 0 10px 25px -5px rgba(6, 182, 212, 0.2) !important;
        }
        .react-flow__edge-text {
          fill: #38bdf8 !important;
          font-weight: 700 !important;
          font-size: 11px !important;
        }
        .react-flow__edge-textbg {
          fill: #020617 !important;
          rx: 4px !important;
        }
      `}</style>

      {/* React Flow Interactive Graph Canvas */}
      {data.parse_stats?.files_parsed === 0 ? (
        <div className="bg-slate-900/90 p-12 rounded-2xl border border-slate-800 text-center space-y-4">
          <div className="w-16 h-16 rounded-full bg-slate-950 border border-slate-800 flex items-center justify-center mx-auto text-amber-400">
            <Info className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-bold text-white">No Java Source Files Detected</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto">
            Target repository <strong>{data.repository}</strong> contains 0 <code>.java</code> source files (Primary language detected: <strong>{summary.language}</strong>). DevLensX AST Knowledge Graph parser targets Java repositories.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 bg-slate-950 rounded-2xl border border-slate-800 h-[620px] relative overflow-hidden shadow-2xl">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            fitView
            className="bg-slate-950"
          >
            <Controls className="bg-slate-900 border-slate-800 text-white" />
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#334155" />
          </ReactFlow>
        </div>

        {/* Selected Node Details Panel */}
        <div className="bg-slate-900/90 p-6 rounded-2xl border border-slate-800 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2 border-b border-slate-800 pb-3">
            <Info className="w-4 h-4 text-cyan-400" />
            <span>Node Detail Inspector</span>
          </h3>

          {selectedNode ? (
            <div className="space-y-3 text-xs">
              <div>
                <span className="text-slate-400 uppercase font-semibold block">Component Name</span>
                <span className="font-mono text-base font-bold text-cyan-300">{selectedNode.id}</span>
              </div>

              <div>
                <span className="text-slate-400 uppercase font-semibold block">Stereotype</span>
                <span className="px-2.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono inline-block mt-1">
                  {selectedNode.data.stereotype}
                </span>
              </div>

              <div>
                <span className="text-slate-400 uppercase font-semibold block">Declared Methods</span>
                <span className="text-slate-200 font-mono font-bold text-sm">{selectedNode.data.methods} methods</span>
              </div>

              <div>
                <span className="text-slate-400 uppercase font-semibold block">Package Path</span>
                <span className="text-slate-400 font-mono text-[11px] break-all block mt-1">
                  com.devlensx.core.{selectedNode.data.stereotype.toLowerCase()}.{selectedNode.id}
                </span>
              </div>
            </div>
          ) : (
            <div className="text-slate-500 text-xs py-10 text-center space-y-2">
              <Layers className="w-8 h-8 mx-auto text-slate-700" />
              <p>Click any node in the React Flow canvas to inspect structural metrics and package details.</p>
            </div>
          )}
        </div>
      </div>
      )}
    </div>
  );
};
