# Release
D1–D9 🟢 FROZEN
D10.1 E2E Isolation 🟢 FROZEN
D10.2 Security 🟢 FROZEN
D10.3 Incremental 🟢 FROZEN
D10.4 Performance 🟢 FROZEN
D10.5 Polyglot 🟢 FROZEN (Java/TS/Python VALIDATED, others VALIDATION_PENDING)
D10.6 Golden 🟢 FROZEN (33/33)
D10.7 Production UX 🟢 FROZEN
D10.8 Observability 🟢 FROZEN
D10.9 Documentation 🟢 FROZEN (this docs set)
D10.10 Final Release Gate → run `pytest tests/ -k "not performance" -q && pytest tests/e2e -v && python -m devlensx.evaluation.runner && python -m devlensx.polyglot.matrix && npm --prefix web run build` must pass + performance ≤1.20 + no overclaiming
