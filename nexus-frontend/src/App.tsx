import React, { useEffect, useState } from 'react';
import {
  fetchTopologies,
  fetchTopologyDetails,
  generateTopology,
  runSimulation,
  optimizePaths,
  runCascadeSimulation,
  runWSL2Emulation,
  generateRecoveryPlan,
  getTopologyTelemetry,
  TopologySummary,
  TopologyDetails,
  SimulationResult,
  OptimizationResponse,
  ResiliencePath,
  CascadeReport,
  EmulationReport,
  RecoveryPlan,
  RecoveryExecution,
  TelemetrySnapshot,
} from './api';
import { NetworkCanvas } from './components/NetworkCanvas';
import { ControlPanel } from './components/ControlPanel';
import { TelemetryDrawer } from './components/TelemetryDrawer';
import { RecoveryModal } from './components/RecoveryModal';
import { Network, Database, Cpu, CheckCircle } from 'lucide-react';

export const App: React.FC = () => {
  const [topologies, setTopologies] = useState<TopologySummary[]>([]);
  const [currentTopology, setCurrentTopology] = useState<TopologyDetails | null>(null);
  const [selectedTopologyId, setSelectedTopologyId] = useState<number | null>(null);

  const [failedNodes, setFailedNodes] = useState<string[]>([]);
  const [simulation, setSimulation] = useState<SimulationResult | null>(null);
  const [cascadeResult, setCascadeResult] = useState<CascadeReport | null>(null);
  const [emulationResult, setEmulationResult] = useState<EmulationReport | null>(null);
  const [telemetrySnapshot, setTelemetrySnapshot] = useState<TelemetrySnapshot | null>(null);

  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);
  const [optimization, setOptimization] = useState<OptimizationResponse | null>(null);
  const [activePath, setActivePath] = useState<ResiliencePath | null>(null);

  const [recoveryPlan, setRecoveryPlan] = useState<RecoveryPlan | null>(null);
  const [notification, setNotification] = useState<string | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isLoadingTelemetry, setIsLoadingTelemetry] = useState<boolean>(false);

  // Load topology list on initial mount
  useEffect(() => {
    loadTopologies();
  }, []);

  const showNotification = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 4000);
  };

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
      setCascadeResult(null);
      setEmulationResult(null);
      setTelemetrySnapshot(null);
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

  const handleGenerateTopology = async (name: string, nodes: number, prob: number, preset: string = 'random') => {
    setIsLoading(true);
    try {
      const res = await generateTopology(name, nodes, prob, 42, preset);
      await loadTopologies();
      handleSelectTopology(res.id);
      showNotification(`Topology "${name}" generated successfully`);
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
      showNotification(`Simulation finished: ${(res.resilience_score * 100).toFixed(1)}% resilience`);
    } catch (err) {
      console.error('Failed to run simulation', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunCascade = async () => {
    if (!selectedTopologyId || !currentTopology) return;
    setIsLoading(true);
    try {
      const firstNode = currentTopology.nodes[0]?.id || '0';
      const res = await runCascadeSimulation(selectedTopologyId, [firstNode], 0.2, 10);
      setCascadeResult(res);
      setFailedNodes(res.all_failed);
      showNotification(`Cascade stabilized in ${res.total_steps} step(s) with ${res.cascade_amplification}x amplification`);
    } catch (err) {
      console.error('Failed to run cascade', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunWSL2 = async () => {
    if (!selectedTopologyId) return;
    setIsLoading(true);
    try {
      const res = await runWSL2Emulation(selectedTopologyId, failedNodes);
      setEmulationResult(res);
      showNotification(`WSL2 Mininet complete: ${res.packet_loss_pct.toFixed(1)}% packet loss`);
    } catch (err) {
      console.error('WSL2 Emulation failed', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePollTelemetry = async () => {
    if (!selectedTopologyId) return;
    setIsLoadingTelemetry(true);
    try {
      const res = await getTopologyTelemetry(selectedTopologyId);
      setTelemetrySnapshot(res);
      showNotification(`Polled ${res.link_count} links (${res.alert_count} alert(s) detected)`);
    } catch (err) {
      console.error('Failed to poll telemetry', err);
    } finally {
      setIsLoadingTelemetry(false);
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

  const handleOptimize = async (
    source: string,
    target: string,
    maxRisk: number,
    tier: string = 'CRITICAL',
    minBw: number = 1000
  ) => {
    if (!selectedTopologyId) return;
    setIsLoading(true);
    try {
      const res = await optimizePaths(selectedTopologyId, source, target, maxRisk, 3, tier, minBw);
      setOptimization(res);
      if (res.paths.length > 0) {
        setActivePath(res.paths[0]);
        showNotification(`Found ${res.paths.length} resilient path(s) [${tier} Tier]`);
      } else {
        showNotification(`No feasible path under budget [${tier} Tier]`);
      }
    } catch (err) {
      console.error('Optimization failed', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateRecovery = async () => {
    if (!selectedTopologyId || !selectedSource || !selectedTarget) return;
    setIsLoading(true);
    try {
      const plan = await generateRecoveryPlan(selectedTopologyId, selectedSource, selectedTarget, 3);
      setRecoveryPlan(plan);
    } catch (err) {
      console.error('Failed to generate recovery plan', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRecoveryExecuted = (result: RecoveryExecution) => {
    setRecoveryPlan(null);
    showNotification(
      `Plan #${result.plan_id} executed! Resilience: ${(result.resilience_after ? (result.resilience_after * 100).toFixed(1) : '100')}%` +
      (result.replanning_triggered ? ' (Adaptive replanning triggered!)' : '')
    );
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 select-none font-sans">
      {/* Top Bar */}
      <header className="h-12 border-b border-slate-800 px-6 flex items-center justify-between bg-slate-900/60 backdrop-blur-md">
        <div className="flex items-center space-x-3">
          <div className="w-3 h-3 rounded-full bg-cyan-400 animate-pulse" />
          <span className="font-semibold text-sm text-slate-200">
            NEXUS Research Workspace
          </span>
          <span className="text-xs text-slate-500 font-mono">Adaptive Network Resilience Intelligence</span>
        </div>

        {notification && (
          <div className="flex items-center space-x-1.5 px-3 py-1 bg-cyan-950 border border-cyan-800/80 text-cyan-300 rounded-full text-xs animate-fade-in">
            <CheckCircle className="w-3.5 h-3.5" />
            <span>{notification}</span>
          </div>
        )}

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
          onRunCascade={handleRunCascade}
          onRunWSL2={handleRunWSL2}
          onOptimize={handleOptimize}
          onGenerateRecovery={handleGenerateRecovery}
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
            <TelemetryDrawer
              simulation={simulation}
              optimization={optimization}
              cascadeResult={cascadeResult}
              emulationResult={emulationResult}
              telemetrySnapshot={telemetrySnapshot}
              onRefreshTelemetry={handlePollTelemetry}
              isLoadingTelemetry={isLoadingTelemetry}
            />
          </div>
        </main>
      </div>

      {/* Human-in-the-loop Recovery Modal */}
      {recoveryPlan && (
        <RecoveryModal
          plan={recoveryPlan}
          onClose={() => setRecoveryPlan(null)}
          onExecuted={handleRecoveryExecuted}
        />
      )}
    </div>
  );
};

export default App;
