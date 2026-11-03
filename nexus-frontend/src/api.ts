import axios from 'axios';

const API_BASE = '/api/v1';

const api = axios.create({ baseURL: API_BASE });

export interface TopologySummary {
  id: number;
  name: string;
  description: string | null;
  num_nodes: number;
  num_links: number;
}

export interface NodeData {
  id: string;
  label?: string;
  node_type?: string;
  risk_weight: number;
}

export interface LinkData {
  source: string;
  target: string;
  bandwidth_mbps?: number;
  latency_ms?: number;
  cost?: number;
}

export interface TopologyDetails {
  id: number;
  name: string;
  description?: string;
  nodes: NodeData[];
  links: LinkData[];
}

export interface SimulationResult {
  simulation_id: number;
  topology_name: string;
  scenario: string;
  resilience_score: number;
  connectivity_ratio: number;
  avg_path_length: number | null;
  failed_nodes: string[];
  surviving_nodes: number;
  surviving_edges: number;
  components: number;
  duration_ms: number;
}

export interface ResiliencePath {
  nodes: string[];
  total_cost: number;
  total_risk: number;
  total_latency_ms: number;
  hop_count: number;
}

export interface OptimizationResponse {
  topology_name: string;
  source: string;
  target: string;
  feasible: boolean;
  solver_status: string;
  duration_ms: number;
  paths: ResiliencePath[];
}

// ── Topology ─────────────────────────────────────────────────────────
export const fetchTopologies = async (): Promise<TopologySummary[]> => {
  const res = await axios.get(`${API_BASE}/topologies/`);
  return res.data;
};

export const fetchTopologyDetails = async (id: number): Promise<TopologyDetails> => {
  const res = await axios.get(`${API_BASE}/topologies/${id}`);
  return res.data;
};

export const generateTopology = async (
  name: string,
  numNodes: number,
  edgeProbability: number,
  seed = 42,
  topologyType = 'random'
): Promise<any> => {
  const res = await axios.post(`${API_BASE}/topologies/generate`, {
    name,
    num_nodes: numNodes,
    edge_probability: edgeProbability,
    seed,
    topology_type: topologyType,
  });
  return res.data;
};

// ── Simulation ───────────────────────────────────────────────────────
export const runSimulation = async (
  topologyId: number,
  scenarioType: 'random' | 'hub' | 'custom',
  failureFraction = 0.2,
  topKHubs = 2,
  customFailedNodes: string[] = []
): Promise<SimulationResult> => {
  const res = await axios.post(`${API_BASE}/simulations/run`, {
    topology_id: topologyId,
    scenario_type: scenarioType,
    failure_fraction: failureFraction,
    top_k_hubs: topKHubs,
    custom_failed_nodes: customFailedNodes,
  });
  return res.data;
};

// ── Optimizer ────────────────────────────────────────────────────────
export const optimizePaths = async (
  topologyId: number,
  source: string,
  target: string,
  maxRisk = 5.0,
  maxPaths = 3,
  serviceTier = 'CRITICAL',
  minBandwidthMbps = 0.0
): Promise<OptimizationResponse> => {
  const res = await axios.post(`${API_BASE}/optimizer/paths`, {
    topology_id: topologyId,
    source,
    target,
    max_risk: maxRisk,
    max_paths: maxPaths,
    service_tier: serviceTier,
    min_bandwidth_mbps: minBandwidthMbps,
  });
  return res.data;
};

// ── Cascade Failure ──────────────────────────────────────────────────
export interface CascadeStep {
  step: number;
  newly_failed: string[];
  overloaded: string[];
  surviving_nodes: number;
  surviving_edges: number;
  load_distribution: Record<string, number>;
}

export interface CascadeReport {
  topology_id: number;
  topology_name: string;
  total_steps: number;
  initial_failed: string[];
  all_failed: string[];
  steps: CascadeStep[];
  final_resilience_score: number;
  final_connectivity_ratio: number;
  cascade_amplification: number;
  duration_ms: number;
}

export async function runCascadeSimulation(
  topologyId: number,
  initialFailedNodes: string[],
  tolerance = 0.2,
  maxSteps = 20
): Promise<CascadeReport> {
  const res = await api.post('/simulations/cascade', {
    topology_id: topologyId,
    initial_failed_nodes: initialFailedNodes,
    tolerance,
    max_steps: maxSteps,
  });
  return res.data;
}

// ── Recovery Plans ───────────────────────────────────────────────────
export interface RecoveryAction {
  action: string;
  path: string[];
  total_cost: number;
}

export interface RecoveryPlan {
  plan_id: number;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXECUTED';
  topology_id: number;
  actions: RecoveryAction[];
  optimizer_result?: Record<string, unknown>;
  resilience_before?: number;
  created_at?: string;
}

export interface RecoveryExecution {
  plan_id: number;
  status: string;
  resilience_before?: number;
  resilience_after?: number;
  replanning_triggered: boolean;
  new_plan_id?: number;
  executed_at?: string;
}

export async function generateRecoveryPlan(
  topologyId: number,
  source = '0',
  target = '1',
  maxPaths = 3
): Promise<RecoveryPlan> {
  const res = await api.post('/recovery/generate', {
    topology_id: topologyId,
    source,
    target,
    max_paths: maxPaths,
  });
  return res.data;
}

export async function approveRecoveryPlan(planId: number, notes = ''): Promise<RecoveryExecution> {
  const res = await api.post(`/recovery/${planId}/approve`, { notes });
  return res.data;
}

export async function rejectRecoveryPlan(planId: number, notes = ''): Promise<{ plan_id: number; status: string }> {
  const res = await api.post(`/recovery/${planId}/reject`, { notes });
  return res.data;
}

export async function listRecoveryPlans(): Promise<RecoveryPlan[]> {
  const res = await api.get('/recovery/');
  return res.data;
}

// ── Monitoring ───────────────────────────────────────────────────────
export interface LinkTelemetry {
  link_id: string;
  source: string;
  target: string;
  timestamp: number;
  throughput_mbps: number;
  latency_ms: number;
  loss_rate: number;
  jitter_ms: number;
  status: 'OK' | 'DEGRADED' | 'CRITICAL';
}

export interface NetworkAlert {
  alert_id: string;
  link_id: string;
  severity: 'WARNING' | 'CRITICAL';
  metric: string;
  value: number;
  threshold: number;
  message: string;
  timestamp: number;
}

export interface TelemetrySnapshot {
  topology_id: number;
  topology_name: string;
  link_count: number;
  telemetry: LinkTelemetry[];
  alerts: NetworkAlert[];
  alert_count: number;
}

export async function getTopologyTelemetry(
  topologyId: number,
  degradedLinks: string[] = []
): Promise<TelemetrySnapshot> {
  const res = await api.post(`/monitor/${topologyId}/telemetry`, {
    degraded_links: degradedLinks,
  });
  return res.data;
}

// ── WSL2 Emulation ───────────────────────────────────────────────────
export interface EmulationReport {
  success: boolean;
  topology_name: string;
  num_nodes: number;
  num_links: number;
  packet_loss_pct: number;
  duration_ms: number;
  details?: Record<string, unknown>;
}

export async function runWSL2Emulation(
  topologyId: number,
  failedNodes: string[] = []
): Promise<EmulationReport> {
  const res = await api.post('/simulations/emulate-wsl', {
    topology_id: topologyId,
    failed_nodes: failedNodes,
  });
  return res.data;
}

