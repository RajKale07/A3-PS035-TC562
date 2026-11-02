import axios from 'axios';

const API_BASE = '/api/v1';

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
  seed = 42
): Promise<any> => {
  const res = await axios.post(`${API_BASE}/topologies/generate`, {
    name,
    num_nodes: numNodes,
    edge_probability: edgeProbability,
    seed,
  });
  return res.data;
};

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

export const optimizePaths = async (
  topologyId: number,
  source: string,
  target: string,
  maxRisk = 5.0,
  maxPaths = 3
): Promise<OptimizationResponse> => {
  const res = await axios.post(`${API_BASE}/optimizer/paths`, {
    topology_id: topologyId,
    source,
    target,
    max_risk: maxRisk,
    max_paths: maxPaths,
  });
  return res.data;
};
