import React, { useEffect, useRef, useState } from 'react';
import type { AnalysisResponse } from '../types';
import { Sparkles, FileCode } from 'lucide-react';

interface GalaxyConstellationGraphProps {
  data: AnalysisResponse;
}

interface ConstellationNode {
  id: string;
  name: string;
  file: string;
  stereotype: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  color: string;
  glowColor: string;
  connections: string[];
}

export const GalaxyConstellationGraph: React.FC<GalaxyConstellationGraphProps> = ({ data }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [hoveredNode, setHoveredNode] = useState<ConstellationNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<ConstellationNode | null>(null);
  const [nodeCount, setNodeCount] = useState<number>(45);

  const nodesRef = useRef<ConstellationNode[]>([]);
  const isDraggingRef = useRef<boolean>(false);
  const draggedNodeRef = useRef<ConstellationNode | null>(null);
  const mousePosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Color mapping matching user image (Cyan, Green, Yellow, Magenta, Red, Blue)
  const getStereotypeColor = (stereotype: string, idx: number) => {
    const colors = [
      { fill: '#00F0FF', glow: 'rgba(0, 240, 255, 0.8)' },   // Cyan - Controller
      { fill: '#10B981', glow: 'rgba(16, 185, 129, 0.8)' },  // Emerald - Service
      { fill: '#A855F7', glow: 'rgba(168, 85, 247, 0.8)' },  // Purple - Repository
      { fill: '#EAB308', glow: 'rgba(234, 179, 8, 0.8)' },   // Yellow - Entity
      { fill: '#EF4444', glow: 'rgba(239, 68, 68, 0.8)' },   // Red - Security / High Debt
      { fill: '#3B82F6', glow: 'rgba(59, 130, 246, 0.8)' }   // Blue - Config
    ];

    if (stereotype === 'Controller') return colors[0];
    if (stereotype === 'Service') return colors[1];
    if (stereotype === 'Repository') return colors[2];
    if (stereotype === 'Entity') return colors[3];
    if (stereotype === 'Security' || stereotype === 'Risk') return colors[4];
    return colors[idx % colors.length];
  };

  // Build Radial Constellation Graph Nodes
  useEffect(() => {
    const rawNodes = data.knowledge_graph?.nodes || [];
    const lang = data.repo_summary?.language || 'Java';
    const ext = lang === 'Python' ? '.py' : lang === 'TypeScript' ? '.tsx' : '.java';

    const canvas = canvasRef.current;
    const width = canvas ? canvas.width : 900;
    const height = canvas ? canvas.height : 600;
    const cx = width / 2;
    const cy = height / 2;

    const formattedNodes: ConstellationNode[] = [];

    // Central Application Core Root Hub
    const appRootName = `ApplicationRootCore${ext}`;
    const rootNode: ConstellationNode = {
      id: 'root-hub',
      name: appRootName,
      file: `src/main/${appRootName}`,
      stereotype: 'Core Application Root',
      x: cx,
      y: cy,
      vx: 0,
      vy: 0,
      radius: 14,
      color: '#10B981',
      glowColor: 'rgba(16, 185, 129, 0.95)',
      connections: []
    };
    formattedNodes.push(rootNode);

    const sourceNodes = rawNodes.length > 0 ? rawNodes.slice(0, nodeCount) : [
      { name: 'OwnerController', stereotype: 'Controller', file: 'OwnerController.java' },
      { name: 'PetController', stereotype: 'Controller', file: 'PetController.java' },
      { name: 'VetsController', stereotype: 'Controller', file: 'VetsController.java' },
      { name: 'ClinicService', stereotype: 'Service', file: 'ClinicService.java' },
      { name: 'OwnerService', stereotype: 'Service', file: 'OwnerService.java' },
      { name: 'PetRepository', stereotype: 'Repository', file: 'PetRepository.java' },
      { name: 'OwnerRepository', stereotype: 'Repository', file: 'OwnerRepository.java' },
      { name: 'VetRepository', stereotype: 'Repository', file: 'VetRepository.java' },
      { name: 'OwnerEntity', stereotype: 'Entity', file: 'Owner.java' },
      { name: 'PetEntity', stereotype: 'Entity', file: 'Pet.java' },
      { name: 'VisitEntity', stereotype: 'Entity', file: 'Visit.java' },
      { name: 'SecurityConfig', stereotype: 'Security', file: 'SecurityConfig.java' }
    ];

    // Position nodes in radial concentric orbits
    sourceNodes.forEach((n, idx) => {
      const fileName = n.name.endsWith(ext) || n.name.includes('.') ? n.name : `${n.name}${ext}`;
      const angle = (idx / sourceNodes.length) * Math.PI * 2 + (Math.random() * 0.4 - 0.2);
      
      // Radius rings (Inner orbit, Middle orbit, Outer orbit)
      const orbitTier = (idx % 3) + 1;
      const radiusDistance = orbitTier * 110 + (Math.random() * 40 - 20);

      const nx = cx + Math.cos(angle) * radiusDistance;
      const ny = cy + Math.sin(angle) * radiusDistance;

      const palette = getStereotypeColor(n.stereotype, idx);

      formattedNodes.push({
        id: `node-${idx}`,
        name: fileName,
        file: n.file || fileName,
        stereotype: n.stereotype || 'Component',
        x: Math.max(40, Math.min(width - 40, nx)),
        y: Math.max(40, Math.min(height - 40, ny)),
        vx: (Math.random() - 0.5) * 0.2,
        vy: (Math.random() - 0.5) * 0.2,
        radius: Math.floor(Math.random() * 5) + 6,
        color: palette.fill,
        glowColor: palette.glow,
        connections: ['root-hub']
      });
    });

    // Create cross-node constellation connections
    formattedNodes.forEach((node, idx) => {
      if (node.id === 'root-hub') return;
      // Connect to nearest neighbors
      for (let j = idx + 1; j < formattedNodes.length; j++) {
        const other = formattedNodes[j];
        const dist = Math.hypot(node.x - other.x, node.y - other.y);
        if (dist < 160 && Math.random() > 0.4) {
          node.connections.push(other.id);
        }
      }
    });

    nodesRef.current = formattedNodes;
  }, [data, nodeCount]);

  // 60FPS Canvas Animation Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;

    const render = () => {
      const width = canvas.width;
      const height = canvas.height;

      ctx.clearRect(0, 0, width, height);

      // 1. Dark Universe Background with Star Particles
      ctx.fillStyle = '#060913';
      ctx.fillRect(0, 0, width, height);

      // Star particles
      ctx.fillStyle = 'rgba(255, 255, 255, 0.25)';
      for (let i = 0; i < 60; i++) {
        const sx = (Math.sin(i * 99 + Date.now() * 0.0001) * 0.5 + 0.5) * width;
        const sy = (Math.cos(i * 33 + Date.now() * 0.0001) * 0.5 + 0.5) * height;
        const sSize = (i % 3) === 0 ? 1.5 : 0.8;
        ctx.beginPath();
        ctx.arc(sx, sy, sSize, 0, Math.PI * 2);
        ctx.fill();
      }

      const nodes = nodesRef.current;
      const nodeMap = new Map(nodes.map(n => [n.id, n]));

      // Gently move un-dragged nodes
      nodes.forEach(n => {
        if (!isDraggingRef.current || draggedNodeRef.current?.id !== n.id) {
          n.x += n.vx;
          n.y += n.vy;
          if (n.x < 30 || n.x > width - 30) n.vx *= -1;
          if (n.y < 30 || n.y > height - 30) n.vy *= -1;
        }
      });

      // 2. Draw Constellation Laser Beams (Edges)
      nodes.forEach(source => {
        source.connections.forEach(targetId => {
          const target = nodeMap.get(targetId);
          if (!target) return;

          const isHoveredEdge = 
            (hoveredNode && (hoveredNode.id === source.id || hoveredNode.id === target.id)) ||
            (selectedNode && (selectedNode.id === source.id || selectedNode.id === target.id));

          ctx.beginPath();
          ctx.moveTo(source.x, source.y);
          ctx.lineTo(target.x, target.y);

          if (isHoveredEdge) {
            ctx.strokeStyle = source.color;
            ctx.lineWidth = 2.5;
            ctx.shadowColor = source.color;
            ctx.shadowBlur = 12;
          } else {
            ctx.strokeStyle = 'rgba(56, 189, 248, 0.18)';
            ctx.lineWidth = 1;
            ctx.shadowBlur = 0;
          }
          ctx.stroke();
        });
      });

      // Reset glow shadow
      ctx.shadowBlur = 0;

      // 3. Draw Glowing Star Nodes
      nodes.forEach(n => {
        const isHovered = hoveredNode?.id === n.id;
        const isSelected = selectedNode?.id === n.id;

        // Outer Glow Halo (matching reference image)
        const glowRadius = n.radius * (isHovered || isSelected ? 3.5 : 2.4);
        const grad = ctx.createRadialGradient(n.x, n.y, n.radius * 0.2, n.x, n.y, glowRadius);
        grad.addColorStop(0, n.glowColor);
        grad.addColorStop(0.5, n.color + '66');
        grad.addColorStop(1, 'rgba(0, 0, 0, 0)');

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(n.x, n.y, glowRadius, 0, Math.PI * 2);
        ctx.fill();

        // Inner Solid Orb
        ctx.fillStyle = isHovered || isSelected ? '#FFFFFF' : n.color;
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
        ctx.fill();

        // White Core Highlight
        ctx.fillStyle = '#FFFFFF';
        ctx.beginPath();
        ctx.arc(n.x - n.radius * 0.3, n.y - n.radius * 0.3, n.radius * 0.35, 0, Math.PI * 2);
        ctx.fill();

        // Node Label
        ctx.fillStyle = isHovered || isSelected ? '#38BDF8' : '#E2E8F0';
        ctx.font = isHovered || isSelected ? 'bold 11px monospace' : '9px monospace';
        ctx.textAlign = 'center';
        ctx.fillText(n.name, n.x, n.y + n.radius + 14);
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [hoveredNode, selectedNode]);

  // Handle Resize
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current && canvasRef.current) {
        canvasRef.current.width = containerRef.current.clientWidth;
        canvasRef.current.height = 550;
      }
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Mouse Interaction (Hover, Drag, Select)
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    mousePosRef.current = { x: mx, y: my };

    if (isDraggingRef.current && draggedNodeRef.current) {
      draggedNodeRef.current.x = mx;
      draggedNodeRef.current.y = my;
      return;
    }

    const found = nodesRef.current.find(n => Math.hypot(n.x - mx, n.y - my) <= n.radius + 8);
    setHoveredNode(found || null);
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    const found = nodesRef.current.find(n => Math.hypot(n.x - mx, n.y - my) <= n.radius + 8);
    if (found) {
      isDraggingRef.current = true;
      draggedNodeRef.current = found;
      setSelectedNode(found);
    }
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
    draggedNodeRef.current = null;
  };

  return (
    <div className="space-y-4">
      {/* Header Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-[#070B14] p-4 rounded-xl border border-[#1F2A40]">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-5 h-5 text-[#38BDF8] animate-pulse" />
          <span className="text-xs font-bold font-mono text-[#F8FAFC]">
            Architecture Universe — Galaxy Star Cluster Mode
          </span>
          <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-[#38BDF8]/10 text-[#38BDF8] border border-[#38BDF8]/20">
            {nodesRef.current.length} Active Files Connected
          </span>
        </div>

        <div className="flex items-center space-x-3 text-xs font-mono">
          <div className="flex items-center space-x-2">
            <span className="text-[#64748B]">Nodes Density:</span>
            <select
              value={nodeCount}
              onChange={(e) => setNodeCount(Number(e.target.value))}
              className="bg-[#101827] border border-[#1F2A40] text-[#F8FAFC] rounded-lg px-2.5 py-1 focus:outline-none"
            >
              <option value={20}>20 Main Files</option>
              <option value={45}>45 Core Files</option>
              <option value={80}>80 All Repository Files</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Canvas Canvas Wrapper */}
      <div ref={containerRef} className="relative w-full overflow-hidden rounded-2xl border border-[#1F2A40] bg-[#060913] shadow-2xl">
        <canvas
          ref={canvasRef}
          onMouseMove={handleMouseMove}
          onMouseDown={handleMouseDown}
          onMouseUp={handleMouseUp}
          className="w-full cursor-crosshair block"
          style={{ height: '550px' }}
        />

        {/* Legend Overlay */}
        <div className="absolute top-4 left-4 bg-[#070B14]/85 backdrop-blur-md p-3 rounded-xl border border-[#1F2A40] space-y-1.5 text-[11px] font-mono shadow-xl pointer-events-none">
          <div className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider mb-1 font-mono">Architecture Color Keys</div>
          <div className="flex items-center space-x-2"><span className="w-2.5 h-2.5 rounded-full bg-[#00F0FF] shadow-[0_0_8px_#00F0FF]"></span> <span className="text-[#F8FAFC]">Controllers & REST APIs</span></div>
          <div className="flex items-center space-x-2"><span className="w-2.5 h-2.5 rounded-full bg-[#10B981] shadow-[0_0_8px_#10B981]"></span> <span className="text-[#F8FAFC]">Services & Workflows</span></div>
          <div className="flex items-center space-x-2"><span className="w-2.5 h-2.5 rounded-full bg-[#A855F7] shadow-[0_0_8px_#A855F7]"></span> <span className="text-[#F8FAFC]">Repositories & Data Access</span></div>
          <div className="flex items-center space-x-2"><span className="w-2.5 h-2.5 rounded-full bg-[#EAB308] shadow-[0_0_8px_#EAB308]"></span> <span className="text-[#F8FAFC]">Entities & Schemas</span></div>
          <div className="flex items-center space-x-2"><span className="w-2.5 h-2.5 rounded-full bg-[#EF4444] shadow-[0_0_8px_#EF4444]"></span> <span className="text-[#F8FAFC]">Security Risks & Debt</span></div>
        </div>

        {/* Selected Node Details Card Overlay */}
        {selectedNode && (
          <div className="absolute bottom-4 right-4 bg-[#070B14]/95 backdrop-blur-md p-4 rounded-xl border border-[#38BDF8] space-y-2 text-xs font-mono shadow-2xl max-w-sm">
            <div className="flex items-center justify-between border-b border-[#1F2A40] pb-2">
              <span className="font-bold text-[#38BDF8] flex items-center space-x-1.5">
                <FileCode className="w-4 h-4" />
                <span>{selectedNode.name}</span>
              </span>
              <button 
                onClick={() => setSelectedNode(null)} 
                className="text-[#64748B] hover:text-white text-xs"
              >
                ✕
              </button>
            </div>
            <div className="space-y-1 text-[#94A3B8] text-[11px]">
              <div><strong>Path:</strong> {selectedNode.file}</div>
              <div><strong>Stereotype:</strong> <span className="text-[#F8FAFC]">{selectedNode.stereotype}</span></div>
              <div><strong>Connections:</strong> {selectedNode.connections.length} File Links</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
