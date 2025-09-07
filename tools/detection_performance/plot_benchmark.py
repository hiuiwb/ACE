#!/usr/bin/env python3
"""
Plot audit benchmark results produced by `tools/benchmark_auditor.py`.

Generates PNGs in `tools/benchmark_plots/`:
 - runtime_vs_entries.png (log-scale x)
 - throughput_vs_entries.png (log-scale x)
 - peakmem_vs_entries.png (log-scale x)
 - detection_rate.png
 - labeled_vs_detected.png

Usage:
  python3 tools/plot_benchmark.py [--csv PATH] [--outdir PATH]

Requires: pandas, matplotlib, seaborn
Install with: pip install pandas matplotlib seaborn
"""
import argparse
import os
import sys

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
except Exception:
    print('This script requires pandas, matplotlib and seaborn. Install with: pip install pandas matplotlib seaborn')
    sys.exit(1)

# visual styling
FONT_SIZE = 25
sns.set(style='whitegrid')
import matplotlib as mpl
mpl.rcParams['font.size'] = FONT_SIZE
mpl.rcParams['axes.titlesize'] = FONT_SIZE
mpl.rcParams['axes.labelsize'] = FONT_SIZE
mpl.rcParams['xtick.labelsize'] = FONT_SIZE
mpl.rcParams['ytick.labelsize'] = FONT_SIZE
mpl.rcParams['legend.fontsize'] = FONT_SIZE
mpl.rcParams['figure.titlesize'] = FONT_SIZE
mpl.rcParams['font.weight'] = 'bold'
mpl.rcParams['axes.titleweight'] = 'bold'
mpl.rcParams['axes.labelweight'] = 'bold'
from matplotlib.ticker import FuncFormatter


def ensure_outdir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def load_csv(path):
    df = pd.read_csv(path)
    # normalize column names
    df.columns = [c.strip() for c in df.columns]
    # ensure numeric types
    for col in ['#entries', '%labeled violations', '#labeled_violations', '#auditor_detections', '%detection_rate', 'total runtime (s)', 'throughput (entries/s)', 'peak memory (MB)']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def _style_axes(ax):
    # set black border
    for spine in ['top', 'right', 'bottom', 'left']:
        ax.spines[spine].set_color('black')
        ax.spines[spine].set_linewidth(1.5)


def _annotate_points(ax, x, y, fmt='{:.2f}', y_offset=6, x_offsets=None, va='bottom'):
    # x and y are sequences; x_offsets is sequence of values in points to shift label horizontally
    if x_offsets is None:
        x_offsets = [0] * len(x)
    for xi, yi, xo in zip(x, y, x_offsets):
        ax.annotate(fmt.format(yi), xy=(xi, yi), xytext=(xo, y_offset), textcoords='offset points', ha='center', fontsize=FONT_SIZE, fontweight='bold', bbox=dict(facecolor='white', edgecolor='none', alpha=0.8))


def plot_runtime(df, outdir):
    plt.figure(figsize=(10,6))
    df_sorted = df.sort_values('#entries')
    ax = plt.gca()
    # split into staff vs patient datasets
    staff_df = df_sorted[df_sorted['dataset'].str.contains('staff', case=False, na=False)]
    patient_df = df_sorted[df_sorted['dataset'].str.contains('patient', case=False, na=False)]
    # plot staff and patient as separate lines
    if not staff_df.empty:
        ax.plot(staff_df['#entries'], staff_df['total runtime (s)'], marker='o', markersize=10, linewidth=3, color='tab:blue', label='Staff activity')
    if not patient_df.empty:
        ax.plot(patient_df['#entries'], patient_df['total runtime (s)'], marker='s', markersize=10, linewidth=3, color='tab:green', label='Patient requests')
    ax.set_xscale('log')
    ax.set_xlabel('Entries (log scale)')
    ax.set_ylabel('Total runtime (s)')
    # ax.set_title('Audit runtime vs dataset size')
    # set preferred x-ticks for readability (numeric positions with short labels)
    preferred_vals = [5000, 10000, 50000, 100000, 200000, 500000]
    preferred_labels = ['5k', '10k', '50k', '100k', '200k', '500k']
    ax.set_xticks(preferred_vals)
    ax.set_xticklabels(preferred_labels)
    _style_axes(ax)
    ax.legend()
    plt.tight_layout()
    out = os.path.join(outdir, 'runtime_vs_entries.png')
    plt.savefig(out, dpi=200)
    plt.close()
    return out


