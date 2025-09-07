#!/usr/bin/env python3
"""Analyze patient request logs for multi-rule violations.

Usage: PYTHONPATH=. python3 tools/analyze_patient_rule_instances.py system_log/patient_request_1000.csv
"""
import sys
from collections import defaultdict, Counter
import pandas as pd

import data_loader
from auditor import Auditor


def analyze(path, kb_file='knowledge_base/knowledge_base.csv', audit_date='2025-08-31', max_samples=5):
    print(f'Analyzing {path}...')
    kb_df = data_loader.load_knowledge_base(kb_file)
    patient_df = data_loader.load_patient_log(path)
    labeled = int((patient_df['label'] != 'benign').sum()) if 'label' in patient_df.columns else 0

    aud = Auditor('policy/policy.pl')
    aud.load_kb_facts(kb_df)
    violations = aud.run_audit(patient_df, audit_date)

    total_rule_instances = len(violations)
    grouped = defaultdict(list)
    for v in violations:
        ts = v.get('timestamp')
        # Use request_timestamp string if available in DataFrame rows
        key = f"{v.get('Principal')}|{v.get('ObjectID')}|{ts}"
        grouped[key].append(v.get('RuleID'))

    counts = Counter(len(set(rules)) for rules in grouped.values())

    print('\nSummary:')
    print(f'  total_rows (file): {len(patient_df)}')
    print(f'  labeled_violations (ground truth): {labeled}')
    print(f'  auditor_rule_instances: {total_rule_instances}')
    print(f'  unique_violating_rows (detected): {len(grouped)}')
    print('  distribution of distinct rules per unique row:')
    for num_rules, cnt in sorted(counts.items()):
        print(f'    rows with {num_rules} distinct rule(s): {cnt}')

    multi_keys = [k for k, rules in grouped.items() if len(set(rules)) > 1]
    if not multi_keys:
        print('\nNo multi-rule rows detected.')
        return

    print(f'\nFound {len(multi_keys)} unique rows that triggered multiple distinct rules. Showing up to {max_samples} samples:')
    samples = multi_keys[:max_samples]
    patient_df['_row_key'] = patient_df.apply(lambda r: f"{r['principal']}|{r['resource']}|{r.get('request_timestamp')}", axis=1)
    for k in samples:
        print('\n---')
        print('row_key:', k)
        print('detected rules:', sorted(set(grouped[k])))
        matched = patient_df[patient_df['_row_key'] == k]
        if not matched.empty:
            print('matching log row(s):')
            print(matched.to_string(index=False))
        else:
            print('  (no exact log row match found; timestamps may differ in format)')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: PYTHONPATH=. python3 tools/analyze_patient_rule_instances.py <patient_csv_path>')
        sys.exit(1)
    analyze(sys.argv[1])
