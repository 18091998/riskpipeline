# RiskPipe Solution Blueprint

## Overview
Deterministic risk evaluation pipeline built over northgate_knowledge_graph.json (277 nodes, 403 edges, 11 issues) evaluated against run date 2026-11-20.

## Core Modules
- riskpipe/graph.py: Loads and queries nodes, edges, and issue neighborhoods.
- riskpipe/rules.py: Evaluates deterministic rule logic, control ratings, due dates, and escalations.
- riskpipe/llm.py & riskpipe/validators.py: Local Ollama client (qwen2.5:1.5b) and grounded ID validation.
- tests/test_pipeline.py: Automated pytest checks for pipeline logic and output files.

## Outputs
- output/risks.json: Full per-issue rule evaluation results.
- output/run_log.json: Execution metadata and issue count.
- output/risks.csv: Tabular summary for spreadsheet review.
