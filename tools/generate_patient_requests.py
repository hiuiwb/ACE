#!/usr/bin/env python3
"""Generate patient request logs (request_access / request_deactivation).

Creates CSV files in `system_log/` for sizes [100,1000,5000,10000,50000]
with a target violation rate of 5%. Each violating row is constructed so it
triggers exactly one GDPR rule from `policy/policy.pl` (either
`gdpr_art15_access` for access requests or `gdpr_art17_erasure` for
deactivation requests).

This script consults `knowledge_base/knowledge_base.csv` to pick valid
patient and PHI record ids and to ensure we select patients who have
assigned doctors (so violations will be attributable in the policy).
"""
import math
import csv
import random
from datetime import datetime, timedelta
import pandas as pd

KB_FILE = "knowledge_base/knowledge_base.csv"
OUT_DIR = "system_log"
SIZES = [100, 1000, 5000, 10000, 50000]
VIOLATION_RATE = 0.05
AUDIT_DATE = datetime(2025, 8, 31)


def load_kb(kb_file=KB_FILE):
    df = pd.read_csv(kb_file, dtype=str)
    return df.fillna('')


def build_patient_phi_map(kb_df):
    # owns_phi_record(Patient, PHI_Record)
    mask = (kb_df['fact_name'] == 'owns_phi_record')
    rows = kb_df[mask]
    mapping = {}
    for _, r in rows.iterrows():
        patient = r['arg1']
        phi = r['arg2']
        if patient and phi:
            mapping.setdefault(patient, []).append(phi)
    return mapping


def build_patient_with_doctor_set(kb_df):
    # is_doctor_of(Doctor, Patient) -> we want patients that have at least one doctor
    mask = (kb_df['fact_name'] == 'is_doctor_of')
    rows = kb_df[mask]
    patients = set()
    for _, r in rows.iterrows():
        patient = r['arg2']
        if patient:
            patients.add(patient)
    return patients


def iso(ts):
    return ts.strftime('%Y-%m-%dT%H:%M:%S')


def make_access_row(req_id, patient, phi, req_time, fulfilled=False, requested_attrs=None):
    # process_timestamp is left empty for unfulfilled requests (violations)
    proc_time = None if not fulfilled else (req_time + timedelta(days=random.randint(1, 25)))
    requested_attrs = requested_attrs or ['clinical_note']
    return {
        'log_id': req_id,
        'principal': patient,
        'action': 'request_access',
        'resource': phi,
        'lab_result': 1 if 'lab_result' in requested_attrs else 0,
        'clinical_note': 1 if 'clinical_note' in requested_attrs else 0,
        'billing_info': 1 if 'billing_info' in requested_attrs else 0,
        'request_timestamp': iso(req_time),
        'process_timestamp': iso(proc_time) if proc_time else '',
        'label': 'violation_gdpr_art15' if not fulfilled and (AUDIT_DATE - req_time).days > 30 else 'benign'
    }


def make_deactivation_row(req_id, patient, phi, req_time, fulfilled=False):
    proc_time = iso(req_time + timedelta(days=random.randint(1, 25))) if fulfilled else ''
    return {
        'log_id': req_id,
        'principal': patient,
        'action': 'request_deactivation',
        'resource': phi,
        'lab_result': 0,
        'clinical_note': 0,
        'billing_info': 0,
        'request_timestamp': iso(req_time),
        'process_timestamp': proc_time,
        'label': 'violation_gdpr_art17' if not fulfilled and (AUDIT_DATE - req_time).days > 30 else 'benign'
    }


def generate_for_size(n, patient_phi_map, patients_with_doctor):
    rows = []
    violation_target = int(math.ceil(n * VIOLATION_RATE))
    benign_target = n - violation_target

    # Generate benign rows first
    for i in range(benign_target):
        # pick a patient that has a phi mapping
        patient = random.choice(list(patient_phi_map.keys()))
        phi = random.choice(patient_phi_map[patient])
        # choose a request timestamp within 30 days of audit date (benign)
        days_before = random.randint(1, 29)
        req_time = AUDIT_DATE - timedelta(days=days_before)
        # randomly choose access or deactivation
        if random.random() < 0.7:
            # access request fulfilled within 30 days
            row = make_access_row(f'req_ben_{i}', patient, phi, req_time, fulfilled=True,
                                  requested_attrs=random.sample(['lab_result','clinical_note','billing_info'], random.randint(1,3)))
        else:
            row = make_deactivation_row(f'req_ben_{i}', patient, phi, req_time, fulfilled=True)
        rows.append(row)

    # Violations: make sure each violates exactly one rule
    # Split violations roughly half access vs deactivation
    for j in range(violation_target):
        patient = random.choice(list(patients_with_doctor)) if patients_with_doctor else random.choice(list(patient_phi_map.keys()))
        phi = random.choice(patient_phi_map.get(patient, list(next(iter(patient_phi_map.values())))))
        # choose a request timestamp older than 30 days so it's eligible as violation
        days_before = random.randint(31, 200)
        req_time = AUDIT_DATE - timedelta(days=days_before)
        if j % 2 == 0:
            # create an access request that is unfulfilled (triggers gdpr_art15_access)
            requested_attrs = random.sample(['lab_result','clinical_note','billing_info'], random.randint(1,3))
            row = make_access_row(f'req_vio_{j}', patient, phi, req_time, fulfilled=False, requested_attrs=requested_attrs)
        else:
            # create a deactivation request that is unfulfilled (triggers gdpr_art17_erasure)
            row = make_deactivation_row(f'req_vio_{j}', patient, phi, req_time, fulfilled=False)
        rows.append(row)

    # Shuffle so violations are spread
    random.shuffle(rows)
    return rows


def main():
    random.seed(0)
    kb = load_kb()
    patient_phi_map = build_patient_phi_map(kb)
    if not patient_phi_map:
        raise SystemExit('No owns_phi_record facts found in KB; cannot generate patient request logs.')
    patients_with_doctor = build_patient_with_doctor_set(kb)

    for size in SIZES:
        rows = generate_for_size(size, patient_phi_map, patients_with_doctor)
        out_file = f"{OUT_DIR}/patient_request_{size}.csv"
        print(f"Writing {len(rows)} rows to {out_file} (target violations: {int(math.ceil(size*VIOLATION_RATE))})")
        # Write CSV with headers matching loader expectations
        with open(out_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['log_id','principal','action','resource','lab_result','clinical_note','billing_info','request_timestamp','process_timestamp','label'])
            writer.writeheader()
            for r in rows:
                writer.writerow(r)


if __name__ == '__main__':
    main()
