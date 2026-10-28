import json
import csv
import io
from typing import Dict, Any, List
from backend.app.db.database import get_connection

def generate_json_report(run_id: str) -> Dict[str, Any]:
    conn = get_connection()
    run = conn.execute("SELECT * FROM benchmark_runs WHERE id = ?", (run_id,)).fetchone()
    if not run:
        conn.close()
        return {"error": "Run not found"}

    metrics = conn.execute("SELECT * FROM benchmark_metrics WHERE run_id = ?", (run_id,)).fetchall()
    iterations = conn.execute("SELECT * FROM benchmark_iterations WHERE run_id = ? AND is_warmup = 0", (run_id,)).fetchall()
    evaluations = conn.execute("SELECT * FROM evaluation_results WHERE run_id = ?", (run_id,)).fetchall()
    samples = conn.execute("SELECT * FROM system_samples WHERE run_id = ?", (run_id,)).fetchall()

    conn.close()

    return {
        "run": dict(run),
        "config": json.loads(run["config_json"]) if run["config_json"] else {},
        "metrics": [dict(m) for m in metrics],
        "iterations": [dict(it) for it in iterations],
        "evaluations": [dict(ev) for ev in evaluations],
        "system_telemetry": [dict(s) for s in samples],
    }

def generate_csv_report(run_id: str) -> str:
    conn = get_connection()
    iterations = conn.execute("""
        SELECT bi.id, bi.run_id, m.name as model_name, bi.prompt_tokens, bi.output_tokens,
               bi.ttft_ms, bi.latency_ms, bi.tokens_per_sec, bi.status, bi.created_at
        FROM benchmark_iterations bi
        LEFT JOIN models m ON bi.model_id = m.id
        WHERE bi.run_id = ? AND bi.is_warmup = 0
    """, (run_id,)).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "iteration_id", "run_id", "model_name", "prompt_tokens", "output_tokens",
        "ttft_ms", "latency_ms", "tokens_per_sec", "status", "timestamp"
    ])
    for it in iterations:
        writer.writerow([
            it["id"], it["run_id"], it["model_name"], it["prompt_tokens"], it["output_tokens"],
            it["ttft_ms"], it["latency_ms"], it["tokens_per_sec"], it["status"], it["created_at"]
        ])
    return output.getvalue()

def generate_markdown_report(run_id: str) -> str:
    data = generate_json_report(run_id)
    if "error" in data:
        return "# Benchmark Run Not Found"

    run = data["run"]
    metrics = data["metrics"]

    md = []
    md.append(f"# ModelBench Local Report: {run.get('name')}")
    md.append(f"- **Run ID:** `{run.get('id')}`")
    md.append(f"- **Status:** `{run.get('status')}`")
    md.append(f"- **Started At:** {run.get('started_at')}")
    md.append(f"- **Completed At:** {run.get('completed_at') or 'In progress'}")
    md.append(f"- **Total Requests:** {run.get('total_requests')}")
    md.append(f"- **Completed Requests:** {run.get('completed_requests')}")
    md.append(f"- **Errors:** {run.get('error_count')}")
    md.append("\n## Model Performance Summary\n")
    md.append("| Model ID | Mean TPS | Median TPS | P95 TPS | Mean TTFT (ms) | Mean Latency (ms) | Quality Score | Error Rate |")
    md.append("|---|---|---|---|---|---|---|---|")

    for m in metrics:
        md.append(
            f"| `{m['model_id']}` | **{m['mean_tps']}** | {m['median_tps']} | {m['p95_tps']} | "
            f"{m['mean_ttft_ms']} | {m['mean_latency_ms']} | {m['average_quality_score']} | {m['error_rate'] * 100:.1f}% |"
        )

    md.append("\n## Evaluation & Hardware Observations\n")
    md.append("- All benchmarks were executed strictly in a local-first environment with zero cloud telemetry.")
    md.append("- Quality metrics reflect deterministic rubric and schema validations.")

    return "\n".join(md)

def generate_html_report(run_id: str) -> str:
    data = generate_json_report(run_id)
    if "error" in data:
        return "<h1>Benchmark Run Not Found</h1>"

    run = data["run"]
    metrics = data["metrics"]
    rows = ""
    for m in metrics:
        rows += f"""
        <tr>
            <td style="padding:10px;border-bottom:1px solid #334155;font-weight:600;">{m['model_id']}</td>
            <td style="padding:10px;border-bottom:1px solid #334155;color:#38bdf8;font-weight:700;">{m['mean_tps']}</td>
            <td style="padding:10px;border-bottom:1px solid #334155;">{m['median_tps']}</td>
            <td style="padding:10px;border-bottom:1px solid #334155;">{m['p95_tps']}</td>
            <td style="padding:10px;border-bottom:1px solid #334155;">{m['mean_ttft_ms']} ms</td>
            <td style="padding:10px;border-bottom:1px solid #334155;">{m['mean_latency_ms']} ms</td>
            <td style="padding:10px;border-bottom:1px solid #334155;color:#4ade80;">{m['average_quality_score']}</td>
            <td style="padding:10px;border-bottom:1px solid #334155;">{m['error_rate'] * 100:.1f}%</td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ModelBench Local Report - {run.get('name')}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 40px; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
        h1 {{ color: #38bdf8; margin-top: 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background: #0f172a; color: #94a3b8; text-align: left; padding: 12px 10px; font-size: 13px; text-transform: uppercase; }}
        .badge {{ background: #0369a1; color: #e0f2fe; padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600; display: inline-block; }}
        .meta-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 24px 0; background: #0f172a; padding: 16px; border-radius: 8px; }}
        .meta-item {{ font-size: 14px; color: #94a3b8; }}
        .meta-item strong {{ display: block; color: #f8fafc; font-size: 16px; margin-top: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <span class="badge">ModelBench Local Report</span>
        <h1>{run.get('name')}</h1>
        <div class="meta-grid">
            <div class="meta-item">Status<strong>{run.get('status')}</strong></div>
            <div class="meta-item">Total Completed<strong>{run.get('completed_requests')} / {run.get('total_requests')}</strong></div>
            <div class="meta-item">Started<strong>{run.get('started_at')[:19].replace('T', ' ')}</strong></div>
        </div>
        <h2>Model Performance Summary</h2>
        <table>
            <thead>
                <tr>
                    <th>Model</th>
                    <th>Mean TPS</th>
                    <th>Median TPS</th>
                    <th>P95 TPS</th>
                    <th>TTFT</th>
                    <th>Latency</th>
                    <th>Quality</th>
                    <th>Error Rate</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
