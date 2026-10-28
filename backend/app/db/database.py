import sqlite3
import json
import uuid
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.app.core.config import settings

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS backends (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        base_url TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS models (
        id TEXT PRIMARY KEY,
        backend_id TEXT NOT NULL,
        name TEXT NOT NULL,
        identifier TEXT NOT NULL,
        size_bytes INTEGER DEFAULT 0,
        parameter_count TEXT DEFAULT 'Unknown',
        quantization TEXT DEFAULT 'Unknown',
        context_length INTEGER DEFAULT 0,
        last_seen TEXT NOT NULL,
        FOREIGN KEY (backend_id) REFERENCES backends(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS datasets (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        category TEXT NOT NULL,
        is_builtin INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS dataset_cases (
        id TEXT PRIMARY KEY,
        dataset_id TEXT NOT NULL,
        case_id TEXT NOT NULL,
        category TEXT NOT NULL,
        prompt TEXT NOT NULL,
        expected_output TEXT,
        evaluation_type TEXT DEFAULT 'none',
        criteria_json TEXT,
        language TEXT DEFAULT 'en',
        max_tokens INTEGER DEFAULT 256,
        is_enabled INTEGER DEFAULT 1,
        FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS benchmark_runs (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        status TEXT NOT NULL, -- pending, running, completed, failed, cancelled
        config_json TEXT NOT NULL,
        total_requests INTEGER DEFAULT 0,
        completed_requests INTEGER DEFAULT 0,
        error_count INTEGER DEFAULT 0,
        started_at TEXT NOT NULL,
        completed_at TEXT
    );

    CREATE TABLE IF NOT EXISTS benchmark_iterations (
        id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        case_id TEXT,
        model_id TEXT NOT NULL,
        prompt_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        ttft_ms REAL DEFAULT 0.0,
        latency_ms REAL DEFAULT 0.0,
        tokens_per_sec REAL DEFAULT 0.0,
        response_text TEXT,
        is_warmup INTEGER DEFAULT 0,
        status TEXT NOT NULL, -- success, failed, timeout
        error_message TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (run_id) REFERENCES benchmark_runs(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS benchmark_metrics (
        id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        model_id TEXT NOT NULL,
        successful_iterations INTEGER DEFAULT 0,
        failed_iterations INTEGER DEFAULT 0,
        mean_tps REAL DEFAULT 0.0,
        median_tps REAL DEFAULT 0.0,
        min_tps REAL DEFAULT 0.0,
        max_tps REAL DEFAULT 0.0,
        p90_tps REAL DEFAULT 0.0,
        p95_tps REAL DEFAULT 0.0,
        std_dev_tps REAL DEFAULT 0.0,
        mean_ttft_ms REAL DEFAULT 0.0,
        median_ttft_ms REAL DEFAULT 0.0,
        p90_ttft_ms REAL DEFAULT 0.0,
        p95_ttft_ms REAL DEFAULT 0.0,
        mean_latency_ms REAL DEFAULT 0.0,
        median_latency_ms REAL DEFAULT 0.0,
        p90_latency_ms REAL DEFAULT 0.0,
        error_rate REAL DEFAULT 0.0,
        mean_cpu_percent REAL DEFAULT 0.0,
        peak_memory_mb REAL DEFAULT 0.0,
        average_quality_score REAL DEFAULT 0.0,
        FOREIGN KEY (run_id) REFERENCES benchmark_runs(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS evaluation_results (
        id TEXT PRIMARY KEY,
        iteration_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        evaluator_name TEXT NOT NULL,
        score REAL NOT NULL,
        passed INTEGER DEFAULT 0,
        explanation TEXT,
        FOREIGN KEY (iteration_id) REFERENCES benchmark_iterations(id) ON DELETE CASCADE,
        FOREIGN KEY (run_id) REFERENCES benchmark_runs(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS system_samples (
        id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        cpu_percent REAL NOT NULL,
        memory_used_mb REAL NOT NULL,
        memory_percent REAL NOT NULL,
        process_memory_mb REAL NOT NULL,
        gpu_percent REAL DEFAULT 0.0,
        gpu_memory_mb REAL DEFAULT 0.0,
        FOREIGN KEY (run_id) REFERENCES benchmark_runs(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_iterations_run_id ON benchmark_iterations(run_id);
    CREATE INDEX IF NOT EXISTS idx_metrics_run_id ON benchmark_metrics(run_id);
    CREATE INDEX IF NOT EXISTS idx_eval_iteration_id ON evaluation_results(iteration_id);
    CREATE INDEX IF NOT EXISTS idx_system_samples_run_id ON system_samples(run_id);
    """)
    conn.commit()

    # Seed Default Backends
    cursor.execute("SELECT COUNT(*) as count FROM backends")
    if cursor.fetchone()["count"] == 0:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        backends = [
            ("backend_ollama", "Ollama Local Daemon", "ollama", settings.ollama_base_url, 1, now),
            ("backend_llama_cpp", "llama.cpp Server", "llama_cpp", settings.llama_cpp_base_url, 1, now),
            ("backend_fake", "ModelBench Simulated Runner (Test Only)", "fake", "http://127.0.0.1:0/fake", 1, now),
        ]
        cursor.executemany("INSERT INTO backends VALUES (?, ?, ?, ?, ?, ?)", backends)
        conn.commit()

    # Seed Built-in Datasets
    cursor.execute("SELECT COUNT(*) as count FROM datasets WHERE is_builtin = 1")
    if cursor.fetchone()["count"] == 0:
        seed_builtin_datasets(cursor)
        conn.commit()

    conn.close()

def seed_builtin_datasets(cursor: sqlite3.Cursor):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    datasets = [
        ("ds_general", "General Knowledge Benchmark", "Standard factual recall and foundational knowledge questions.", "General Knowledge", 1, now),
        ("ds_reasoning", "Logical Reasoning & Math", "Multi-step logical deductions, mathematical problem-solving, and syllogisms.", "Reasoning", 1, now),
        ("ds_instruction", "Instruction Following", "Complex constraints, strict format adherence, and negative constraints.", "Instruction Following", 1, now),
        ("ds_summarization", "Text Summarization", "Condensing paragraphs into concise bullets and single-sentence summaries.", "Summarization", 1, now),
        ("ds_coding", "Coding & Syntax Generation", "Algorithmic challenges, code refactoring, and bug detection in Python & JS.", "Coding", 1, now),
        ("ds_structured", "Structured JSON Schema Output", "Strict JSON generation conforming to deterministic JSON Schema specifications.", "Structured Output", 1, now),
        ("ds_indonesian", "Indonesian Language & Culture", "Evaluasi pemahaman bahasa Indonesia baku, konteks budaya, dan tata bahasa.", "Indonesian Language", 1, now),
        ("ds_english", "English Linguistic Nuance", "Idiomatic expressions, stylistic adaptation, and grammatical corrections.", "English Language", 1, now),
    ]
    cursor.executemany("INSERT INTO datasets VALUES (?, ?, ?, ?, ?, ?)", datasets)

    cases = [
        # General Knowledge
        ("case_gk_1", "ds_general", "GK-01", "General Knowledge", "What is the capital city of France? Answer with only the city name.", "Paris", "exact_match", None, "en", 16, 1),
        ("case_gk_2", "ds_general", "GK-02", "General Knowledge", "What chemical element has the atomic number 6? Answer with the chemical element name only.", "Carbon", "normalized_match", None, "en", 16, 1),
        # Reasoning
        ("case_rs_1", "ds_reasoning", "RS-01", "Reasoning", "If all roses are flowers and some flowers fade quickly, does it follow that some roses fade quickly? Answer directly with 'Yes', 'No', or 'Not necessarily' followed by a one-sentence explanation.", "Not necessarily", "rubric", json.dumps({"required_keywords": ["Not necessarily"]}), "en", 64, 1),
        ("case_rs_2", "ds_reasoning", "RS-02", "Reasoning", "Calculate 15% of 240. Show the final numeric result clearly.", "36", "normalized_match", None, "en", 32, 1),
        # Instruction Following
        ("case_if_1", "ds_instruction", "IF-01", "Instruction Following", "List exactly 3 prime numbers between 20 and 40 in ascending order separated by commas. Do not include any other words.", "23, 29, 31", "rubric", json.dumps({"required_keywords": ["23", "29", "31"]}), "en", 32, 1),
        # Summarization
        ("case_sm_1", "ds_summarization", "SM-01", "Summarization", "Summarize in under 15 words: 'Machine learning is a subset of artificial intelligence that involves training computer models on empirical data so they can learn patterns and make predictions without being explicitly programmed.'", None, "rubric", json.dumps({"max_word_count": 20, "required_keywords": ["machine learning"]}), "en", 64, 1),
        # Coding
        ("case_cd_1", "ds_coding", "CD-01", "Coding", "Write a Python one-liner function named `is_even` that returns True if integer `n` is even, else False.", "def is_even(n): return n % 2 == 0", "rubric", json.dumps({"required_keywords": ["is_even", "% 2"]}), "en", 64, 1),
        # Structured Output
        ("case_st_1", "ds_structured", "ST-01", "Structured Output", "Output valid JSON with keys: name (string), age (number), and skills (array of strings) for an AI engineer.", '{"name": "Alice", "age": 28, "skills": ["Python", "FastAPI"]}', "structured_output", json.dumps({"schema": {"type": "object", "required": ["name", "age", "skills"]}}), "en", 128, 1),
        # Indonesian Language
        ("case_id_1", "ds_indonesian", "ID-01", "Indonesian Language", "Sebutkan nama ibu kota baru Negara Kesatuan Republik Indonesia (IKN) di Kalimantan Timur! Jawab hanya dengan nama kotanya.", "Nusantara", "normalized_match", None, "id", 16, 1),
        ("case_id_2", "ds_indonesian", "ID-02", "Indonesian Language", "Tuliskan peribahasa Indonesia yang memiliki arti: 'Sedikit demi sedikit, lama-lama menjadi bukit'.", "Sedikit demi sedikit lama-lama menjadi bukit", "rubric", json.dumps({"required_keywords": ["bukit"]}), "id", 32, 1),
        # English Language
        ("case_en_1", "ds_english", "EN-01", "English Language", "Provide the superlative form of the adjective 'good'. Answer with the single word only.", "best", "normalized_match", None, "en", 16, 1),
    ]
    cursor.executemany("INSERT INTO dataset_cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", cases)
