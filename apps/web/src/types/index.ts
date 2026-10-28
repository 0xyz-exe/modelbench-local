export interface Backend {
  id: string;
  name: string;
  type: string;
  base_url: string;
  is_active: number;
  created_at: string;
}

export interface Model {
  id: string;
  backend_id: string;
  name: string;
  identifier: string;
  size_bytes: number;
  parameter_count: string;
  quantization: string;
  context_length: number;
  last_seen: string;
  backend_name?: string;
  backend_type?: string;
}

export interface Dataset {
  id: string;
  name: string;
  description: string;
  category: string;
  is_builtin: number;
  case_count: number;
  created_at: string;
}

export interface DatasetCase {
  id: string;
  dataset_id: string;
  case_id: string;
  category: string;
  prompt: string;
  expected_output: string | null;
  evaluation_type: string;
  criteria_json: string | null;
  language: string;
  max_tokens: number;
}

export interface BenchmarkRun {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  config_json: string;
  total_requests: number;
  completed_requests: number;
  error_count: number;
  started_at: string;
  completed_at: string | null;
  best_tps?: number;
  avg_quality?: number;
}

export interface BenchmarkMetric {
  id: string;
  run_id: string;
  model_id: string;
  model_name?: string;
  model_identifier?: string;
  quantization?: string;
  parameter_count?: string;
  run_name?: string;
  successful_iterations: number;
  failed_iterations: number;
  mean_tps: number;
  median_tps: number;
  min_tps: number;
  max_tps: number;
  p90_tps: number;
  p95_tps: number;
  std_dev_tps: number;
  mean_ttft_ms: number;
  median_ttft_ms: number;
  p90_ttft_ms: number;
  p95_ttft_ms: number;
  mean_latency_ms: number;
  median_latency_ms: number;
  p90_latency_ms: number;
  error_rate: number;
  mean_cpu_percent: number;
  peak_memory_mb: number;
  average_quality_score: number;
}

export interface BenchmarkIteration {
  id: string;
  run_id: string;
  case_id: string;
  model_id: string;
  model_name?: string;
  prompt?: string;
  category?: string;
  prompt_tokens: number;
  output_tokens: number;
  ttft_ms: number;
  latency_ms: number;
  tokens_per_sec: number;
  response_text: string;
  status: string;
  error_message: string | null;
  created_at: string;
}

export interface SystemInfo {
  os: string;
  os_release: string;
  architecture: string;
  processor: string;
  cpu_count_physical: number;
  cpu_count_logical: number;
  total_ram_gb: number;
  python_version: string;
  gpu_available: boolean;
  gpu_name?: string | null;
  gpu_total_memory_mb?: number;
}

export interface SystemMetrics {
  timestamp: string;
  cpu_percent: number;
  memory_used_mb: number;
  memory_percent: number;
  memory_available_mb: number;
  process_memory_mb: number;
  gpu_percent: number;
  gpu_memory_mb: number;
  gpu_available: boolean;
}
