import React, { useState } from 'react';
import { TopologySummary, ResiliencePath } from '../api';
import {
  Play,
  Zap,
  RefreshCw,
  PlusCircle,
  ShieldAlert,
  GitCommit,
  Layers,
  Terminal,
  ShieldCheck,
} from 'lucide-react';

interface ControlPanelProps {
  topologies: TopologySummary[];
  selectedTopologyId: number | null;
  onSelectTopology: (id: number) => void;
  onGenerateTopology: (name: string, nodes: number, prob: number, preset?: string) => void;
  onRunSimulation: (type: 'random' | 'hub') => void;
  onRunCascade: () => void;
  onRunWSL2: () => void;
  onOptimize: (source: string, target: string, maxRisk: number, tier: string, minBw: number) => void;
  onGenerateRecovery: () => void;
  selectedSource: string | null;
  selectedTarget: string | null;
  paths: ResiliencePath[];
  onSelectPath: (p: ResiliencePath) => void;
  activePath: ResiliencePath | null;
  isLoading: boolean;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({
  topologies,
  selectedTopologyId,
  onSelectTopology,
  onGenerateTopology,
  onRunSimulation,
  onRunCascade,
  onRunWSL2,
  onOptimize,
  onGenerateRecovery,
  selectedSource,
  selectedTarget,
  paths,
  onSelectPath,
  activePath,
  isLoading,
}) => {
  const [tab, setTab] = useState<'topology' | 'simulate' | 'optimize'>('topology');
  const [genName, setGenName] = useState(`mesh_${Math.floor(Math.random() * 1000)}`);
  const [genNodes, setGenNodes] = useState(8);
  const [genProb, setGenProb] = useState(0.4);
  const [genPreset, setGenPreset] = useState<'random' | 'abilene' | 'fat_tree' | 'ring'>('random');

  const [maxRisk, setMaxRisk] = useState(4.0);
  const [serviceTier, setServiceTier] = useState<'CRITICAL' | 'BUSINESS' | 'BEST_EFFORT'>('CRITICAL');
  const [minBandwidth, setMinBandwidth] = useState(1000);

  return (
    <div className="w-80 h-full bg-slate-900 border-r border-slate-800 flex flex-col p-4 space-y-4 font-sans">
      {/* Top Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight text-white flex items-center space-x-2">
          <Zap className="w-5 h-5 text-cyan-400" />
          <span>NEXUS Core</span>
        </h1>
        <p className="text-xs text-slate-400">Adaptive Network Resilience Intelligence</p>
      </div>

      {/* Tabs */}
      <div className="grid grid-cols-3 gap-1 bg-slate-950 p-1 rounded-lg text-xs font-medium">
        <button
          onClick={() => setTab('topology')}
          className={`py-1.5 rounded-md transition-all ${
            tab === 'topology' ? 'bg-cyan-500/20 text-cyan-300 font-semibold' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Topology
        </button>
        <button
          onClick={() => setTab('simulate')}
          className={`py-1.5 rounded-md transition-all ${
            tab === 'simulate' ? 'bg-red-500/20 text-red-300 font-semibold' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Simulate
        </button>
        <button
          onClick={() => setTab('optimize')}
          className={`py-1.5 rounded-md transition-all ${
            tab === 'optimize' ? 'bg-emerald-500/20 text-emerald-300 font-semibold' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Optimize
        </button>
      </div>

      {/* Tab Contents */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1">
        {tab === 'topology' && (
          <div className="space-y-4 text-xs">
            {/* Select Topology */}
            <div>
              <label className="block text-slate-400 mb-1">Loaded Topology</label>
              <select
                value={selectedTopologyId || ''}
                onChange={(e) => onSelectTopology(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                {topologies.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({t.num_nodes}N / {t.num_links}L)
                  </option>
                ))}
              </select>
            </div>

            {/* Generator */}
            <div className="border-t border-slate-800 pt-3 space-y-3">
              <span className="font-semibold text-slate-300 flex items-center space-x-1">
                <PlusCircle className="w-3.5 h-3.5 text-cyan-400" />
                <span>Topology Generator & Presets</span>
              </span>

              <div>
                <label className="block text-slate-400 mb-1">Architecture Archetype</label>
                <select
                  value={genPreset}
                  onChange={(e) => setGenPreset(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="random">Random Erdős–Rényi Mesh</option>
                  <option value="abilene">Abilene / Internet2 US Backbone (12 PoPs)</option>
                  <option value="fat_tree">Fat-Tree K=4 DC (Core/Agg/Edge)</option>
                  <option value="ring">Metro Ring with Chord Shortcuts</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Topology Name</label>
                <input
                  type="text"
                  value={genName}
                  onChange={(e) => setGenName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              {genPreset === 'random' && (
                <>
                  <div>
                    <label className="block text-slate-400 mb-1">Node Count: {genNodes}</label>
                    <input
                      type="range"
                      min="4"
                      max="25"
                      value={genNodes}
                      onChange={(e) => setGenNodes(Number(e.target.value))}
                      className="w-full accent-cyan-400"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 mb-1">Edge Probability: {genProb}</label>
                    <input
                      type="range"
                      min="0.2"
                      max="0.8"
                      step="0.05"
                      value={genProb}
                      onChange={(e) => setGenProb(Number(e.target.value))}
                      className="w-full accent-cyan-400"
                    />
                  </div>
                </>
              )}

              <button
                disabled={isLoading}
                onClick={() => {
                  onGenerateTopology(genName, genNodes, genProb, genPreset);
                  setGenName(`mesh_${Math.floor(Math.random() * 1000)}`);
                }}
                className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-medium py-2 rounded-lg transition flex items-center justify-center space-x-2 shadow-lg shadow-cyan-600/20"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                <span>Build & Persist Topology</span>
              </button>
            </div>
          </div>
        )}

        {tab === 'simulate' && (
          <div className="space-y-4 text-xs">
            <div>
              <span className="font-semibold text-slate-300 flex items-center space-x-1 mb-2">
                <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
                <span>Resilience Failure Stress-Testing</span>
              </span>
              <p className="text-slate-400 mb-3">
                Simulate targeted hub outages, multi-step Motter-Lai cascade redistributions, or real Mininet packet loss.
              </p>
            </div>

            <button
              disabled={isLoading || !selectedTopologyId}
              onClick={() => onRunSimulation('random')}
              className="w-full bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-medium py-2.5 rounded-lg transition flex items-center justify-center space-x-2"
            >
              <Play className="w-3.5 h-3.5 text-amber-400" />
              <span>Random 25% Node Failure</span>
            </button>

            <button
              disabled={isLoading || !selectedTopologyId}
              onClick={() => onRunSimulation('hub')}
              className="w-full bg-red-950/40 hover:bg-red-900/50 border border-red-800/50 text-red-200 font-medium py-2.5 rounded-lg transition flex items-center justify-center space-x-2"
            >
              <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
              <span>Targeted Hub Destruction</span>
            </button>

            <button
              disabled={isLoading || !selectedTopologyId}
              onClick={onRunCascade}
              className="w-full bg-purple-950/40 hover:bg-purple-900/50 border border-purple-800/50 text-purple-200 font-medium py-2.5 rounded-lg transition flex items-center justify-center space-x-2"
            >
              <Layers className="w-3.5 h-3.5 text-purple-400" />
              <span>Motter-Lai Cascading Overload</span>
            </button>

            <button
              disabled={isLoading || !selectedTopologyId}
              onClick={onRunWSL2}
              className="w-full bg-cyan-950/40 hover:bg-cyan-900/50 border border-cyan-800/50 text-cyan-200 font-medium py-2.5 rounded-lg transition flex items-center justify-center space-x-2"
            >
              <Terminal className="w-3.5 h-3.5 text-cyan-400" />
              <span>Run WSL2 Mininet Emulation</span>
            </button>
          </div>
        )}

        {tab === 'optimize' && (
          <div className="space-y-4 text-xs">
            <div>
              <span className="font-semibold text-slate-300 flex items-center space-x-1 mb-2">
                <GitCommit className="w-3.5 h-3.5 text-emerald-400" />
                <span>OR-Tools CP-SAT QoS Optimizer</span>
              </span>
              <p className="text-slate-400 mb-3">
                Click nodes on the canvas to set Source and Target, configure SLA service tier, and generate human-authorized recovery actions.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                <span className="text-[10px] text-purple-400 uppercase font-bold block">Source</span>
                <span className="font-mono text-sm text-slate-100">
                  {selectedSource ? `Node R${selectedSource}` : 'Select Node'}
                </span>
              </div>
              <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                <span className="text-[10px] text-pink-400 uppercase font-bold block">Target</span>
                <span className="font-mono text-sm text-slate-100">
                  {selectedTarget ? `Node R${selectedTarget}` : 'Select Node'}
                </span>
              </div>
            </div>

            {/* QoS Tier */}
            <div>
              <label className="block text-slate-400 mb-1">Critical-Service QoS Tier</label>
              <select
                value={serviceTier}
                onChange={(e) => setServiceTier(e.target.value as any)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500 font-medium"
              >
                <option value="CRITICAL">🔴 CRITICAL Tier (Strict Low-Risk, Max Resiliency)</option>
                <option value="BUSINESS">🟡 BUSINESS Tier (Balanced Latency & Cost)</option>
                <option value="BEST_EFFORT">🟢 BEST_EFFORT (Min Cost Routing)</option>
              </select>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Min Bandwidth: {minBandwidth} Mbps</label>
              <input
                type="range"
                min="100"
                max="10000"
                step="100"
                value={minBandwidth}
                onChange={(e) => setMinBandwidth(Number(e.target.value))}
                className="w-full accent-emerald-400"
              />
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Max Risk Budget: {maxRisk.toFixed(1)}</label>
              <input
                type="range"
                min="1.0"
                max="8.0"
                step="0.5"
                value={maxRisk}
                onChange={(e) => setMaxRisk(Number(e.target.value))}
                className="w-full accent-emerald-400"
              />
            </div>

            <div className="space-y-2">
              <button
                disabled={isLoading || !selectedSource || !selectedTarget || selectedSource === selectedTarget}
                onClick={() => onOptimize(selectedSource!, selectedTarget!, maxRisk, serviceTier, minBandwidth)}
                className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium py-2 rounded-lg transition flex items-center justify-center space-x-2 shadow-lg shadow-emerald-600/20"
              >
                <Zap className="w-3.5 h-3.5" />
                <span>Solve Resilient Paths</span>
              </button>

              <button
                disabled={isLoading || !selectedTopologyId || !selectedSource || !selectedTarget || selectedSource === selectedTarget}
                onClick={onGenerateRecovery}
                className="w-full bg-slate-800 hover:bg-slate-700 disabled:opacity-50 border border-slate-700 text-slate-200 font-medium py-2 rounded-lg transition flex items-center justify-center space-x-2"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                <span>Generate Recovery Plan</span>
              </button>
            </div>

            {paths.length > 0 && (
              <div className="border-t border-slate-800 pt-3 space-y-2">
                <span className="font-semibold text-slate-300 block">Candidate Paths ({paths.length})</span>
                {paths.map((p, idx) => (
                  <div
                    key={idx}
                    onClick={() => onSelectPath(p)}
                    className={`p-2 rounded-lg border cursor-pointer transition ${
                      activePath === p
                        ? 'bg-cyan-950/40 border-cyan-500 text-cyan-200'
                        : 'bg-slate-950/50 border-slate-800 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex justify-between font-medium">
                      <span>Path #{idx + 1} ({p.hop_count} hops)</span>
                      <span className="text-emerald-400 font-mono">${p.total_cost}</span>
                    </div>
                    <div className="text-[11px] text-slate-400 mt-1 flex justify-between">
                      <span>Risk: {p.total_risk}</span>
                      <span>Latency: {p.total_latency_ms} ms</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
