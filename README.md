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
- Compliance scores based on:
  - Rule criticality (C)
  - Number of violations (V)
  - Request processing timeliness (T)
  - Coverage breadth (B)
- Scenario-based verification for GDPR and HIPAA compliance