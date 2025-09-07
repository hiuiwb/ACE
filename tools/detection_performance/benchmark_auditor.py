#!/usr/bin/env python3
"""
Run the staff/patient analyzers on all CSVs in system_log/ and produce a summary CSV
with the following columns:

Dataset,#entries,%labeled violations,#labeled_violations,#auditor_detections,%detection_rate,total runtime (s),throughput (entries/s),peak memory (MB)

Usage: python3 tools/benchmark_auditor.py
Requires: psutil
"""
import csv
import glob
import os
import re
import subprocess
import sys
import time

try:
    import psutil
except Exception:
    print("psutil is required. Install with: pip install psutil")
    sys.exit(1)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SYSTEM_LOG = os.path.join(ROOT, 'system_log')
OUT_CSV = os.path.join(os.path.dirname(__file__), 'audit_benchmark_results.csv')

ANALYZERS = {
    'staff_activity': os.path.join('tools', 'analyze_staff_rule_instances.py'),
    'patient_request': os.path.join('tools', 'analyze_patient_rule_instances.py'),
}

RE_TOTAL = re.compile(r'total_rows.*?:\s*([0-9,]+)', re.IGNORECASE)
RE_LABELED = re.compile(r'labeled_violations.*?:\s*([0-9,]+)', re.IGNORECASE)
RE_AUDITOR = re.compile(r'auditor_rule_instances.*?:\s*([0-9,]+)', re.IGNORECASE)


def parse_summary(output_text):
    """Parse analyzer stdout for total rows, labeled violations, auditor detections."""
    total = None
    labeled = None
    auditor = None

    m = RE_TOTAL.search(output_text)
    if m:
        total = int(m.group(1).replace(',', ''))
    m = RE_LABELED.search(output_text)
    if m:
        labeled = int(m.group(1).replace(',', ''))
    m = RE_AUDITOR.search(output_text)
    if m:
        auditor = int(m.group(1).replace(',', ''))

    return total, labeled, auditor


def count_csv_rows(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            # assume header exists
            lines = sum(1 for _ in f)
            return max(0, lines - 1)
    except Exception:
        return None


def run_analyzer(analyzer_script, csv_path):
    env = os.environ.copy()
    # ensure local imports work
    env['PYTHONPATH'] = ROOT

    cmd = [sys.executable, analyzer_script, csv_path]

    start = time.time()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, text=True)
    psproc = psutil.Process(proc.pid)
    peak = 0
    output_lines = []

    # read stdout line-by-line while sampling memory
    try:
        while True:
            line = proc.stdout.readline()
            if line:
                output_lines.append(line)
            if proc.poll() is not None:
                # drain remaining
                rem = proc.stdout.read()
                if rem:
                    output_lines.append(rem)
                break
            # sample memory
            try:
                rss = psproc.memory_info().rss
                if rss > peak:
                    peak = rss
            except psutil.NoSuchProcess:
                pass
            time.sleep(0.01)
    except KeyboardInterrupt:
        proc.kill()
        raise

    retcode = proc.wait()
    end = time.time()
    runtime = end - start

    stdout_text = ''.join(output_lines)
    total, labeled, auditor = parse_summary(stdout_text)

    # fallback: count CSV rows if analyzer did not print total_rows
    if total is None:
        total = count_csv_rows(csv_path) or 0
    # fallback: if labeled or auditor missing, attempt to extract from 'Audit complete' or similar
    if labeled is None:
        m = re.search(r'Audit complete\. Found\s*([0-9,]+)\s*violation', stdout_text)
        if m:
            labeled = int(m.group(1).replace(',', ''))
    if auditor is None:
        # try to use labeled as auditor if only one reported
        auditor = labeled

    peak_mb = peak / (1024.0 * 1024.0)

    return {
        'total_rows': total,
        'labeled_violations': labeled or 0,
        'auditor_detections': auditor or 0,
        'runtime_s': round(runtime, 3),
        'throughput': round((total / runtime) if runtime > 0 else 0, 3),
        'peak_mem_mb': round(peak_mb, 2),
        'raw_stdout': stdout_text,
        'returncode': retcode,
    }


def main():
    patterns = [
        os.path.join(SYSTEM_LOG, 'staff_activity_*.csv'),
        os.path.join(SYSTEM_LOG, 'patient_request_*.csv'),
    ]
    files = []
    for p in patterns:
        files.extend(sorted(glob.glob(p)))

    if not files:
        print('No dataset CSVs found in system_log/. Generate logs first.')
        sys.exit(1)

    header = ['dataset', '#entries', '%labeled violations', '#labeled_violations', '#auditor_detections', '%detection_rate', 'total runtime (s)', 'throughput (entries/s)', 'peak memory (MB)']

    rows = []
    for path in files:
        name = os.path.basename(path)
        if 'staff_activity' in name:
            analyzer = ANALYZERS['staff_activity']
        elif 'patient_request' in name:
            analyzer = ANALYZERS['patient_request']
        else:
            print(f'Skipping unknown file: {name}')
            continue

        analyzer_path = os.path.join(ROOT, analyzer)
        if not os.path.exists(analyzer_path):
            print(f'Analyzer not found: {analyzer_path}. Skipping {name}.')
            continue

        print(f'Running analyzer for {name} ...')
        stats = run_analyzer(analyzer_path, path)

        total = stats['total_rows']
        labeled = stats['labeled_violations']
        auditor = stats['auditor_detections']
        detection_rate = round((auditor / total * 100.0) if total > 0 else 0.0, 3)
        pct_labeled = round((labeled / total * 100.0) if total > 0 else 0.0, 3)

        row = [
            name,
            total,
            pct_labeled,
            labeled,
            auditor,
            detection_rate,
            stats['runtime_s'],
            stats['throughput'],
            stats['peak_mem_mb'],
        ]
        rows.append(row)

    # write CSV
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for r in rows:
            writer.writerow(r)

    print('\nBenchmark complete. Results written to:', OUT_CSV)


if __name__ == '__main__':
    main()
