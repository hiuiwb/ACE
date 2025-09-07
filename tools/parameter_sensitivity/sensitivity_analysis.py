#!/usr/bin/env python3
"""
Sensitivity analysis for the compliance model.

- Lambda analysis: time-decayed severity using decay constant lambda; produces recovery curves.
- Alpha analysis: normalized volume score S_V vs alpha_V where k = 1/alpha_V so
  S_V = 1 - exp(-M_V/alpha_V), matching the interpretation in the writeup.

Outputs:
- tools/sensitivity_lambda.csv
- tools/sensitivity_alpha.csv
- tools/sensitivity_analysis.png
"""

import os
import sys
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ensure repo root on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scorer import ComplianceScorer

# --- Configuration ---
WEIGHTS = {'C':0.5, 'V':0.2, 'T':0.2, 'B':0.1}
# baseline normalization constants (not used directly for alpha experiment)
KS = {'V':0.1, 'T':0.05, 'B':0.2}
RULE_CRITICALITIES = {}
# Plot styling to match monthly_combined visuals
FONT_SIZE = 25
LINE_WIDTH = 2.5
MARKER_SIZE = 8
LEGEND_NCOL = 3

DATA_LOG = os.path.join('system_log','staff_activity_5000.csv')
OUT_DIR = os.path.join('tools')
os.makedirs(OUT_DIR, exist_ok=True)

scorer = ComplianceScorer(WEIGHTS, KS, RULE_CRITICALITIES)

# Helper: filter violations from staff log (same heuristic as other tools)
def load_violation_rows(log_path):
    df = pd.read_csv(log_path)
    # normalize column names if needed
    df.columns = [c.strip() for c in df.columns]
    if 'label' in df.columns:
        viol = df[df['label'].astype(str).str.lower().str.startswith('violation')]
    else:
        viol = df[~df['action'].astype(str).str.lower().isin(['', 'read_phi', 'request_access'])]
    # avoid pandas SettingWithCopyWarning by working on an explicit copy
    viol = viol.copy()
    viol['timestamp'] = pd.to_datetime(viol['timestamp'])
    return viol

viol_df = load_violation_rows(DATA_LOG)
if viol_df.empty:
    print('No violations found in', DATA_LOG)
    sys.exit(1)

# pick a principal with a reasonable number of violations (top violator)
top_principal = viol_df['principal'].value_counts().idxmax()
print('Selected principal for lambda analysis:', top_principal)

# choose the latest month for that principal and build grouped instances per RuleID
pv = viol_df[viol_df['principal'] == top_principal].copy()
pv['year'] = pv['timestamp'].dt.year
pv['month'] = pv['timestamp'].dt.month
# pick the most recent month available for that principal
latest_year_month = pv.sort_values('timestamp')['timestamp'].max()
# filter rows that belong to the same month as the latest timestamp
ly = latest_year_month.year
lm = latest_year_month.month
pv_month = pv[(pv['timestamp'].dt.year == ly) & (pv['timestamp'].dt.month == lm)].copy()
if pv_month.empty:
    pv_month = pv.copy()

# group by rule to compute the Volume/Duration/Breadth and the group's reference timestamp
groups = []
for rule_id, g in pv_month.groupby('label'):
    try:
        volume = int(g['resource'].nunique())
    except Exception:
        volume = int(len(g))
    duration = (g['timestamp'].max() - g['timestamp'].min()).days + 1
    # breadth: attempt to use resource_type KB via scorer
    breadth = 1
    try:
        types = set()
        for res in g['resource'].unique():
            t = scorer._get_resource_type(res)
            if t:
                types.add(t)
        if len(types) > 0:
            breadth = len(types)
    except Exception:
        breadth = 1
    ref_ts = g['timestamp'].max()
    groups.append({'RuleID': rule_id if pd.notna(rule_id) else 'unknown_rule',
                   'volume': volume, 'duration': duration, 'breadth': breadth,
                   'ref_ts': ref_ts})

if not groups:
    print('No grouped violation instances found for principal', top_principal)
    sys.exit(1)

# --- Lambda analysis ---
lambdas = [0.1, 0.5, 1.0]  # low forgiveness, balanced, high forgiveness
max_days = 180
days = np.arange(0, max_days+1)

