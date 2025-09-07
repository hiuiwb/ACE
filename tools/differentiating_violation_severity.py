#!/usr/bin/env python3
"""
Differentiating Violation Severity experiment.
Compares ACE scorer against Binary and Count-based baselines for four scenarios.
Outputs:
 - tools/differentiating_violation_severity.csv
 - tools/differentiating_violation_severity.png

Assumptions:
 - All scenarios are evaluated for principal 'doctor_A' within a single 30-day window.
 - For the count-based model we assume N_total_events = 100 for normalization (can be adjusted).
"""

import os
import sys
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scorer import ComplianceScorer

OUT_DIR = os.path.join('tools')
os.makedirs(OUT_DIR, exist_ok=True)

# Model parameters (same as earlier experiments)
WEIGHTS = {'C':0.5, 'V':0.2, 'T':0.2, 'B':0.1}
KS = {'V':0.1, 'T':0.05, 'B':0.2}
RULE_CRITICALITIES = {
    'hipaa_auth_control': 0.8,
    'gdpr_art17_erasure': 0.95
}

scorer = ComplianceScorer(WEIGHTS, KS, RULE_CRITICALITIES)

principal = 'doctor_A'
# base date for scenario timestamps
base = pd.Timestamp('2025-08-01')

# Helper to create violation records
def make_record(ruleid, principal, resource, ts):
    return {'RuleID': ruleid, 'Principal': principal, 'resource': resource, 'timestamp': ts}

# Scenario A: single low-impact violation (1 resource, 1 day)
scenario_A = [make_record('hipaa_auth_control', principal, 'res_A_1', base + pd.Timedelta(days=2))]

# Scenario B: high volume (50 unique resources over 2 days)
scenario_B = []
for i in range(50):
    day = 5 + (i % 2)  # distribute across two days
    scenario_B.append(make_record('hipaa_auth_control', principal, f'res_B_{i}', base + pd.Timedelta(days=day)))

# Scenario C: high criticality, not fulfilled within 30 days (create events spanning >30 days)
scenario_C = [make_record('gdpr_art17_erasure', principal, 'res_C_1', base + pd.Timedelta(days=10)),
              make_record('gdpr_art17_erasure', principal, 'res_C_1', base + pd.Timedelta(days=42))]

# Scenario D: high duration: same resource accessed once per day for 25 consecutive days
scenario_D = []
for d in range(25):
    scenario_D.append(make_record('hipaa_auth_control', principal, 'res_D_1', base + pd.Timedelta(days=60 + d)))

scenarios = {
    'A_low_impact': scenario_A,
    'B_high_volume': scenario_B,
    'C_high_criticality': scenario_C,
    'D_high_duration': scenario_D
}

# Baseline params
TOTAL_EVENTS = 100.0  # assumption for count-based normalization

rows = []
for name, vio in scenarios.items():
    # ACE score
    ace_res = scorer.calculate_final_score(vio, principal_id=principal, time_window_days=30)
    if isinstance(ace_res, tuple):
        ace_score, breakdown = ace_res
    else:
        ace_score = ace_res
        breakdown = None
    # Binary model
    binary_score = 0.0 if len(vio) > 0 else 1.0
    # Count-based model
    n_viol = float(len(vio))
    count_score = max(0.0, 1.0 - (n_viol / TOTAL_EVENTS))

    rows.append({'scenario': name, 'ACE_score': float(ace_score), 'Binary_score': float(binary_score),
                 'Count_score': float(count_score), 'n_violations': int(n_viol)})

out_df = pd.DataFrame(rows)
out_csv = os.path.join(OUT_DIR, 'differentiating_violation_severity.csv')
out_df.to_csv(out_csv, index=False)
print('Wrote', out_csv)

# Plot comparison
# try:
#     plt.style.use('seaborn-whitegrid')
# except Exception:
#     try:
#         plt.style.use('seaborn')
#     except Exception:
#         plt.style.use('ggplot')
FONT_SIZE = 14
fig, ax = plt.subplots(figsize=(9,5))
index = np.arange(len(out_df))
width = 0.25
ax.bar(index - width, out_df['ACE_score'], width=width, label='ACE', color='C0', edgecolor='k')
ax.bar(index, out_df['Count_score'], width=width, label='Count-based', color='C1', edgecolor='k')
ax.bar(index + width, out_df['Binary_score'], width=width, label='Binary', color='C2', edgecolor='k')

ax.set_xticks(index)
ax.set_xticklabels(out_df['scenario'], fontsize=FONT_SIZE, fontweight='bold')
ax.set_ylabel('Score', fontsize=FONT_SIZE, fontweight='bold')
ax.set_ylim(-0.05, 1.05)
ax.grid(True, alpha=0.3, linestyle='--')
ax.legend(fontsize=FONT_SIZE-2)
for tl in ax.get_yticklabels():
    tl.set_fontsize(FONT_SIZE)
    tl.set_fontweight('bold')
plt.tight_layout()
plot_png = os.path.join(OUT_DIR, 'differentiating_violation_severity.png')
plt.savefig(plot_png, dpi=300)
print('Wrote', plot_png)

print('\nResults:')
print(out_df.to_string(index=False))
