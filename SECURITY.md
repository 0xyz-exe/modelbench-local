# Security Policy

## Core Security Posture
ModelBench Local operates completely locally on loopback (`127.0.0.1`) by default.
- No network telemetry is collected.
- Prompts, outputs, and system metrics never leave your computer.
- Model adapters only communicate with localhost or user-specified backend endpoints.

## Reporting a Vulnerability
If you discover a security vulnerability or potential SSRF issue in backend validation, please file a report to `security@0xyz-exe.dev` or open a confidential GitHub Security Advisory.
