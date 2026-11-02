import React from 'react';
import { SimulationResult, OptimizationResponse } from '../api';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';
import { Activity, ShieldCheck, Gauge, Clock } from 'lucide-react';

interface TelemetryDrawerProps {
  simulation: SimulationResult | null;
  optimization: OptimizationResponse | null;
}

export const TelemetryDrawer: React.FC<TelemetryDrawerProps> = ({
  simulation,
  optimization,
}) => {
  const chartData = optimization?.paths.map((p, idx) => ({
    name: `Path ${idx + 1}`,
    cost: p.total_cost,
    latency: p.total_latency_ms,
    risk: p.total_risk,
  })) || [];

  return (
    <div className="h-48 bg-slate-900 border-t border-slate-800 p-4 flex space-x-6">
      {/* Metric Cards */}
      <div className="w-1/3 grid grid-cols-2 gap-3">
        <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Resilience Score</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white mt-1">
            {simulation ? (simulation.resilience_score * 100).toFixed(1) + '%' : '--'}
          </div>
          <div className="text-[10px] text-slate-500">
            {simulation ? `${simulation.surviving_nodes} nodes preserved` : 'Run a simulation'}
          </div>
        </div>

        <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Connectivity</span>
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-cyan-400 mt-1">
            {simulation ? (simulation.connectivity_ratio * 100).toFixed(1) + '%' : '--'}
          </div>
          <div className="text-[10px] text-slate-500">
            {simulation ? `${simulation.components} component(s)` : 'Awaiting test'}
          </div>
        </div>

        <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Solver Time</span>
            <Clock className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-purple-400 mt-1">
            {optimization ? `${optimization.duration_ms} ms` : '--'}
          </div>
          <div className="text-[10px] text-slate-500">
            {optimization ? `Status: ${optimization.solver_status}` : 'OR-Tools CP-SAT'}
          </div>
        </div>

        <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Avg Hop Count</span>
            <Gauge className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
            {optimization && optimization.paths.length > 0
              ? (
                  optimization.paths.reduce((acc, p) => acc + p.hop_count, 0) /
                  optimization.paths.length
                ).toFixed(1)
              : '--'}
          </div>
          <div className="text-[10px] text-slate-500">
            {optimization?.paths.length || 0} paths discovered
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="flex-1 bg-slate-950 p-3 rounded-xl border border-slate-800 flex flex-col">
        <span className="text-xs font-semibold text-slate-400 mb-1">
          Path Metrics Comparison (Cost vs Latency)
        </span>
        <div className="flex-1 w-full">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }}
                />
                <Bar dataKey="cost" fill="#06b6d4" name="Cost" radius={[4, 4, 0, 0]} />
                <Bar dataKey="latency" fill="#8b5cf6" name="Latency (ms)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="w-full h-full flex items-center justify-center text-xs text-slate-600">
              Run path optimization to compare multi-path metrics
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
