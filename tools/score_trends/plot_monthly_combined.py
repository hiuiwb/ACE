#!/usr/bin/env python3
"""Composite plot: monthly rule violations (stacked bars per principal) and compliance trends (line plot)."""
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.gridspec import GridSpec
import numpy as np

# Visual defaults
FONT_SIZE = 15
mpl.rcParams['font.size'] = FONT_SIZE
mpl.rcParams['axes.titlesize'] = FONT_SIZE
mpl.rcParams['axes.labelsize'] = FONT_SIZE
mpl.rcParams['xtick.labelsize'] = FONT_SIZE
mpl.rcParams['ytick.labelsize'] = FONT_SIZE
mpl.rcParams['legend.fontsize'] = FONT_SIZE
mpl.rcParams['font.weight'] = 'bold'
mpl.rcParams['axes.titleweight'] = 'bold'

# Paths
LOG_PATH = os.path.join('system_log','staff_activity_5000.csv')
CSV_PATH = os.path.join('tools','monthly_compliance_scores.csv')
OUT_FILE = os.path.join('tools','monthly_combined.pdf')

# Check inputs
for path in [LOG_PATH, CSV_PATH]:
    if not os.path.exists(path):
        print(f"Missing file: {path}")
        raise SystemExit(1)

# Load raw log for rule violations
df_log = pd.read_csv(LOG_PATH)
df_log['timestamp'] = pd.to_datetime(df_log['timestamp'])
df_log['year'] = df_log['timestamp'].dt.year
df_log['month'] = df_log['timestamp'].dt.month
viol_df = df_log[df_log['label'].astype(str).str.lower().str.startswith('violation')]

# Group for bar facets
grouped = viol_df.groupby(['year','month','label','principal']).size().reset_index(name='count')
months = grouped[['year','month']].drop_duplicates().sort_values(['year','month']).values.tolist()
n_months = len(months)
# We'll use a two-panel layout: left for rule violations, right for compliance trends
cols = 2
rows = 1

# Load compliance CSV for lines
df_c = pd.read_csv(CSV_PATH)
df_c['month_start'] = pd.to_datetime(df_c[['year','month']].assign(day=1))
# unique principals
principals = sorted(df_c['principal'].unique())
# color map for principals
colors = mpl.cm.tab20.colors
color_map = {p: colors[i % len(colors)] for i,p in enumerate(principals)}


# Build a two-row single figure: top = trend (left y: score, right y: month totals), bottom = grouped stacked bars per month
months_sorted = sorted(grouped[['year','month']].drop_duplicates().values.tolist())
n_months = len(months_sorted)
rule_order = sorted(grouped['label'].unique())
n_rules = len(rule_order)

# Single axes: trend lines (left y) and grouped stacked bars per month (right y)
fig, ax_line = plt.subplots(figsize=(16,4))

# prepare month positions
month_centers = np.arange(n_months)

# Plot trends on primary axis (compliance score)
for p in principals:
    sub = df_c[df_c['principal'] == p].sort_values('month_start')
    scores = []
    for yy, mm in months_sorted:
        r = sub[(sub['year']==yy)&(sub['month']==mm)]
        scores.append(r['score'].iloc[0] if not r.empty else float('nan'))
    ax_line.plot(month_centers, scores, marker='o', label=p, color=color_map[p], linewidth=2.5, markersize=8)
# ax_line.set_title('Monthly compliance trends and per-month rule violations')
ax_line.set_xlim(-0.5, n_months-0.5)
ax_line.set_xticks(month_centers)
ax_line.set_xticklabels([f'{y}-{m:02d}' for y,m in months_sorted], rotation=0)
ax_line.set_ylabel('Compliance score', fontsize=FONT_SIZE, fontweight='bold')
ax_line.set_ylim(-0.05, 1.05)
ax_line.grid(True, linestyle='--', alpha=0.5)

# Secondary axis for violations
ax2 = ax_line.twinx()
# compute month totals
month_sums = grouped.groupby(['year','month'])['count'].sum().to_dict()
counts = [int(month_sums.get((yy, mm), 0)) for yy, mm in months_sorted]
# For each month, draw small stacked bars: one bar per rule, stacked by principal
group_width = 0.8
for mi, (yy, mm) in enumerate(months_sorted):
    sub = grouped[(grouped['year']==yy)&(grouped['month']==mm)]
    piv = sub.pivot(index='label', columns='principal', values='count').reindex(index=rule_order).fillna(0)
    n_r = len(rule_order)
    # offsets within the month: distribute small bars around the month center
    offsets = (np.arange(n_r) - (n_r-1)/2) * (group_width / max(1, n_r))
    for ri, rule in enumerate(rule_order):
        bottoms = 0
        x = mi + offsets[ri]
        for p in principals:
            val = piv.at[rule, p] if p in piv.columns else 0
            if val > 0:
                ax2.bar(x, val, bottom=bottoms, width=(group_width / max(1, n_r))*0.9, color=color_map[p], edgecolor='black', linewidth=0.6)
                bottoms += val
        if bottoms > 0:
            ax2.text(x, bottoms + max(1, bottoms*0.02), str(int(bottoms)), ha='center', va='bottom', fontsize=12, fontweight='bold')

ax2.set_ylabel('Violation counts', fontsize=FONT_SIZE, fontweight='bold')
ax2.set_ylim(0, max(1, int(max(counts) * 1.1)))

# Make y-axis tick labels bold and sized to FONT_SIZE for clarity
for lbl in ax_line.get_yticklabels():
    lbl.set_fontsize(FONT_SIZE)
    lbl.set_fontweight('bold')
for lbl in ax2.get_yticklabels():
    lbl.set_fontsize(FONT_SIZE)
    lbl.set_fontweight('bold')

# Single legend for principals (shared for lines and bars) placed inside the axes at the top center
handles = [plt.Rectangle((0,0),1,1, color=color_map[p]) for p in principals]
# place legend inside the main axes, top center
ax_line.legend(handles, principals, title='Principal', loc='upper center', bbox_to_anchor=(0.5, 0.95), ncol=len(principals), frameon=False, fontsize=FONT_SIZE)

# (Rule mapping text removed to keep the figure clean)

plt.tight_layout()
plt.savefig(OUT_FILE, dpi=150, bbox_inches='tight')
plt.close()
print('Wrote', OUT_FILE)
