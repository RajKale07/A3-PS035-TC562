import React, { useEffect, useRef } from 'react';
import cytoscape, { Core } from 'cytoscape';
import { NodeData, LinkData, ResiliencePath } from '../api';

interface NetworkCanvasProps {
  nodes: NodeData[];
  links: LinkData[];
  failedNodes: string[];
  activePath: ResiliencePath | null;
  selectedSource: string | null;
  selectedTarget: string | null;
  onSelectNode: (nodeId: string) => void;
}

export const NetworkCanvas: React.FC<NetworkCanvasProps> = ({
  nodes,
  links,
  failedNodes,
  activePath,
  selectedSource,
  selectedTarget,
  onSelectNode,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Convert nodes to cytoscape elements
    const elements: cytoscape.ElementDefinition[] = [
      ...nodes.map((n) => {
        const isFailed = failedNodes.includes(n.id);
        const isSource = selectedSource === n.id;
        const isTarget = selectedTarget === n.id;
        const inPath = activePath?.nodes.includes(n.id);

        let bgColor = '#3b82f6'; // default blue
        if (n.risk_weight > 0.6) bgColor = '#f97316'; // orange/high risk
        else if (n.risk_weight < 0.3) bgColor = '#10b981'; // green/low risk

        if (isFailed) bgColor = '#ef4444';
        if (inPath) bgColor = '#06b6d4';
        if (isSource) bgColor = '#8b5cf6';
        if (isTarget) bgColor = '#ec4899';

        return {
          data: {
            id: n.id,
            label: n.label || `R${n.id}`,
            risk: n.risk_weight,
            isFailed: isFailed ? 1 : 0,
            isSource: isSource ? 1 : 0,
            isTarget: isTarget ? 1 : 0,
            inPath: inPath ? 1 : 0,
            bgColor,
          },
        };
      }),
      ...links.map((lnk, idx) => {
        const inPath =
          activePath &&
          activePath.nodes.some((n, i) => {
            if (i === activePath.nodes.length - 1) return false;
            const next = activePath.nodes[i + 1];
            return (
              (lnk.source === n && lnk.target === next) ||
              (lnk.source === next && lnk.target === n)
            );
          });

        const isFailedLink =
          failedNodes.includes(lnk.source) || failedNodes.includes(lnk.target);

        return {
          data: {
            id: `e_${lnk.source}_${lnk.target}_${idx}`,
            source: lnk.source,
            target: lnk.target,
            cost: lnk.cost || 1.0,
            latency: lnk.latency_ms || 1.0,
            inPath: inPath ? 1 : 0,
            isFailed: isFailedLink ? 1 : 0,
          },
        };
      }),
    ];

    if (!cyRef.current) {
      cyRef.current = cytoscape({
        container: containerRef.current,
        elements,
        style: [
          {
            selector: 'node',
            style: {
              'background-color': 'data(bgColor)',
              label: 'data(label)',
              color: '#f8fafc',
              'font-size': '12px',
              'font-weight': 'bold',
              'text-valign': 'center',
              'text-halign': 'center',
              width: 38,
              height: 38,
              'border-width': 2,
              'border-color': '#1e293b',
              'transition-property': 'background-color, border-color, width, height',
              'transition-duration': 0.3,
            },
          },
          {
            selector: 'node[isFailed = 1]',
            style: {
              'background-color': '#dc2626',
              'border-color': '#7f1d1d',
              'border-width': 3,
              opacity: 0.5,
              shape: 'diamond',
            },
          },
          {
            selector: 'node[inPath = 1]',
            style: {
              width: 44,
              height: 44,
              'border-width': 3,
              'border-color': '#67e8f9',
            },
          },
          {
            selector: 'node[isSource = 1]',
            style: {
              'border-color': '#c084fc',
              'border-width': 4,
            },
          },
          {
            selector: 'node[isTarget = 1]',
            style: {
              'border-color': '#f472b6',
              'border-width': 4,
            },
          },
          {
            selector: 'edge',
            style: {
              width: 2,
              'line-color': '#475569',
              'curve-style': 'bezier',
              opacity: 0.8,
            },
          },
          {
            selector: 'edge[inPath = 1]',
            style: {
              width: 5,
              'line-color': '#06b6d4',
              opacity: 1.0,
              'z-index': 999,
            },
          },
          {
            selector: 'edge[isFailed = 1]',
            style: {
              'line-color': '#ef4444',
              'line-style': 'dashed',
              opacity: 0.3,
            },
          },
        ],
        layout: {
          name: 'cose',
          animate: true,
          padding: 30,
        },
      });

      cyRef.current.on('tap', 'node', (evt) => {
        const node = evt.target;
        onSelectNode(node.id());
      });
    } else {
      // Update existing cy instance
      const cy = cyRef.current;
      cy.batch(() => {
        cy.elements().remove();
        cy.add(elements);
        cy.layout({ name: 'cose', animate: false, padding: 30 }).run();
      });
    }

    return () => {
      // keep instance
    };
  }, [nodes, links, failedNodes, activePath, selectedSource, selectedTarget]);

  return (
    <div className="relative w-full h-full bg-slate-900 rounded-xl overflow-hidden border border-slate-800 shadow-2xl">
      <div ref={containerRef} className="w-full h-full" />
      <div className="absolute top-4 left-4 bg-slate-950/80 backdrop-blur-md px-3 py-2 rounded-lg border border-slate-800 text-xs text-slate-300 flex items-center space-x-3 pointer-events-none">
        <span className="flex items-center space-x-1">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block"></span>
          <span>Low Risk</span>
        </span>
        <span className="flex items-center space-x-1">
          <span className="w-2.5 h-2.5 rounded-full bg-orange-500 inline-block"></span>
          <span>High Risk</span>
        </span>
        <span className="flex items-center space-x-1">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500 inline-block"></span>
          <span>Failed</span>
        </span>
        <span className="flex items-center space-x-1">
          <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 inline-block"></span>
          <span>Resilient Path</span>
        </span>
      </div>
    </div>
  );
};
