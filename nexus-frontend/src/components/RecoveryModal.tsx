import React, { useState } from 'react';
import {
  RecoveryPlan,
  RecoveryExecution,
  approveRecoveryPlan,
  rejectRecoveryPlan,
} from '../api';
import { CheckCircle2, XCircle, AlertTriangle, ShieldCheck } from 'lucide-react';

interface Props {
  plan: RecoveryPlan;
  onClose: () => void;
  onExecuted: (result: RecoveryExecution) => void;
}

export const RecoveryModal: React.FC<Props> = ({ plan, onClose, onExecuted }) => {
  const [loading, setLoading] = useState(false);
  const [notes, setNotes] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleApprove = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await approveRecoveryPlan(plan.plan_id, notes);
      onExecuted(result);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Approval failed');
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    setLoading(true);
    setError(null);
    try {
      await rejectRecoveryPlan(plan.plan_id, notes);
      onClose();
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Rejection failed');
    } finally {
      setLoading(false);
    }
  };

  const statusColor: Record<string, string> = {
    PENDING: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    APPROVED: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    REJECTED: 'bg-red-500/20 text-red-300 border-red-500/30',
    EXECUTED: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 w-full max-w-lg shadow-2xl space-y-4 text-slate-100 font-sans">
        {/* Header */}
        <div className="flex justify-between items-center pb-3 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <h2 className="text-base font-semibold">Human-in-the-Loop Recovery Authorization</h2>
          </div>
          <span className={`px-2.5 py-0.5 rounded-full text-xs font-mono font-medium border ${statusColor[plan.status] || 'bg-slate-800 text-slate-300'}`}>
            {plan.status}
          </span>
        </div>

        {/* Resilience Metrics */}
        <div className="grid grid-cols-2 gap-3 bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs">
          <div>
            <span className="text-slate-400 block mb-0.5">Resilience Before Failure</span>
            <span className="text-base font-bold text-amber-400 font-mono">
              {plan.resilience_before !== undefined ? `${(plan.resilience_before * 100).toFixed(1)}%` : 'N/A'}
            </span>
          </div>
          <div>
            <span className="text-slate-400 block mb-0.5">Plan ID / Target</span>
            <span className="text-base font-bold text-cyan-400 font-mono">
              #{plan.plan_id} (Topo #{plan.topology_id})
            </span>
          </div>
        </div>

        {/* Proposed Recovery Actions */}
        <div>
          <span className="text-xs font-semibold text-slate-300 block mb-2">
            Proposed Rerouting Actions ({plan.actions.length})
          </span>
          <div className="max-h-48 overflow-y-auto space-y-2 bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs">
            {plan.actions.length === 0 ? (
              <span className="text-slate-500 italic">No rerouting actions generated.</span>
            ) : (
              plan.actions.map((act, idx) => (
                <div key={idx} className="p-2 bg-slate-900 rounded border border-slate-800 flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-cyan-400 font-bold uppercase">{act.action}</span>
                    <span className="text-slate-400">Path:</span>
                    <span className="font-mono text-emerald-300 flex items-center space-x-1">
                      {act.path.join(' → ')}
                    </span>
                  </div>
                  {act.total_cost !== undefined && (
                    <span className="font-mono text-slate-400 text-[11px]">Cost: {act.total_cost}</span>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Notes */}
        <div>
          <label className="text-xs text-slate-400 block mb-1">Authorization Notes / Reason</label>
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g., Authorized after verifying link degradation..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
          />
        </div>

        {error && (
          <div className="p-2.5 bg-red-950/50 border border-red-800 text-red-200 text-xs rounded-lg flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-end space-x-2 pt-2 border-t border-slate-800 text-xs">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-3.5 py-1.5 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 transition"
          >
            Cancel
          </button>
          <button
            onClick={handleReject}
            disabled={loading}
            className="px-3.5 py-1.5 rounded-lg bg-red-900/60 hover:bg-red-800 text-red-200 font-medium transition flex items-center space-x-1.5"
          >
            <XCircle className="w-3.5 h-3.5" />
            <span>Reject Plan</span>
          </button>
          <button
            onClick={handleApprove}
            disabled={loading}
            className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition flex items-center space-x-1.5 shadow-lg shadow-emerald-600/20"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{loading ? 'Executing...' : 'Approve & Execute'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
