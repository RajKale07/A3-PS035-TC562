import React, { useEffect, useState } from 'react';
import {
  fetchTopologies,
  fetchTopologyDetails,
  generateTopology,
  runSimulation,
  optimizePaths,
  TopologySummary,
  TopologyDetails,
  SimulationResult,
  OptimizationResponse,
  ResiliencePath,
} from './api';
import { NetworkCanvas } from './components/NetworkCanvas';
import { ControlPanel } from './components/ControlPanel';
import { TelemetryDrawer } from './components/TelemetryDrawer';
import { Network, Database, Cpu } from 'lucide-react';

export const App: React.FC = () => {
  const [topologies, setTopologies] = useState<TopologySummary[]>([]);
  const [currentTopology, setCurrentTopology] = useState<TopologyDetails | null>(null);
  const [selectedTopologyId, setSelectedTopologyId] = useState<number | null>(null);

  const [failedNodes, setFailedNodes] = useState<string[]>([]);
  const [simulation, setSimulation] = useState<SimulationResult | null>(null);

  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);
  const [optimization, setOptimization] = useState<OptimizationResponse | null>(null);
  const [activePath, setActivePath] = useState<ResiliencePath | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Load topology list on initial mount
  useEffect(() => {
    loadTopologies();
  }, []);

  const loadTopologies = async () => {
    try {
      const data = await fetchTopologies();
      setTopologies(data);
      if (data.length > 0 && !selectedTopologyId) {
        handleSelectTopology(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load topologies', err);
    }
  };

  const handleSelectTopology = async (id: number) => {
    setSelectedTopologyId(id);
    setIsLoading(true);
    try {
      const details = await fetchTopologyDetails(id);
      setCurrentTopology(details);
      setFailedNodes([]);
      setSimulation(null);
      setOptimization(null);
      setActivePath(null);
      setSelectedSource(null);
      setSelectedTarget(null);
    } catch (err) {
      console.error('Failed to load topology details', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateTopology = async (name: string, nodes: number, prob: number) => {
    setIsLoading(true);
    try {
      const res = await generateTopology(name, nodes, prob);
      await loadTopologies();
      handleSelectTopology(res.id);
    } catch (err) {
      console.error('Failed to generate topology', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunSimulation = async (type: 'random' | 'hub') => {
    if (!selectedTopologyId) return;
    setIsLoading(true);
    try {
      const res = await runSimulation(selectedTopologyId, type);
      setSimulation(res);
      setFailedNodes(res.failed_nodes);
    } catch (err) {
      console.error('Failed to run simulation', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectNode = (nodeId: string) => {
    if (!selectedSource) {
      setSelectedSource(nodeId);
    } else if (!selectedTarget && nodeId !== selectedSource) {
      setSelectedTarget(nodeId);
    } else {
      setSelectedSource(nodeId);
      setSelectedTarget(null);
      setOptimization(null);
      setActivePath(null);
    }
  };

  const handleOptimize = async (source: string, target: string, maxRisk: number) => {
    if (!selectedTopologyId) return;
    setIsLoading(true);
    try {
      const res = await optimizePaths(selectedTopologyId, source, target, maxRisk);
      setOptimization(res);
      if (res.paths.length > 0) {
        setActivePath(res.paths[0]);
      }
    } catch (err) {
      console.error('Optimization failed', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 select-none">
      {/* Top Bar */}
      <header className="h-12 border-b border-slate-800 px-6 flex items-center justify-between bg-slate-900/60 backdrop-blur-md">
        <div className="flex items-center space-x-3">
          <div className="w-3 h-3 rounded-full bg-cyan-400 animate-pulse" />
          <span className="font-semibold text-sm text-slate-200">
            NEXUS Research Workspace
          </span>
          <span className="text-xs text-slate-500 font-mono">v0.1.0-alpha</span>
        </div>
        <div className="flex items-center space-x-6 text-xs text-slate-400">
          <div className="flex items-center space-x-1.5">
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            <span>FastAPI: <strong className="text-slate-200 font-mono">127.0.0.1:8000</strong></span>
          </div>
          <div className="flex items-center space-x-1.5">
            <Database className="w-3.5 h-3.5 text-emerald-400" />
            <span>PostgreSQL: <strong className="text-slate-200 font-mono">nexus_db</strong></span>
          </div>
          <div className="flex items-center space-x-1.5">
            <Network className="w-3.5 h-3.5 text-purple-400" />
            <span>Nodes: <strong className="text-slate-200 font-mono">{currentTopology?.nodes.length || 0}</strong></span>
          </div>
        </div>
      </header>

      {/* Main Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Control Panel */}
        <ControlPanel
          topologies={topologies}
          selectedTopologyId={selectedTopologyId}
          onSelectTopology={handleSelectTopology}
          onGenerateTopology={handleGenerateTopology}
          onRunSimulation={handleRunSimulation}
          onOptimize={handleOptimize}
          selectedSource={selectedSource}
          selectedTarget={selectedTarget}
          paths={optimization?.paths || []}
          onSelectPath={setActivePath}
          activePath={activePath}
          isLoading={isLoading}
        />

        {/* Center Canvas Area */}
        <main className="flex-1 flex flex-col p-4 bg-slate-950 overflow-hidden">
          <div className="flex-1 relative">
            <NetworkCanvas
              nodes={currentTopology?.nodes || []}
              links={currentTopology?.links || []}
              failedNodes={failedNodes}
              activePath={activePath}
              selectedSource={selectedSource}
              selectedTarget={selectedTarget}
              onSelectNode={handleSelectNode}
            />
          </div>

          {/* Bottom Telemetry Drawer */}
          <div className="mt-4">
            <TelemetryDrawer simulation={simulation} optimization={optimization} />
          </div>
        </main>
      </div>
    </div>
  );
};

export default App;
