import React, { useState, useEffect } from 'react';
import {
  Activity,
  Layers,
  Cpu,
  Play,
  BarChart3,
  Database,
  History,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  Zap,
  Shield,
  FileDown,
  Terminal,
  Settings as SettingsIcon,
  HardDrive,
  Info,
  Sliders,
  ChevronRight,
  Server
} from 'lucide-react';
import { api } from './services/api';
import {
  Backend,
  Model,
  Dataset,
  DatasetCase,
  BenchmarkRun,
  BenchmarkMetric,
  SystemInfo,
  SystemMetrics
} from './types';

type Tab = 'overview' | 'models' | 'lab' | 'compare' | 'datasets' | 'history' | 'monitor';

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [backends, setBackends] = useState<Backend[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [runs, setRuns] = useState<BenchmarkRun[]>([]);
  const [metricsComparison, setMetricsComparison] = useState<BenchmarkMetric[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  // Benchmark Lab State
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [selectedDatasets, setSelectedDatasets] = useState<string[]>([]);
  const [preset, setPreset] = useState<'quick' | 'performance' | 'quality' | 'stress' | 'efficiency'>('performance');
  const [warmupIterations, setWarmupIterations] = useState<number>(1);
  const [measuredIterations, setMeasuredIterations] = useState<number>(2);
  const [concurrency, setConcurrency] = useState<number>(1);
  const [maxTokens, setMaxTokens] = useState<number>(128);
  const [temperature, setTemperature] = useState<number>(0.7);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [runProgress, setRunProgress] = useState<{ completed: number; total: number; status: string; currentTps?: number } | null>(null);

  // Results History Modal/Detail State
  const [selectedRunDetail, setSelectedRunDetail] = useState<any | null>(null);

  // Selected Dataset inspection
  const [inspectedDataset, setInspectedDataset] = useState<{ dataset: Dataset; cases: DatasetCase[] } | null>(null);

  const loadData = async () => {
    try {
      const [sysInfo, sysMetrics, bList, mList, dList, rList, cList] = await Promise.all([
        api.getSystemInfo(),
        api.getSystemMetrics(),
        api.getBackends(),
        api.getModels(),
        api.getDatasets(),
        api.getBenchmarks(),
        api.getComparisons(),
      ]);
      setSystemInfo(sysInfo);
      setSystemMetrics(sysMetrics);
      setBackends(bList);
      setModels(mList);
      setDatasets(dList);
      setRuns(rList);
      setMetricsComparison(cList);

      // Preselect default models & datasets if available
      if (mList.length > 0 && selectedModels.length === 0) {
        setSelectedModels([mList[0].id]);
      }
      if (dList.length > 0 && selectedDatasets.length === 0) {
        setSelectedDatasets([dList[0].id]);
      }
    } catch (err) {
      console.error('Failed to load ModelBench Local data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(async () => {
      try {
        const m = await api.getSystemMetrics();
        setSystemMetrics(m);
      } catch (e) {}
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleRefreshModels = async () => {
    setRefreshing(true);
    try {
      await api.refreshModels();
      await loadData();
    } finally {
      setRefreshing(false);
    }
  };

  const handlePresetSelect = (p: 'quick' | 'performance' | 'quality' | 'stress' | 'efficiency') => {
    setPreset(p);
    if (p === 'quick') {
      setWarmupIterations(0);
      setMeasuredIterations(1);
      setMaxTokens(64);
      setConcurrency(1);
    } else if (p === 'performance') {
      setWarmupIterations(1);
      setMeasuredIterations(3);
      setMaxTokens(256);
      setConcurrency(1);
    } else if (p === 'quality') {
      setWarmupIterations(1);
      setMeasuredIterations(2);
      setMaxTokens(384);
      setConcurrency(1);
    } else if (p === 'stress') {
      setWarmupIterations(1);
      setMeasuredIterations(5);
      setMaxTokens(128);
      setConcurrency(2);
    } else if (p === 'efficiency') {
      setWarmupIterations(1);
      setMeasuredIterations(2);
      setMaxTokens(256);
      setConcurrency(1);
    }
  };

  const handleStartBenchmark = async () => {
    if (selectedModels.length === 0 || selectedDatasets.length === 0) {
      alert('Please select at least one model and one dataset.');
      return;
    }

    const payload = {
      name: `${preset.toUpperCase()} Run (${selectedModels.length} models, ${selectedDatasets.length} datasets)`,
      model_ids: selectedModels,
      dataset_ids: selectedDatasets,
      warmup_iterations: warmupIterations,
      measured_iterations: measuredIterations,
      concurrency: concurrency,
      max_tokens: maxTokens,
      temperature: temperature,
      seed: 42,
      timeout_seconds: 45.0,
    };

    try {
      const res = await api.createBenchmark(payload);
      setActiveRunId(res.run_id);
      setRunProgress({ completed: 0, total: 10, status: 'running' });

      // Start SSE Progress Listener
      const evtSource = new EventSource(`/api/benchmarks/${res.run_id}/stream`);
      evtSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'progress') {
            setRunProgress({
              completed: data.completed,
              total: data.total,
              status: 'running',
              currentTps: data.tps,
            });
          } else if (data.type === 'completed' || data.type === 'cancelled' || data.type === 'failed') {
            evtSource.close();
            setRunProgress((prev) => prev ? { ...prev, status: data.type } : null);
            loadData();
          }
        } catch (e) {
          console.error(e);
        }
      };
      evtSource.onerror = () => {
        evtSource.close();
        loadData();
      };
    } catch (e) {
      alert('Failed to launch benchmark: ' + String(e));
    }
  };

  const handleCancelBenchmark = async () => {
    if (activeRunId) {
      await api.cancelBenchmark(activeRunId);
      setRunProgress((prev) => prev ? { ...prev, status: 'cancelled' } : null);
    }
  };

  const handleInspectRun = async (id: string) => {
    const details = await api.getBenchmarkDetails(id);
    setSelectedRunDetail(details);
  };

  const handleInspectDataset = async (id: string) => {
    const data = await api.getDatasetDetails(id);
    setInspectedDataset(data);
  };

  // Aggregated Overview Metrics
  const totalModels = models.length;
  const completedRuns = runs.filter((r) => r.status === 'completed').length;
  const allTps = metricsComparison.map((m) => m.mean_tps).filter((v) => v > 0);
  const avgSystemTps = allTps.length ? (allTps.reduce((a, b) => a + b, 0) / allTps.length).toFixed(1) : '0.0';
  const bestTps = allTps.length ? Math.max(...allTps).toFixed(1) : '0.0';
  const allQuality = metricsComparison.map((m) => m.average_quality_score).filter((v) => v > 0);
  const avgQuality = allQuality.length ? (allQuality.reduce((a, b) => a + b, 0) / allQuality.length).toFixed(2) : '0.00';

  return (
    <div className="flex h-screen w-full bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-64 flex flex-col border-r border-slate-800 bg-slate-900/50 backdrop-blur-md select-none shrink-0">
        <div className="p-5 border-b border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-sm tracking-wide text-white">ModelBench</h1>
              <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800">
                LOCAL v1.0
              </span>
            </div>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1 flex-1 overflow-y-auto">
          <button
            onClick={() => setActiveTab('overview')}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'overview'
                ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Activity className="h-4 w-4" />
            Overview
          </button>

          <button
            onClick={() => setActiveTab('models')}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'models'
                ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Layers className="h-4 w-4" />
            Models
            <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
              {models.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('lab')}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'lab'
                ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Play className="h-4 w-4" />
            Benchmark Lab
          </button>

          <button
            onClick={() => setActiveTab('compare')}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'compare'
                ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <BarChart3 className="h-4 w-4" />
            Compare Models
          </button>

          <button
            onClick={() => setActiveTab('datasets')}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'datasets'
                ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Database className="h-4 w-4" />
            Datasets
            <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
              {datasets.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('history')}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'history'
                ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <History className="h-4 w-4" />
            Results History
            <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
              {runs.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('monitor')}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'monitor'
                ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Cpu className="h-4 w-4" />
            System Monitor
          </button>
        </nav>

        {/* Runtime Status Pill */}
        <div className="p-3 m-3 rounded-lg bg-slate-900 border border-slate-800 text-xs">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-slate-400 text-[11px] font-medium flex items-center gap-1.5">
              <Shield className="h-3 w-3 text-emerald-400" />
              Local Privacy Mode
            </span>
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Zero cloud telemetry. Pure loopback execution.
          </p>
        </div>
      </aside>

      {/* Main Content Pane */}
      <main className="flex-1 flex flex-col overflow-hidden bg-slate-950">
        {/* Top Header */}
        <header className="h-14 border-b border-slate-800 px-6 flex items-center justify-between shrink-0 bg-slate-900/30">
          <div className="flex items-center gap-3">
            <span className="text-xs uppercase font-mono tracking-wider text-slate-400">
              {activeTab.replace('_', ' ')}
            </span>
            <span className="text-slate-600">/</span>
            <span className="text-xs text-slate-200 font-medium">
              {activeTab === 'overview' && 'System Benchmarking Telemetry & Operations'}
              {activeTab === 'models' && 'Discovered Local AI Models & Inference Runtimes'}
              {activeTab === 'lab' && 'Interactive Execution Suite & Presets'}
              {activeTab === 'compare' && 'Multi-Model Comparative Matrix & Scatter Plots'}
              {activeTab === 'datasets' && 'Curated Benchmark Categories & Test Cases'}
              {activeTab === 'history' && 'Audit Trail, Iteration Traces & Report Export'}
              {activeTab === 'monitor' && 'Hardware Resource Sampling (CPU, RAM, GPU)'}
            </span>
          </div>

          {/* Quick Hardware Info & Refresh */}
          <div className="flex items-center gap-4">
            {systemMetrics && (
              <div className="flex items-center gap-4 text-xs font-mono">
                <span className="flex items-center gap-1.5 text-slate-300">
                  <Cpu className="h-3.5 w-3.5 text-sky-400" />
                  {systemMetrics.cpu_percent}% CPU
                </span>
                <span className="flex items-center gap-1.5 text-slate-300">
                  <HardDrive className="h-3.5 w-3.5 text-indigo-400" />
                  {Math.round(systemMetrics.memory_used_mb / 1024)}GB RAM ({systemMetrics.memory_percent}%)
                </span>
              </div>
            )}
            <button
              onClick={handleRefreshModels}
              disabled={refreshing}
              className="p-1.5 rounded-lg border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-all text-xs flex items-center gap-1.5"
              title="Refresh Local Models and Runtimes"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin text-sky-400' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </header>

        {/* Body Viewport */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* TAB 1: OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-6 max-w-7xl mx-auto">
              {/* Stat Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-sm">
                  <div className="flex items-center justify-between text-slate-400 mb-2">
                    <span className="text-xs font-medium uppercase tracking-wider">Registered Models</span>
                    <Layers className="h-4 w-4 text-sky-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-white">{totalModels}</div>
                  <p className="text-[11px] text-slate-400 mt-1">Available on local adapters</p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-sm">
                  <div className="flex items-center justify-between text-slate-400 mb-2">
                    <span className="text-xs font-medium uppercase tracking-wider">Benchmark Runs</span>
                    <History className="h-4 w-4 text-emerald-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-white">{completedRuns}</div>
                  <p className="text-[11px] text-slate-400 mt-1">Completed benchmark sessions</p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-sm">
                  <div className="flex items-center justify-between text-slate-400 mb-2">
                    <span className="text-xs font-medium uppercase tracking-wider">Peak Throughput</span>
                    <Zap className="h-4 w-4 text-amber-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-sky-400">{bestTps} <span className="text-xs font-normal text-slate-400">tok/s</span></div>
                  <p className="text-[11px] text-slate-400 mt-1">Avg observed: {avgSystemTps} tok/s</p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-sm">
                  <div className="flex items-center justify-between text-slate-400 mb-2">
                    <span className="text-xs font-medium uppercase tracking-wider">Quality Score</span>
                    <CheckCircle2 className="h-4 w-4 text-indigo-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-indigo-400">{avgQuality} <span className="text-xs font-normal text-slate-400">/ 1.0</span></div>
                  <p className="text-[11px] text-slate-400 mt-1">Deterministic schema & rubric pass</p>
                </div>
              </div>

              {/* Runtimes & Recent Telemetry */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Backends Card */}
                <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800">
                  <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                    <Server className="h-4 w-4 text-sky-400" />
                    Inference Runtime Status
                  </h3>
                  <div className="space-y-3">
                    {backends.map((b) => (
                      <div key={b.id} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between">
                        <div>
                          <div className="text-xs font-medium text-slate-200">{b.name}</div>
                          <div className="text-[11px] font-mono text-slate-400 truncate max-w-[180px]">{b.base_url}</div>
                        </div>
                        <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                          ONLINE
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* System Specs Card */}
                <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 lg:col-span-2">
                  <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                    <Cpu className="h-4 w-4 text-indigo-400" />
                    Host Hardware Environment
                  </h3>
                  {systemInfo && (
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs font-mono">
                      <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800/60">
                        <span className="text-slate-400 block text-[10px] uppercase">OS Platform</span>
                        <span className="text-slate-200 font-semibold">{systemInfo.os} {systemInfo.architecture}</span>
                      </div>
                      <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800/60">
                        <span className="text-slate-400 block text-[10px] uppercase">CPU Cores</span>
                        <span className="text-slate-200 font-semibold">{systemInfo.cpu_count_logical} Logical ({systemInfo.cpu_count_physical} Phys)</span>
                      </div>
                      <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800/60">
                        <span className="text-slate-400 block text-[10px] uppercase">Total System RAM</span>
                        <span className="text-slate-200 font-semibold">{systemInfo.total_ram_gb} GB</span>
                      </div>
                      <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800/60">
                        <span className="text-slate-400 block text-[10px] uppercase">Processor</span>
                        <span className="text-slate-200 font-semibold truncate block" title={systemInfo.processor}>{systemInfo.processor}</span>
                      </div>
                      <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800/60">
                        <span className="text-slate-400 block text-[10px] uppercase">Python Runtime</span>
                        <span className="text-slate-200 font-semibold">Python {systemInfo.python_version}</span>
                      </div>
                      <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800/60">
                        <span className="text-slate-400 block text-[10px] uppercase">GPU Acceleration</span>
                        <span className={systemInfo.gpu_available ? "text-emerald-400 font-semibold" : "text-slate-400"}>
                          {systemInfo.gpu_available ? systemInfo.gpu_name : 'CPU Only (Graceful)'}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Recent Runs Table */}
              <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <History className="h-4 w-4 text-sky-400" />
                    Recent Benchmark Runs
                  </h3>
                  <button
                    onClick={() => setActiveTab('history')}
                    className="text-xs text-sky-400 hover:text-sky-300 font-medium"
                  >
                    View All &rarr;
                  </button>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-950/60 text-slate-400 uppercase text-[10px] border-b border-slate-800">
                      <tr>
                        <th className="py-2.5 px-3">Session Name</th>
                        <th className="py-2.5 px-3">Status</th>
                        <th className="py-2.5 px-3">Completed</th>
                        <th className="py-2.5 px-3">Peak TPS</th>
                        <th className="py-2.5 px-3">Avg Quality</th>
                        <th className="py-2.5 px-3">Started</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {runs.slice(0, 5).map((r) => (
                        <tr key={r.id} className="hover:bg-slate-800/30 transition-colors">
                          <td className="py-2.5 px-3 font-semibold text-slate-200">{r.name}</td>
                          <td className="py-2.5 px-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                              r.status === 'completed'
                                ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                                : r.status === 'running'
                                ? 'bg-sky-950 text-sky-400 border border-sky-800 animate-pulse'
                                : 'bg-rose-950 text-rose-400 border border-rose-800'
                            }`}>
                              {r.status.toUpperCase()}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-slate-400">{r.completed_requests} / {r.total_requests}</td>
                          <td className="py-2.5 px-3 text-sky-400 font-bold">{r.best_tps || '0.0'}</td>
                          <td className="py-2.5 px-3 text-indigo-400 font-bold">{r.avg_quality || '0.00'}</td>
                          <td className="py-2.5 px-3 text-slate-400">{r.started_at.slice(0, 19).replace('T', ' ')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: MODELS */}
          {activeTab === 'models' && (
            <div className="space-y-6 max-w-7xl mx-auto">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-white">Discovered Local Models</h2>
                  <p className="text-xs text-slate-400">Models registered across local Ollama, llama.cpp, and testing adapters.</p>
                </div>
                <button
                  onClick={handleRefreshModels}
                  disabled={refreshing}
                  className="px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium flex items-center gap-1.5 transition-all shadow-md"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
                  Sync Runtime Models
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {models.map((m) => (
                  <div key={m.id} className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition-all shadow-sm">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h4 className="text-sm font-semibold text-white leading-snug">{m.name}</h4>
                        <span className="text-[11px] font-mono text-slate-400">{m.identifier}</span>
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-sky-300 border border-slate-700">
                        {m.backend_name || m.backend_id}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs font-mono my-3 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
                      <div>
                        <span className="text-slate-400 block text-[10px]">Parameters</span>
                        <span className="text-slate-200">{m.parameter_count}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">Quantization</span>
                        <span className="text-slate-200">{m.quantization}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">Context Window</span>
                        <span className="text-slate-200">{m.context_length} tokens</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">Size on Disk</span>
                        <span className="text-slate-200">{m.size_bytes ? `${(m.size_bytes / (1024**3)).toFixed(2)} GB` : 'N/A'}</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-[11px]">
                      <span className="text-slate-400 font-mono text-[10px]">Seen: {m.last_seen.slice(0, 10)}</span>
                      <button
                        onClick={() => {
                          setSelectedModels([m.id]);
                          setActiveTab('lab');
                        }}
                        className="text-sky-400 hover:text-sky-300 font-medium flex items-center gap-1"
                      >
                        Benchmark &rarr;
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 3: BENCHMARK LAB */}
          {activeTab === 'lab' && (
            <div className="space-y-6 max-w-6xl mx-auto">
              <div>
                <h2 className="text-lg font-bold text-white">Benchmark Execution Lab</h2>
                <p className="text-xs text-slate-400">Configure parameters, pick test presets, and monitor live streaming throughput.</p>
              </div>

              {/* Presets Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                {[
                  { id: 'quick', name: 'Quick Smoke', desc: '1 run, 64 tokens' },
                  { id: 'performance', name: 'Performance', desc: '3 runs, throughput' },
                  { id: 'quality', name: 'Quality Test', desc: 'Accuracy & schemas' },
                  { id: 'stress', name: 'Stress Test', desc: 'Concurrency 2, 5 runs' },
                  { id: 'efficiency', name: 'Hardware Eff.', desc: 'RAM vs TPS' },
                ].map((p) => (
                  <button
                    key={p.id}
                    onClick={() => handlePresetSelect(p.id as any)}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      preset === p.id
                        ? 'bg-sky-500/15 border-sky-500 text-sky-300 shadow-md shadow-sky-500/10'
                        : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:bg-slate-800/40'
                    }`}
                  >
                    <div className="text-xs font-bold text-white">{p.name}</div>
                    <div className="text-[10px] text-slate-400 mt-1">{p.desc}</div>
                  </button>
                ))}
              </div>

              {/* Configuration Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Models Selection */}
                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3 flex items-center justify-between">
                    <span>1. Target Models ({selectedModels.length})</span>
                    <button
                      onClick={() => setSelectedModels(models.map((m) => m.id))}
                      className="text-[10px] text-sky-400 hover:underline normal-case"
                    >
                      Select All
                    </button>
                  </h3>
                  <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                    {models.map((m) => {
                      const isSelected = selectedModels.includes(m.id);
                      return (
                        <div
                          key={m.id}
                          onClick={() => {
                            if (isSelected) {
                              setSelectedModels(selectedModels.filter((id) => id !== m.id));
                            } else {
                              setSelectedModels([...selectedModels, m.id]);
                            }
                          }}
                          className={`p-2.5 rounded-lg border text-xs cursor-pointer flex items-center justify-between transition-all ${
                            isSelected
                              ? 'bg-sky-950/60 border-sky-600/80 text-sky-200'
                              : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:bg-slate-800/40'
                          }`}
                        >
                          <div>
                            <span className="font-semibold block">{m.name}</span>
                            <span className="text-[10px] font-mono text-slate-400">{m.identifier} ({m.quantization})</span>
                          </div>
                          <input type="checkbox" checked={isSelected} readOnly className="rounded text-sky-500 pointer-events-none" />
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Datasets Selection */}
                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3 flex items-center justify-between">
                    <span>2. Benchmark Datasets ({selectedDatasets.length})</span>
                    <button
                      onClick={() => setSelectedDatasets(datasets.map((d) => d.id))}
                      className="text-[10px] text-sky-400 hover:underline normal-case"
                    >
                      Select All
                    </button>
                  </h3>
                  <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                    {datasets.map((d) => {
                      const isSelected = selectedDatasets.includes(d.id);
                      return (
                        <div
                          key={d.id}
                          onClick={() => {
                            if (isSelected) {
                              setSelectedDatasets(selectedDatasets.filter((id) => id !== d.id));
                            } else {
                              setSelectedDatasets([...selectedDatasets, d.id]);
                            }
                          }}
                          className={`p-2.5 rounded-lg border text-xs cursor-pointer flex items-center justify-between transition-all ${
                            isSelected
                              ? 'bg-sky-950/60 border-sky-600/80 text-sky-200'
                              : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:bg-slate-800/40'
                          }`}
                        >
                          <div>
                            <span className="font-semibold block">{d.name}</span>
                            <span className="text-[10px] text-slate-400">{d.category} ({d.case_count} cases)</span>
                          </div>
                          <input type="checkbox" checked={isSelected} readOnly className="rounded text-sky-500 pointer-events-none" />
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Execution Sliders */}
              <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
                <div>
                  <label className="text-slate-400 block mb-1">Warmup Iterations</label>
                  <input
                    type="number"
                    min={0}
                    max={5}
                    value={warmupIterations}
                    onChange={(e) => setWarmupIterations(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Measured Runs</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={measuredIterations}
                    onChange={(e) => setMeasuredIterations(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Concurrency Limit</label>
                  <input
                    type="number"
                    min={1}
                    max={4}
                    value={concurrency}
                    onChange={(e) => setConcurrency(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Max Output Tokens</label>
                  <input
                    type="number"
                    min={16}
                    max={1024}
                    step={16}
                    value={maxTokens}
                    onChange={(e) => setMaxTokens(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200"
                  />
                </div>
              </div>

              {/* Action & Live Progress Monitor */}
              <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-4">
                <div className="w-full flex-1">
                  {runProgress ? (
                    <div>
                      <div className="flex items-center justify-between text-xs font-mono mb-2">
                        <span className="text-slate-300 font-semibold flex items-center gap-2">
                          <Activity className="h-4 w-4 text-sky-400 animate-spin" />
                          Status: {runProgress.status.toUpperCase()}
                        </span>
                        <span className="text-sky-400">
                          {runProgress.completed} / {runProgress.total} requests
                          {runProgress.currentTps ? ` (${runProgress.currentTps.toFixed(1)} tok/s)` : ''}
                        </span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-slate-950 border border-slate-800 overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-sky-500 to-indigo-500 transition-all duration-300"
                          style={{
                            width: `${Math.min(100, Math.round((runProgress.completed / Math.max(1, runProgress.total)) * 100))}%`,
                          }}
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-slate-400 leading-relaxed">
                      Estimated requests: <strong className="text-slate-200 font-mono">{selectedModels.length * selectedDatasets.length * (warmupIterations + measuredIterations)}</strong>.
                      Execution remains strictly bounded to local hardware.
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {runProgress && runProgress.status === 'running' ? (
                    <button
                      onClick={handleCancelBenchmark}
                      className="px-4 py-2 rounded-lg bg-rose-600/80 hover:bg-rose-500 text-white text-xs font-medium transition-all"
                    >
                      Abort Run
                    </button>
                  ) : (
                    <button
                      onClick={handleStartBenchmark}
                      className="px-5 py-2.5 rounded-lg bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white text-xs font-bold transition-all shadow-lg shadow-sky-500/20 flex items-center gap-2"
                    >
                      <Play className="h-4 w-4 fill-white" />
                      Execute Benchmark
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: COMPARE MODELS */}
          {activeTab === 'compare' && (
            <div className="space-y-6 max-w-7xl mx-auto">
              <div>
                <h2 className="text-lg font-bold text-white">Model Comparison Matrix</h2>
                <p className="text-xs text-slate-400">Empirical throughput, TTFT, quality score, and memory footprints side-by-side.</p>
              </div>

              {/* Interactive Bar Chart Visualization (SVG) */}
              <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-4 flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-sky-400" />
                  Generation Throughput (Tokens / Second)
                </h3>
                <div className="space-y-3">
                  {metricsComparison.map((m) => {
                    const maxVal = Math.max(...metricsComparison.map((x) => x.mean_tps), 50);
                    const pct = Math.min(100, (m.mean_tps / maxVal) * 100);
                    return (
                      <div key={m.id} className="text-xs font-mono">
                        <div className="flex justify-between text-slate-300 mb-1">
                          <span className="font-semibold">{m.model_name || m.model_id}</span>
                          <span className="text-sky-400 font-bold">{m.mean_tps} tok/s</span>
                        </div>
                        <div className="w-full h-3 rounded-full bg-slate-950 border border-slate-800/80 overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-sky-500 to-indigo-500 rounded-full"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Full Comparison Table */}
              <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3">
                  Benchmark Metrics Table
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] border-b border-slate-800">
                      <tr>
                        <th className="py-2.5 px-3">Model</th>
                        <th className="py-2.5 px-3">Mean TPS</th>
                        <th className="py-2.5 px-3">Median TPS</th>
                        <th className="py-2.5 px-3">P95 TPS</th>
                        <th className="py-2.5 px-3">Mean TTFT</th>
                        <th className="py-2.5 px-3">Mean Latency</th>
                        <th className="py-2.5 px-3">Quality Score</th>
                        <th className="py-2.5 px-3">Error Rate</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {metricsComparison.map((m) => (
                        <tr key={m.id} className="hover:bg-slate-800/20">
                          <td className="py-2.5 px-3 font-semibold text-slate-200">
                            {m.model_name || m.model_id}
                            <span className="block text-[10px] text-slate-400">{m.quantization} • {m.parameter_count}</span>
                          </td>
                          <td className="py-2.5 px-3 text-sky-400 font-bold">{m.mean_tps}</td>
                          <td className="py-2.5 px-3 text-slate-300">{m.median_tps}</td>
                          <td className="py-2.5 px-3 text-slate-300">{m.p95_tps}</td>
                          <td className="py-2.5 px-3 text-indigo-300">{m.mean_ttft_ms} ms</td>
                          <td className="py-2.5 px-3 text-slate-300">{m.mean_latency_ms} ms</td>
                          <td className="py-2.5 px-3 text-emerald-400 font-bold">{m.average_quality_score}</td>
                          <td className="py-2.5 px-3 text-slate-400">{(m.error_rate * 100).toFixed(1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: DATASETS */}
          {activeTab === 'datasets' && (
            <div className="space-y-6 max-w-7xl mx-auto">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-white">Benchmark Datasets</h2>
                  <p className="text-xs text-slate-400">Built-in test suites covering 8 categories with deterministic verification.</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {datasets.map((d) => (
                  <div
                    key={d.id}
                    onClick={() => handleInspectDataset(d.id)}
                    className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-sky-500/50 cursor-pointer transition-all shadow-sm"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800">
                        {d.category}
                      </span>
                      <span className="text-xs font-mono text-slate-400">{d.case_count} cases</span>
                    </div>
                    <h4 className="text-sm font-semibold text-white mt-1">{d.name}</h4>
                    <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">{d.description}</p>
                    <div className="mt-4 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-sky-400 font-medium">
                      <span>Inspect Cases &rarr;</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Test Cases Viewer Modal */}
              {inspectedDataset && (
                <div className="p-5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-white">{inspectedDataset.dataset.name}</h3>
                      <p className="text-xs text-slate-400">Category: {inspectedDataset.dataset.category}</p>
                    </div>
                    <button
                      onClick={() => setInspectedDataset(null)}
                      className="text-xs px-2.5 py-1 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
                    >
                      Close
                    </button>
                  </div>
                  <div className="space-y-3">
                    {inspectedDataset.cases.map((c) => (
                      <div key={c.id} className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono space-y-1.5">
                        <div className="flex justify-between text-slate-400 text-[10px]">
                          <span>CASE ID: {c.case_id}</span>
                          <span>EVAL TYPE: {c.evaluation_type}</span>
                        </div>
                        <div className="text-slate-200"><strong className="text-sky-400">Prompt:</strong> {c.prompt}</div>
                        {c.expected_output && (
                          <div className="text-slate-400"><strong className="text-emerald-400">Expected:</strong> {c.expected_output}</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 6: RESULTS HISTORY */}
          {activeTab === 'history' && (
            <div className="space-y-6 max-w-7xl mx-auto">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-white">Results History & Reports</h2>
                  <p className="text-xs text-slate-400">Trace historical runs, inspect per-prompt outputs, and export reports in 4 formats.</p>
                </div>
              </div>

              <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] border-b border-slate-800">
                      <tr>
                        <th className="py-2.5 px-3">Run ID</th>
                        <th className="py-2.5 px-3">Session Name</th>
                        <th className="py-2.5 px-3">Status</th>
                        <th className="py-2.5 px-3">Completed</th>
                        <th className="py-2.5 px-3">Peak TPS</th>
                        <th className="py-2.5 px-3">Export</th>
                        <th className="py-2.5 px-3">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {runs.map((r) => (
                        <tr key={r.id} className="hover:bg-slate-800/20">
                          <td className="py-2.5 px-3 text-slate-400">{r.id}</td>
                          <td className="py-2.5 px-3 font-semibold text-slate-200">{r.name}</td>
                          <td className="py-2.5 px-3">
                            <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300">
                              {r.status.toUpperCase()}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-slate-400">{r.completed_requests} / {r.total_requests}</td>
                          <td className="py-2.5 px-3 text-sky-400 font-bold">{r.best_tps || '0.0'}</td>
                          <td className="py-2.5 px-3">
                            <div className="flex items-center gap-1.5">
                              <a
                                href={`/api/reports/${r.id}/export?format=html`}
                                target="_blank"
                                rel="noreferrer"
                                className="px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-sky-400 text-[10px]"
                              >
                                HTML
                              </a>
                              <a
                                href={`/api/reports/${r.id}/export?format=csv`}
                                download
                                className="px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-emerald-400 text-[10px]"
                              >
                                CSV
                              </a>
                              <a
                                href={`/api/reports/${r.id}/export?format=md`}
                                download
                                className="px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-amber-400 text-[10px]"
                              >
                                MD
                              </a>
                              <a
                                href={`/api/reports/${r.id}/export?format=json`}
                                download
                                className="px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-indigo-400 text-[10px]"
                              >
                                JSON
                              </a>
                            </div>
                          </td>
                          <td className="py-2.5 px-3">
                            <button
                              onClick={() => handleInspectRun(r.id)}
                              className="text-sky-400 hover:underline"
                            >
                              Inspect &rarr;
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Run Details Modal / Drawer */}
              {selectedRunDetail && (
                <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-white">{selectedRunDetail.run.name}</h3>
                      <span className="text-xs font-mono text-slate-400">Run ID: {selectedRunDetail.run.id}</span>
                    </div>
                    <button
                      onClick={() => setSelectedRunDetail(null)}
                      className="text-xs px-2.5 py-1 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
                    >
                      Close
                    </button>
                  </div>

                  <h4 className="text-xs font-bold uppercase text-slate-400 mt-2">Iteration Trace Log</h4>
                  <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                    {selectedRunDetail.iterations.map((it: any) => (
                      <div key={it.id} className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono space-y-1">
                        <div className="flex justify-between text-slate-400 text-[10px]">
                          <span>{it.model_name || it.model_id}</span>
                          <span className="text-sky-400">{it.tokens_per_sec} tok/s • TTFT: {it.ttft_ms}ms • Latency: {it.latency_ms}ms</span>
                        </div>
                        <div className="text-slate-300 font-sans"><strong className="text-sky-400 font-mono">Output:</strong> {it.response_text}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 7: SYSTEM MONITOR */}
          {activeTab === 'monitor' && (
            <div className="space-y-6 max-w-6xl mx-auto">
              <div>
                <h2 className="text-lg font-bold text-white">Hardware & System Telemetry</h2>
                <p className="text-xs text-slate-400">Live non-invasive sampling of local CPU, system RAM, and process RSS.</p>
              </div>

              {systemMetrics && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* CPU Meter */}
                  <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 text-center">
                    <span className="text-xs font-mono uppercase text-slate-400 block mb-2">CPU Utilization</span>
                    <div className="text-4xl font-mono font-bold text-sky-400 my-4">{systemMetrics.cpu_percent}%</div>
                    <div className="w-full h-2 rounded-full bg-slate-950 overflow-hidden">
                      <div className="h-full bg-sky-500 rounded-full" style={{ width: `${Math.min(100, systemMetrics.cpu_percent)}%` }} />
                    </div>
                  </div>

                  {/* RAM Meter */}
                  <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 text-center">
                    <span className="text-xs font-mono uppercase text-slate-400 block mb-2">System Memory</span>
                    <div className="text-4xl font-mono font-bold text-indigo-400 my-4">{systemMetrics.memory_percent}%</div>
                    <p className="text-[11px] font-mono text-slate-400 mb-2">{Math.round(systemMetrics.memory_used_mb / 1024)}GB used / {Math.round(systemMetrics.memory_available_mb / 1024)}GB avail</p>
                    <div className="w-full h-2 rounded-full bg-slate-950 overflow-hidden">
                      <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${Math.min(100, systemMetrics.memory_percent)}%` }} />
                    </div>
                  </div>

                  {/* Process RSS */}
                  <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 text-center">
                    <span className="text-xs font-mono uppercase text-slate-400 block mb-2">ModelBench Process RSS</span>
                    <div className="text-4xl font-mono font-bold text-emerald-400 my-4">{Math.round(systemMetrics.process_memory_mb)} <span className="text-sm">MB</span></div>
                    <p className="text-[11px] text-slate-400 mt-2">Pure local execution overhead</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
