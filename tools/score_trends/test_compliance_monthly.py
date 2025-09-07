#!/usr/bin/env python3
import pandas as pd
import os
import sys
# ensure repository root is on sys.path so local modules (e.g., scorer.py) can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from scorer import ComplianceScorer

# parameters (same as weekly)
weights = {'C':0.5, 'V':0.2, 'T':0.2, 'B':0.1}
ks = {'V':0.1, 'T':0.05, 'B':0.2}
# example criticalities (should cover all rule IDs in staff policy)
rule_criticalities = {'rule_1': 0.8, 'rule_2': 0.6}

scorer = ComplianceScorer(weights, ks, rule_criticalities,
                           kb_path=os.path.join('knowledge_base','knowledge_base.csv'))

# read updated staff activity log (5k entries)
df = pd.read_csv(os.path.join('system_log','staff_activity_5000.csv'))
# parse timestamps
df['timestamp'] = pd.to_datetime(df['timestamp'])
# add year/month for grouping monthly
df['year'] = df['timestamp'].dt.year
df['month'] = df['timestamp'].dt.month

# filter violations: using 'label' column if exists
if 'label' in df.columns:
    viol_df = df[df['label'].astype(str).str.lower().str.startswith('violation')]
else:
    viol_df = df[~df['action'].astype(str).str.lower().isin(['', 'read_phi', 'request_access'])]

out_rows = []
# group by month
for (year, month), group in viol_df.groupby(['year','month']):
    principals = group['principal'].unique()
    for p in principals:
        pv = group[group['principal'] == p]
        # build violations list expected by the scorer
        violations = []
        for _, r in pv.iterrows():
            ruleid = r.get('label') if pd.notna(r.get('label')) else 'unknown_rule'
            violations.append({'RuleID': ruleid,
                               'Principal': r.get('principal'),
                               'resource': r.get('resource'),
                               'timestamp': r.get('timestamp')})
        score_res = scorer.calculate_final_score(violations, p, time_window_days=30)
        # unpack score and optional breakdown
        if isinstance(score_res, tuple):
            score, _ = score_res
        else:
            score = score_res
        viol_count = int(len(pv))
        out_rows.append({'year': int(year), 'month': int(month),
                         'principal': p, 'score': float(score),
                         'violations': viol_count})
# construct DataFrame
out_df = pd.DataFrame(out_rows)
# compute month-level totals
totals = out_df.groupby(['year','month'])['violations'].sum().reset_index()
totals = totals.rename(columns={'violations':'month_total_violations'})
out_df = out_df.merge(totals, on=['year','month'], how='left')
# sort
out_df = out_df.sort_values(['year','month','principal'])
# save
out_dir = os.path.join('tools')
if not os.path.exists(out_dir):
    os.makedirs(out_dir)
out_path = os.path.join(out_dir, 'monthly_compliance_scores.csv')
out_df.to_csv(out_path, index=False)
print('Wrote', out_path)

# Also export per-rule-per-principal monthly counts for plotting
grouped_rules = viol_df.groupby(['year','month','label','principal']).size().reset_index(name='count')
rules_out = os.path.join(out_dir, 'monthly_rule_principal_counts.csv')
grouped_rules.to_csv(rules_out, index=False)
print('Wrote', rules_out)