def plot_throughput(df, outdir):
    plt.figure(figsize=(10,6))
    df_sorted = df.sort_values('#entries')
    ax = plt.gca()
    staff_df = df_sorted[df_sorted['dataset'].str.contains('staff', case=False, na=False)]
    patient_df = df_sorted[df_sorted['dataset'].str.contains('patient', case=False, na=False)]
    if not staff_df.empty:
        ax.plot(staff_df['#entries'], staff_df['throughput (entries/s)'], marker='o', markersize=10, linewidth=3, color='tab:blue', label='Staff activity')
    if not patient_df.empty:
        ax.plot(patient_df['#entries'], patient_df['throughput (entries/s)'], marker='s', markersize=10, linewidth=3, color='tab:green', label='Patient requests')
    ax.set_xscale('log')
    ax.set_xlabel('Entries (log scale)')
    ax.set_ylabel('Throughput (entries/s)')
    # ax.set_title('Throughput vs dataset size')
    preferred_vals = [5000, 10000, 50000, 100000, 200000, 500000]
    preferred_labels = ['5k', '10k', '50k', '100k', '200k', '500k']
    ax.set_xticks(preferred_vals)
    ax.set_xticklabels(preferred_labels)
    _style_axes(ax)
    ax.legend()
    plt.tight_layout()
    out = os.path.join(outdir, 'throughput_vs_entries.png')
    plt.savefig(out, dpi=200)
    plt.close()
    return out


def plot_peakmem(df, outdir):
    plt.figure(figsize=(10,6))
    df_sorted = df.sort_values('#entries')
    ax = plt.gca()
    staff_df = df_sorted[df_sorted['dataset'].str.contains('staff', case=False, na=False)]
    patient_df = df_sorted[df_sorted['dataset'].str.contains('patient', case=False, na=False)]
    if not staff_df.empty:
        ax.plot(staff_df['#entries'], staff_df['peak memory (MB)'], marker='o', markersize=10, linewidth=3, color='tab:blue', label='Staff activity')
    if not patient_df.empty:
        ax.plot(patient_df['#entries'], patient_df['peak memory (MB)'], marker='s', markersize=10, linewidth=3, color='tab:green', label='Patient requests')
    ax.set_xscale('log')
    ax.set_xlabel('Entries (log scale)')
    ax.set_ylabel('Peak memory (MB)')
    # ax.set_title('Peak memory vs dataset size')
    preferred_vals = [5000, 10000, 50000, 100000, 200000, 500000]
    preferred_labels = ['5k', '10k', '50k', '100k', '200k', '500k']
    ax.set_xticks(preferred_vals)
    ax.set_xticklabels(preferred_labels)
    _style_axes(ax)
    ax.legend()
    plt.tight_layout()
    out = os.path.join(outdir, 'peakmem_vs_entries.png')
    plt.savefig(out, dpi=200)
    plt.close()
    return out


def plot_detection_rate(df, outdir):
    plt.figure(figsize=(12,6))
    # seaborn palette expects a palette name or list; using matplotlib color and black edges
    ax = sns.barplot(x='dataset', y='%detection_rate', data=df, color='tab:orange', edgecolor='black')
    plt.xticks(rotation=0, ha='right')
    plt.ylabel('% detection rate')
    # plt.title('Detection rate per dataset')
    _style_axes(ax)
    # no bar-value annotations (cleaner presentation)
    # ensure xtick labels are bold and readable
    for lbl in ax.get_xticklabels():
        lbl.set_fontweight('bold')
    plt.tight_layout()
    out = os.path.join(outdir, 'detection_rate.png')
    plt.savefig(out, dpi=200)
    plt.close()
    return out


