# Automated Compliance Engine

This project is a simulation and audit engine for automated compliance checking against GDPR and HIPAA policies. It integrates Python and Prolog to detect violations, score compliance, and support scenario-driven verification for data protection regulations.

## Features
- **Knowledge Base Generation:** Scripts to generate testable facts for users, resources, requests, and consent.
- **System Log Simulation:** Realistic event logs for user actions, access requests, and data processing.
- **Policy Rules:** Prolog rules for GDPR (Articles 15, 17, 18) and HIPAA (minimum necessary, patient access, breach notification).
- **Automated Audit:** Python engine loads KB and logs, asserts facts, runs Prolog queries, and outputs detailed violation reports and compliance scores.
- **Scenario Coverage:** Built-in test cases for erasure, restriction, access requests, and more.

## Project Structure
```
auditor.py           # Python audit engine
main.py              # Main entry point
score.py             # Compliance scoring logic
data_loader.py       # Data loading utilities
knowledge_base/      # KB generation scripts and facts
system_log/          # Log generation scripts and logs
policy/policy.pl     # Prolog policy rules
```

## How to Run
1. Install Python 3.9+ and SWI-Prolog.
2. Install dependencies:
   ```bash
   pip install pandas numpy faker pyswip
   ```
3. Generate the knowledge base and system log:
   ```bash
   python3 knowledge_base/knowlege_base_generation.py
   python3 system_log/system_log_generation.py
   ```
4. Run the main audit engine:
   ```bash
   python3 main.py
   ```

## Customization
- Edit `knowledge_base/knowlege_base_generation.py` and `system_log/system_log_generation.py` to add new scenarios or test cases.
- Update `policy/policy.pl` to modify or extend compliance rules.

## Output
- Detailed violation summary per principal
- Compliance scores
- Scenario-driven verification for GDPR and HIPAA