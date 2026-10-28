# Contributing to ModelBench Local

Thank you for contributing! ModelBench Local welcomes community contributions to improve local LLM benchmarking.

## Development Workflow
1. Fork and clone the repository.
2. Set up the Python virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Set up frontend:
   ```bash
   cd apps/web
   npm install
   npm run dev
   ```
4. Run tests before committing:
   ```bash
   pytest backend/tests
   ```
5. Ensure all code remains local-first with zero tracking or telemetry.
