import { Backend, Model, Dataset, DatasetCase, BenchmarkRun, BenchmarkMetric, SystemInfo, SystemMetrics } from '../types';

const API_BASE = '/api';

export const api = {
  getHealth: async () => {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
  },
  getSystemInfo: async (): Promise<SystemInfo> => {
    const res = await fetch(`${API_BASE}/system/info`);
    return res.json();
  },
  getSystemMetrics: async (): Promise<SystemMetrics> => {
    const res = await fetch(`${API_BASE}/system/metrics`);
    return res.json();
  },
  getBackends: async (): Promise<Backend[]> => {
    const res = await fetch(`${API_BASE}/backends`);
    return res.json();
  },
  getBackendHealth: async (id: string) => {
    const res = await fetch(`${API_BASE}/backends/${id}/health`);
    return res.json();
  },
  getModels: async (): Promise<Model[]> => {
    const res = await fetch(`${API_BASE}/models`);
    return res.json();
  },
  refreshModels: async () => {
    const res = await fetch(`${API_BASE}/models/refresh`, { method: 'POST' });
    return res.json();
  },
  getDatasets: async (): Promise<Dataset[]> => {
    const res = await fetch(`${API_BASE}/datasets`);
    return res.json();
  },
  getDatasetDetails: async (id: string): Promise<{ dataset: Dataset; cases: DatasetCase[] }> => {
    const res = await fetch(`${API_BASE}/datasets/${id}`);
    return res.json();
  },
  createDataset: async (data: { name: string; description: string; category: string }) => {
    const res = await fetch(`${API_BASE}/datasets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return res.json();
  },
  getBenchmarks: async (): Promise<BenchmarkRun[]> => {
    const res = await fetch(`${API_BASE}/benchmarks`);
    return res.json();
  },
  getBenchmarkDetails: async (id: string) => {
    const res = await fetch(`${API_BASE}/benchmarks/${id}`);
    return res.json();
  },
  createBenchmark: async (payload: any) => {
    const res = await fetch(`${API_BASE}/benchmarks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return res.json();
  },
  cancelBenchmark: async (id: string) => {
    const res = await fetch(`${API_BASE}/benchmarks/${id}/cancel`, { method: 'POST' });
    return res.json();
  },
  getComparisons: async (modelIds?: string[]): Promise<BenchmarkMetric[]> => {
    const query = modelIds?.length ? `?model_ids=${modelIds.join(',')}` : '';
    const res = await fetch(`${API_BASE}/comparisons${query}`);
    return res.json();
  },
};