lambda_rows = []
for lam in lambdas:
    scores = []
    for d in days:
        # for each group compute severity as in scorer, then apply decay factor exp(-lambda * age)
        max_decayed = 0.0
        for G in groups:
            s_v = scorer._normalize(G['volume'], scorer.k['V'])
            s_t = scorer._normalize(G['duration'], scorer.k['T'])
            s_b = scorer._normalize(G['breadth'], scorer.k['B'])
            criticality = scorer.rule_criticalities.get(G['RuleID'], 0.5)
            severity = (scorer.weights['C'] * criticality +
                        scorer.weights['V'] * s_v +
                        scorer.weights['T'] * s_t +
                        scorer.weights['B'] * s_b)
            # age is d days since the reference timestamp
            age = float(d)
            decayed = severity * math.exp(-lam * age)
            if decayed > max_decayed:
                max_decayed = decayed
        compliance = max(0.0, 1.0 - max_decayed)
        lambda_rows.append({'lambda': lam, 'day': int(d), 'score': float(compliance)})

lambda_df = pd.DataFrame(lambda_rows)
lambda_out = os.path.join(OUT_DIR, 'sensitivity_lambda.csv')
lambda_df.to_csv(lambda_out, index=False)
print('Wrote', lambda_out)

# --- Alpha analysis (volume scaling) ---
M_V = 20
alphas = np.linspace(5, 50, 46)  # 5..50 step 1
alpha_rows = []
for a in alphas:
    # map alpha to k as k = 1/alpha so that S_V = 1 - exp(-M/alpha)
    k = 1.0 / float(a)
    s_v = 1.0 - math.exp(-k * M_V)
    alpha_rows.append({'alpha': float(a), 's_v': float(s_v)})
alpha_df = pd.DataFrame(alpha_rows)
alpha_out = os.path.join(OUT_DIR, 'sensitivity_alpha.csv')
alpha_df.to_csv(alpha_out, index=False)
print('Wrote', alpha_out)

# --- Plotting ---
# Use a preferred style if available; fall back safely to common styles
# try:
#     plt.style.use('seaborn-darkgrid')
# except Exception:
#     try:
#         plt.style.use('seaborn')
#     except Exception:
#         plt.style.use('ggplot')

# Enforce white background and black text to match monthly_combined style
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'
plt.rcParams['savefig.facecolor'] = 'white'
plt.rcParams['text.color'] = 'k'
plt.rcParams['axes.labelcolor'] = 'k'
plt.rcParams['xtick.color'] = 'k'
plt.rcParams['ytick.color'] = 'k'
plt.rcParams['axes.edgecolor'] = 'k'
plt.rcParams['legend.frameon'] = False

# 1) Lambda recovery curves saved separately
fig, ax = plt.subplots(figsize=(7,5))
colors = plt.get_cmap('tab10')
for i, lam in enumerate(lambdas):
    subset = lambda_df[lambda_df['lambda'] == lam]
    ax.plot(subset['day'], subset['score'], label=f'lambda={lam}',
            linewidth=LINE_WIDTH, marker='o', markersize=MARKER_SIZE,
            markeredgecolor='k', markeredgewidth=0.8, color=colors(i))
ax.set_xlabel('Days since last violation', fontsize=FONT_SIZE, fontweight='bold')
ax.set_ylabel('Compliance score', fontsize=FONT_SIZE, fontweight='bold')
# ax.set_title('Decay / Recovery curves for different lambda', fontsize=FONT_SIZE, fontweight='bold')
# legend inside figure as single row
lg = ax.legend(loc='lower right', ncol=1, fontsize=FONT_SIZE, frameon=False)
for t in lg.get_texts():
    t.set_fontweight('bold')
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_xlim(0, 100)
# make ticks bold and sized
for tl in ax.get_xticklabels() + ax.get_yticklabels():
    tl.set_fontsize(FONT_SIZE)
    tl.set_fontweight('bold')
# enforce black spines (no outer figure border)
for spine in ax.spines.values():
    spine.set_visible(True)
    spine.set_edgecolor('k')
    spine.set_linewidth(1.0)
plt.tight_layout()
lambda_png = os.path.join(OUT_DIR, 'sensitivity_lambda.pdf')
plt.savefig(lambda_png, dpi=300, bbox_inches='tight')
print('Wrote', lambda_png)
plt.close(fig)

# 2) Alpha: Volume (S_V) — skip saving separate PNG per user request (CSV retained)
# (alpha_df already written to CSV above)

