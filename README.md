# Automated Compliance Engine (ACE)

This project is a simulation and audit engine for automated compliance checking against GDPR and HIPAA policies. It integrates Python and Prolog to detect violations, score compliance, and support scenario-driven verification for data protection regulations.

## Features
- **Knowledge Base Generation:** Scripts to generate testable facts for users, resources, requests, and consent.
- **System Log Simulation:** Realistic event logs for user actions, access requests, and data processing.
- **Policy Rules:** Prolog rules for GDPR (Articles 15, 17, 18) and HIPAA (minimum necessary, patient access).
- **Automated Audit:** Python engine loads KB and logs, asserts facts, runs Prolog queries, and outputs detailed violation reports with configurable scoring weights.
- **Compliance Scoring:** Sophisticated scoring system with customizable weights for different compliance aspects (criticality, violations, timeliness, and breadth).
- **Scenario Coverage:** Built-in test cases for erasure, restriction, access requests, and more.

## Project Structure
```
auditor.py                    # Python audit engine
main.py                      # Main entry point and configuration
scorer.py                    # Compliance scoring logic
data_loader.py              # Data loading utilities
knowledge_base/
  ├── kb_generation.py      # Knowledge base generation script
  └── knowledge_base.csv    # Generated knowledge base facts
system_log/
  ├── patient_log_generation.py    # Patient request log generator
  ├── staff_log_generation.py      # Staff activity log generator
  ├── patient_request_log.csv      # Patient request events
  └── staff_activity_log.csv       # Staff activity events
policy/
  └── policy.pl            # Prolog policy rules
```

## Configuration
The system can be configured through parameters in `main.py`:
- **Scoring Weights:** Customize importance of different compliance aspects (Criticality, Violations, Timeliness, Breadth)
- **Rule Criticalities:** Set severity levels for different policy rules
- **Normalization Constants:** Adjust scoring normalization factors
- **Audit Date:** Set the date for compliance evaluation

## How to Run
1. Install Python 3.9+ and SWI-Prolog
2. Install dependencies:
   ```bash
   pip install pandas numpy faker pyswip
   ```
3. Generate test data:
   ```bash
   python3 knowledge_base/kb_generation.py
   python3 system_log/patient_log_generation.py
   python3 system_log/staff_log_generation.py
   ```
4. Run the audit engine:
   ```bash
   python3 main.py
   ```

## Customization
- Modify scoring parameters in `main.py` to adjust compliance evaluation
- Edit log generation scripts to create different test scenarios
- Update `policy/policy.pl` to modify compliance rules
- Adjust knowledge base generation for different entity relationships

## Output
The system generates:
- Detailed violation reports per policy rule
# Automated Compliance Engine (ACE)

ACE is a simulation and audit toolkit for testing GDPR and HIPAA compliance. It combines a Prolog policy engine with Python-based generators and auditors to produce reproducible system logs, assert facts from a knowledge base, and report policy violations and compliance scores.

## Highlights
- KB-aware log generators for staff activities and patient requests
- Prolog policies for GDPR (Art.15/17/18) and HIPAA concepts (minimum necessary, patient access)
- Python auditor that asserts KB and event facts into SWI-Prolog and collects rule-instance violations
- Validation tools (analyzers) that confirm generator labels match auditor detections (single-rule-per-violation option)

## Project structure (relevant files)

```
auditor.py                             # Python audit engine that talks to SWI-Prolog
main.py                                # Entry point / high-level configuration
scorer.py                              # Compliance scoring logic
data_loader.py                         # KB and CSV loading helpers used by analyzers
knowledge_base/
  ├─ kb_generation.py                  # KB generation
  └─ knowledge_base.csv                 # Knowledge base facts
policy/
  └─ policy.pl                          # Prolog policy rules
tools/
  ├─ generate_staff_logs.py             # KB-aware staff activity log generator
  ├─ analyze_staff_rule_instances.py    # Analyzer that validates staff CSVs against auditor
  ├─ generate_patient_requests.py       # KB-aware patient request log generator
  └─ analyze_patient_rule_instances.py  # Analyzer that validates patient CSVs against auditor
system_log/
  ├─ staff_activity_<N>.csv             # Generated staff logs (e.g. staff_activity_10000.csv)
  └─ patient_request_<N>.csv            # Generated patient request logs (e.g. patient_request_50000.csv)
```

Notes:
- Generators produce a set of CSV files under `system_log/` with the naming convention shown above.
- By default generators use an `AUDIT_DATE` constant (example in repo: `2025-08-31`) so results are reproducible.

## Option B — single-rule-per-violation

The recent generators implement an Option B constraint: when a row is labeled as a violation, the generator constructs the event so it triggers exactly one policy rule in the Prolog policy. Validation uses the analyzer scripts and the auditor; the expected invariant is:

`labeled_violations == auditor_rule_instances` and no single row maps to >1 rule instance.

The analyzers report a compact summary (total rows, labeled violations, auditor rule instances, unique violating rows, and distribution of distinct rules per violating row) and will flag multi-rule rows if they occur.

## Quick start

1) Install system requirements

```bash
# macOS / Linux
python3 -m pip install --user pandas numpy faker pyswip
# Install SWI-Prolog separately (e.g. Homebrew: `brew install swi-prolog`)
```

2) Generate the knowledge base

```bash
python3 knowledge_base/kb_generation.py
```

3) Generate system logs (example sizes: 100, 1000, 5000, 10000, 50000)

```bash
# staff logs (produces system_log/staff_activity_100.csv etc.)
python3 tools/generate_staff_logs.py

# patient request logs (produces system_log/patient_request_100.csv etc.)
python3 tools/generate_patient_requests.py
```

4) Validate a generated CSV with the auditor/analyzer (recommended: use `PYTHONPATH=.` so the auditor imports correctly)

```bash
# Analyze a staff file
PYTHONPATH=. python3 tools/analyze_staff_rule_instances.py system_log/staff_activity_10000.csv

# Analyze a patient request file
PYTHONPATH=. python3 tools/analyze_patient_rule_instances.py system_log/patient_request_50000.csv
```

The analyzer prints per-row Prolog assertion logs during the run and then a compact final summary. For large files rely on the final summary for correctness checks.

## Validation contract (quick)

- Inputs: KB CSV (`knowledge_base/knowledge_base.csv`) and a generated system log CSV
- Output: Analyzer summary showing counts of labeled vs detected violations and whether any single row triggered >1 rule
- Success criteria: `labeled_violations == auditor_rule_instances` and zero multi-rule rows

## Extending / Customizing

- Adjust `AUDIT_DATE` or generator parameters in the corresponding `tools/` script to vary scenarios
- Edit `policy/policy.pl` to change rules; use the analyzers to re-run validation
- If you want quieter analyzer output, consider adding a `--quiet` flag to the analyzer scripts (not yet implemented in core)

## Troubleshooting

- If an analyzer fails with `ModuleNotFoundError`, ensure you run it with `PYTHONPATH=.` so local modules (e.g. `auditor.py`) are importable.
- The Prolog engine (SWI-Prolog) must be installed and reachable via `pyswip`/system paths.

## Contributing

- Make changes in the `tools/` folder for generators and analyzers.
- Run the analyzers after generating logs to check Option B constraints are preserved.