def plot_labeled_vs_detected(df, outdir):
    plt.figure(figsize=(10,6))
    dfm = df.copy()
    dfm = dfm.sort_values('#entries')
    ax = plt.gca()
    # split into staff vs patient and plot both labeled and detected per type
    staff_df = dfm[dfm['dataset'].str.contains('staff', case=False, na=False)]
    patient_df = dfm[dfm['dataset'].str.contains('patient', case=False, na=False)]
    if not staff_df.empty:
        ax.plot(staff_df['#entries'], staff_df['#labeled_violations'], marker='o', markersize=10, linewidth=3, color='tab:blue', label='Staff labeled')
        ax.plot(staff_df['#entries'], staff_df['#auditor_detections'], marker='x', markersize=10, linewidth=3, color='tab:red', label='Staff detected')
    if not patient_df.empty:
        ax.plot(patient_df['#entries'], patient_df['#labeled_violations'], marker='s', markersize=10, linewidth=3, color='tab:cyan', label='Patient labeled')
        ax.plot(patient_df['#entries'], patient_df['#auditor_detections'], marker='D', markersize=10, linewidth=3, color='tab:orange', label='Patient detected')
    ax.set_xscale('log')
    ax.set_xlabel('Entries (log scale)')
    ax.set_ylabel('Violations (count)')
    # ax.set_title('Labeled vs Auditor-detected violations')
    ax.legend()
    _style_axes(ax)
    preferred_vals = [5000, 10000, 50000, 100000, 200000, 500000]
    preferred_labels = ['5k', '10k', '50k', '100k', '200k', '500k']
    ax.set_xticks(preferred_vals)
    ax.set_xticklabels(preferred_labels)
    plt.tight_layout()
    out = os.path.join(outdir, 'labeled_vs_detected.png')
    plt.savefig(out, dpi=200)
    plt.close()
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--csv', default=os.path.join('tools', 'audit_benchmark_results.csv'), help='Path to benchmark CSV')
    p.add_argument('--outdir', default=os.path.join('tools', 'benchmark_plots'), help='Output directory for PNGs')
    args = p.parse_args()

    if not os.path.exists(args.csv):
        print(f'Benchmark CSV not found: {args.csv}')
        sys.exit(1)

    df = load_csv(args.csv)
    ensure_outdir(args.outdir)

    # rename columns to simpler keys for plotting convenience if necessary
    # expected columns: dataset, #entries, %labeled violations, #labeled_violations, #auditor_detections, %detection_rate, total runtime (s), throughput (entries/s), peak memory (MB)
    # normalize column names to friendly ones
    colmap = {
        '#entries': '#entries',
        '%labeled violations': '%labeled violations',
        '#labeled_violations': '#labeled_violations',
        '#auditor_detections': '#auditor_detections',
        '%detection_rate': '%detection_rate',
        'total runtime (s)': 'total runtime (s)',
        'throughput (entries/s)': 'throughput (entries/s)',
        'peak memory (MB)': 'peak memory (MB)'
    }

    # ensure required columns exist
    req = ['dataset', '#entries', '#labeled_violations', '#auditor_detections', '%detection_rate', 'total runtime (s)', 'throughput (entries/s)', 'peak memory (MB)']
    for c in req:
        if c not in df.columns:
            print(f'Missing required column in CSV: {c}')
            sys.exit(1)

    # generate plots
    outputs = []
    outputs.append(plot_runtime(df, args.outdir))
    outputs.append(plot_throughput(df, args.outdir))
    outputs.append(plot_peakmem(df, args.outdir))
    outputs.append(plot_labeled_vs_detected(df, args.outdir))
    # for detection rate use a copy with dataset as string labels
    df_bar = df.copy()
    df_bar['dataset'] = df_bar['dataset'].astype(str)
    outputs.append(plot_detection_rate(df_bar, args.outdir))

    print('Plots written:')
    for o in outputs:
        print('  -', o)


if __name__ == '__main__':
    main()
