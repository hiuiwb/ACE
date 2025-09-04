# Automated Compliance Engine (ACE)

This repository contains a reproducible test harness for automated compliance verification against GDPR and HIPAA-style policies. ACE couples a Prolog policy file with Python tooling to:

- build a small knowledge base (KB)
- generate KB-aware system logs (staff activities and patient requests)
- assert facts into the Prolog engine and collect rule-instance violations
- validate that generated violating events map to exactly one policy rule

This README is organized for quick onboarding and reproducible experiments.

## TL;DR — quick commands

Install dependencies and SWI-Prolog, then run:

```bash
python3 knowledge_base/kb_generation.py
python3 tools/generate_staff_logs.py
python3 tools/generate_patient_requests.py
PYTHONPATH=. python3 tools/analyze_staff_rule_instances.py system_log/staff_activity_10000.csv
```

See the `Quick start` section below for details.

## Table of contents

1. Quick start
2. Project layout
3. Generators & Analyzers
4. Validation 
5. Configuration
6. How to run (examples)
7. Troubleshooting
8. Contributing

## 1) Quick start

Requirements
- Python 3.9+
- SWI-Prolog installed (used via `pyswip`)

Install Python packages:

```bash
python3 -m pip install --user pandas numpy faker pyswip
# On macOS use: brew install swi-prolog
```

Generate KB and logs and validate a sample:

```bash
python3 knowledge_base/kb_generation.py
python3 tools/generate_staff_logs.py
python3 tools/generate_patient_requests.py
PYTHONPATH=. python3 tools/analyze_staff_rule_instances.py system_log/staff_activity_10000.csv
```

Notes: large analyzer runs produce verbose per-row assertion logs; rely on the final compact summary for validation.

## 2) Project layout

```
auditor.py                             # Audit engine that loads KB and runs Prolog queries
main.py                                # High-level runner and configuration
scorer.py                              # Compliance scoring logic
data_loader.py                         # Helpers: load KB and CSVs
knowledge_base/
  ├─ kb_generation.py                  # Create KB facts (CSV)
  └─ knowledge_base.csv                 # Generated KB
policy/
  └─ policy.pl                          # Prolog policy rules (GDPR/HIPAA predicates)
tools/
  ├─ generate_staff_logs.py             # KB-aware staff activity generator
  ├─ analyze_staff_rule_instances.py    # Analyzer for staff logs (validation)
  ├─ generate_patient_requests.py       # KB-aware patient request generator
  └─ analyze_patient_rule_instances.py  # Analyzer for patient logs (validation)
system_log/
  ├─ staff_activity_<N>.csv             # Generated staff CSVs (100,1000,5000,10000,50000)
  └─ patient_request_<N>.csv            # Generated patient request CSVs
```

## 3) Generators & Analyzers

- generate_staff_logs.py: creates KB-aware staff activity CSVs with configurable sizes and a violation rate. Recent edits enforce each labeled violation is constructed so it triggers exactly one policy rule.
- generate_patient_requests.py: creates patient-request CSVs (access, erasure, restriction) with similar guarantees.
- analyze_staff_rule_instances.py / analyze_patient_rule_instances.py: load a CSV, assert per-row facts into Prolog via `auditor.py`, collect violations, and print a compact summary including any multi-rule rows.

Use `PYTHONPATH=.` so the `auditor.py` module is importable by analyzer scripts.

## 4) Validation

Validation contract:
- Inputs: `knowledge_base/knowledge_base.csv` and one generated `system_log/*.csv`
- Analyzer output: counts for total rows, labeled_violations, auditor_rule_instances, unique_violating_rows, and distribution of distinct rules per row
- Success criteria: `labeled_violations == auditor_rule_instances` and zero rows that map to >1 rule

The analyzers include this check and will print a short report. For large files rely on the final summary (the scripts produce per-row Prolog assertion logs during the run which are verbose).

## 5) Configuration

Primary configuration is in `main.py` and within the generator scripts:

- Scoring weights — adjust importance for Criticality, Violations, Timeliness, Breadth
- Rule criticalities — severity levels per rule
- Normalization constants — used by the scorer
- AUDIT_DATE — the audit evaluation date (used by generators for reproducibility; example in repo: `2025-08-31`)

Generator-specific parameters (edit in `tools/generate_*` scripts): sizes, violation rate, and deterministic seed.

## 6) How to run (examples)

Generate KB and a full set of logs (sizes: 100, 1000, 5000, 10000, 50000):

```bash
python3 knowledge_base/kb_generation.py
python3 tools/generate_staff_logs.py
python3 tools/generate_patient_requests.py
```

Validate a specific CSV (recommended):

```bash
# staff
PYTHONPATH=. python3 tools/analyze_staff_rule_instances.py system_log/staff_activity_5000.csv

# patient
PYTHONPATH=. python3 tools/analyze_patient_rule_instances.py system_log/patient_request_50000.csv
```

Run the audit engine (example):

```bash
python3 main.py
```

## 7) Troubleshooting

- Module import errors: run analyzers with `PYTHONPATH=.` to ensure local modules (e.g. `auditor.py`) are found.
- SWI-Prolog: ensure it is installed and reachable; `pyswip` acts as the bridge. On macOS use Homebrew to install: `brew install swi-prolog`.
- Verbose logs: analyzer scripts print every asserted Prolog fact; for large files skip the assertion output and review the analyzer's final summary.