# 3) Alpha: Duration (S_T) analysis — treat M_T as example duration (days)
M_T = 10
alpha_rows_t = []
for a in alphas:
    k = 1.0 / float(a)
    s_t = 1.0 - math.exp(-k * M_T)
    alpha_rows_t.append({'alpha': float(a), 's_t': float(s_t)})
alpha_t_df = pd.DataFrame(alpha_rows_t)
alpha_t_out = os.path.join(OUT_DIR, 'sensitivity_alpha_duration.csv')
alpha_t_df.to_csv(alpha_t_out, index=False)
print('Wrote', alpha_t_out)
# Skip saving the separate duration PNG per request

# 4) Alpha: Breadth (S_B) analysis — treat M_B as example breadth (distinct types)
M_B = 3
alpha_rows_b = []
for a in alphas:
    k = 1.0 / float(a)
    s_b = 1.0 - math.exp(-k * M_B)
    alpha_rows_b.append({'alpha': float(a), 's_b': float(s_b)})
alpha_b_df = pd.DataFrame(alpha_rows_b)
alpha_b_out = os.path.join(OUT_DIR, 'sensitivity_alpha_breadth.csv')
alpha_b_df.to_csv(alpha_b_out, index=False)
print('Wrote', alpha_b_out)
# Skip saving the separate breadth PNG per request

# 5) Combined figure: S_V, S_T, S_B on same axes for direct comparison
fig, ax = plt.subplots(figsize=(7,5))
cols = plt.get_cmap('tab10')
ax.plot(alpha_df['alpha'], alpha_df['s_v'], marker='o', linewidth=LINE_WIDTH,
    markersize=MARKER_SIZE, markeredgecolor='k', markeredgewidth=0.8,
    label=r'$S_V$ (volume)', color=cols(0))
ax.plot(alpha_t_df['alpha'], alpha_t_df['s_t'], marker='s', linewidth=LINE_WIDTH,
    markersize=MARKER_SIZE, markeredgecolor='k', markeredgewidth=0.8,
    label=r'$S_T$ (duration)', color=cols(2))
ax.plot(alpha_b_df['alpha'], alpha_b_df['s_b'], marker='^', linewidth=LINE_WIDTH,
    markersize=MARKER_SIZE, markeredgecolor='k', markeredgewidth=0.8,
    label=r'$S_B$ (breadth)', color=cols(4))
ax.set_xlabel(r'alpha (scaling factor)', fontsize=FONT_SIZE, fontweight='bold')
ax.set_ylabel('Normalized score', fontsize=FONT_SIZE, fontweight='bold')
# ax.set_title('Normalized component scores vs alpha (comparison)', fontsize=FONT_SIZE, fontweight='bold')
# legend inside figure single row
lg = ax.legend(loc='upper right', ncol=1, fontsize=FONT_SIZE, frameon=False)
for t in lg.get_texts():
    t.set_fontweight('bold')
ax.grid(True, alpha=0.3, linestyle='--')
for tl in ax.get_xticklabels() + ax.get_yticklabels():
    tl.set_fontsize(FONT_SIZE)
    tl.set_fontweight('bold')
# enforce black spines (no outer figure border)
for spine in ax.spines.values():
    spine.set_visible(True)
    spine.set_edgecolor('k')
    spine.set_linewidth(1.0)
plt.tight_layout()
combined_png = os.path.join(OUT_DIR, 'sensitivity_alpha_combined.pdf')
combined_svg = os.path.join(OUT_DIR, 'sensitivity_alpha_combined.svg')
plt.savefig(combined_png, dpi=300, bbox_inches='tight')
plt.savefig(combined_svg, bbox_inches='tight')
print('Wrote', combined_png)
plt.close(fig)

# Small textual summary for quick interpretation
# For each lambda, compute time-to-recover to score >= 0.95 if any
summary_rows = []
for lam in lambdas:
    sub = lambda_df[lambda_df['lambda']==lam]
    rec = sub[sub['score'] >= 0.95]
    trec = int(rec['day'].min()) if not rec.empty else None
    summary_rows.append({'lambda': lam, 'days_to_95pct': trec})
summary_df = pd.DataFrame(summary_rows)
summary_out = os.path.join(OUT_DIR, 'sensitivity_lambda_summary.csv')
summary_df.to_csv(summary_out, index=False)
print('Wrote', summary_out)
print('\nSummary:')
print(summary_df.to_string(index=False))

print('\nDone.')
