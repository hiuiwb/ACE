#!/usr/bin/env python3
"""Generate staff activity logs of various sizes using the knowledge base.

Creates CSVs in the system_log/ directory named staff_activity_<N>.csv.
Each file contains a mix of benign and violating entries; violation rate is configurable (default 5%).

This script uses the KB at knowledge_base/knowledge_base.csv to pick principals,
PHI records, and consent/role facts so violations are realistic.
"""
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd


OUT_DIR = Path('system_log')
OUT_DIR.mkdir(exist_ok=True)

KB_PATH = Path('knowledge_base/knowledge_base.csv')

SIZES = [100, 1000, 5000, 10000, 50000]
VIOLATION_RATE = 0.05

START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2025, 8, 30)

# Purpose to attributes mapping (same as project conventions)
PURPOSE_TO_ATTRIBUTES = {
    'diagnosis': ['clinical_note', 'lab_result'],
    'billing': ['billing_info'],
    'research': ['clinical_note', 'lab_result'],
    'marketing': ['billing_info']
}


def load_kb(kb_path=KB_PATH):
    df = pd.read_csv(kb_path)
    return df


def extract_entities(kb_df):
    doctors = kb_df[(kb_df.fact_name == 'has_role') & (kb_df.arg2 == 'doctor')]['arg1'].unique().tolist()
    billing = kb_df[(kb_df.fact_name == 'has_role') & (kb_df.arg2 == 'billing_clerk')]['arg1'].unique().tolist()
    patients = kb_df[(kb_df.fact_name == 'has_role') & (kb_df.arg2 == 'patient')]['arg1'].unique().tolist()
    owns = kb_df[kb_df.fact_name == 'owns_phi_record'][['arg1','arg2']].values.tolist()
    # map patient -> phi
    phi_map = {p: r for (p, r) in owns}
    # list of phi records
    phi_records = list(phi_map.values())
    # restrictions for gdpr_art18: find (patient,purpose) with has_restriction
    restricted = kb_df[kb_df.fact_name == 'has_restriction'][['arg1','arg2']].values.tolist()
    restricted_map = {}
    for p, purpose in restricted:
        restricted_map.setdefault(p, []).append(purpose)
    # build patient -> assigned doctor mapping from is_doctor_of facts
    doctor_assignments = kb_df[kb_df.fact_name == 'is_doctor_of'][['arg1','arg2']].values.tolist()
    patient_to_doctor = {patient: doctor for (doctor, patient) in doctor_assignments}
    # build patient -> unrestricted purposes mapping
    unrestricted = kb_df[kb_df.fact_name == 'has_unrestricted_status'][['arg1','arg2']].values.tolist()
    unrestricted_map = {}
    for p, purpose in unrestricted:
        unrestricted_map.setdefault(p, []).append(purpose)
    # build role -> allowed attribute map from role_can_access_type facts
    role_access = {}
    access_facts = kb_df[kb_df.fact_name == 'role_can_access_type'][['arg1','arg2']].values.tolist()
    for role, attr in access_facts:
        role_access.setdefault(role, []).append(attr)
    return doctors, billing, patients, phi_map, phi_records, restricted_map, patient_to_doctor, unrestricted_map, role_access


def rand_timestamp(start=START_DATE, end=END_DATE):
    delta = end - start
    sec = random.randint(0, int(delta.total_seconds()))
    ts = start + timedelta(seconds=sec)
    return ts.strftime('%Y-%m-%dT%H:%M:%S')


def make_benign_entry(log_id, doctors, billing, patients, phi_map, patient_to_doctor, unrestricted_map, role_access):
    # choose a doctor and their patient, or a billing clerk for billing purpose
    if random.random() < 0.8:
        # doctor legitimate read
        patient = random.choice(list(phi_map.keys()))
        # choose the assigned doctor for this patient when available
        doctor = patient_to_doctor.get(patient, None)
        if doctor is None:
            doctor = random.choice(doctors) if doctors else 'doc_0'
        record = phi_map.get(patient, random.choice(list(phi_map.values())))

        # choose a purpose that the patient has allowed when possible
        allowed = unrestricted_map.get(patient)
        if allowed:
            purpose = random.choice(allowed)
        else:
            purpose = random.choice(['diagnosis','research'])

        attrs = PURPOSE_TO_ATTRIBUTES[purpose]
        # determine allowed attributes for this principal's role
        role = 'doctor' if str(doctor).startswith('doc_') else ('billing_clerk' if str(doctor).startswith('bclerk') else None)
        allowed_attrs = role_access.get(role, []) if role else []
        # set attributes only if allowed by role and purpose
        lab = 1 if ('lab_result' in attrs and 'lab_result' in allowed_attrs and random.random() < 0.8) else 0
        clin = 1 if ('clinical_note' in attrs and 'clinical_note' in allowed_attrs and random.random() < 0.8) else 0
        bill = 1 if ('billing_info' in attrs and 'billing_info' in allowed_attrs and random.random() < 0.05) else 0
        ts = rand_timestamp()
        label = 'benign'
        return {
            'log_id': log_id, 'principal': doctor, 'action': 'read_phi', 'resource': record,
            'lab_result': lab, 'clinical_note': clin, 'billing_info': bill, 'purpose': purpose, 'timestamp': ts, 'label': label
        }
    else:
        # billing clerk reading billing info
        clerk = random.choice(billing) if billing else 'bclerk_0'
        patient = random.choice(list(phi_map.keys()))
        record = phi_map.get(patient, random.choice(list(phi_map.values())))
        purpose = 'billing'
        # billing clerks should only access billing_info
        lab = 0
        clin = 0
        bill = 1
        ts = rand_timestamp()
        return {
            'log_id': log_id, 'principal': clerk, 'action': 'read_phi', 'resource': record,
            'lab_result': lab, 'clinical_note': clin, 'billing_info': bill, 'purpose': purpose, 'timestamp': ts, 'label': 'benign'
        }


def make_violation_entry(log_id, doctors, billing, patients, phi_map, restricted_map, violation_type, patient_to_doctor, unrestricted_map, role_access):
    # Construct entries to trigger exactly one rule
    if violation_type == 'hipaa_auth':
        # doctor reads a PHI record not belonging to their patient
        # pick a doctor and a PHI record owned by a patient that is not theirs
        # pick a patient and then pick a doctor who is NOT the assigned doctor
        patient = random.choice(list(phi_map.keys()))
        assigned = patient_to_doctor.get(patient)
        other_doctors = [d for d in doctors if d != assigned]
        doctor = random.choice(other_doctors) if other_doctors else (random.choice(doctors) if doctors else 'doc_0')
        record = phi_map[patient]
        # pick a purpose that is NOT restricted for this patient to avoid GDPR overlap
        candidate_purposes = [p for p in PURPOSE_TO_ATTRIBUTES.keys() if p not in restricted_map.get(patient, [])]
        if not candidate_purposes:
            purpose = 'diagnosis'
        else:
            purpose = random.choice(candidate_purposes)
        # choose a single attribute allowed for doctors for this purpose (avoid multiple attrs)
        doctor_allowed = role_access.get('doctor', [])
        possible_attrs = [a for a in PURPOSE_TO_ATTRIBUTES.get(purpose, []) if a in doctor_allowed]
        # default to clinical_note if nothing lines up
        chosen_attr = possible_attrs[0] if possible_attrs else ('clinical_note')
        lab = 1 if chosen_attr == 'lab_result' else 0
        clin = 1 if chosen_attr == 'clinical_note' else 0
        bill = 1 if chosen_attr == 'billing_info' else 0
        ts = rand_timestamp()
        return {
            'log_id': log_id, 'principal': doctor, 'action': 'read_phi', 'resource': record,
            'lab_result': lab, 'clinical_note': clin, 'billing_info': bill, 'purpose': purpose, 'timestamp': ts, 'label': 'violation_hipaa_auth'
        }
    elif violation_type == 'hipaa_min_necessary':
        # billing clerk reads clinical_note or lab_result (not allowed)
        clerk = random.choice(billing) if billing else 'bclerk_0'
        patient = random.choice(list(phi_map.keys()))
        record = phi_map[patient]
        # choose purpose billing but attributes clinical_note or lab_result flagged
        purpose = 'billing'
        # pick exactly one disallowed attribute (clinical_note or lab_result)
        if random.random() < 0.5:
            lab = 1; clin = 0
        else:
            lab = 0; clin = 1
        bill = 0
        ts = rand_timestamp()
        return {
            'log_id': log_id, 'principal': clerk, 'action': 'read_phi', 'resource': record,
            'lab_result': lab, 'clinical_note': clin, 'billing_info': bill, 'purpose': purpose, 'timestamp': ts, 'label': 'violation_hipaa_min_necessary'
        }
    elif violation_type == 'gdpr_art18_restriction':
        # choose a patient that has a restriction for a purpose and use that purpose
        if restricted_map:
            patient = random.choice(list(restricted_map.keys()))
            # pick a restricted purpose for this patient
            purposes = restricted_map.get(patient, [])
            purpose = random.choice(purposes) if purposes else random.choice(list(PURPOSE_TO_ATTRIBUTES.keys()))
            record = phi_map.get(patient, random.choice(list(phi_map.values())))
            purpose_attrs = PURPOSE_TO_ATTRIBUTES.get(purpose, [])
            # prefer the assigned doctor but choose any principal whose role allows at least one of the purpose attributes
            candidates = []
            assigned = patient_to_doctor.get(patient)
            if assigned:
                candidates.append(assigned)
            # include billing clerks as likely principals for billing-related attrs
            candidates.extend(billing)
            principal = None
            chosen_attr = None
            for cand in candidates:
                role = 'doctor' if str(cand).startswith('doc_') else ('billing_clerk' if str(cand).startswith('bclerk') else None)
                allowed_attrs = role_access.get(role, []) if role else []
                possible = [a for a in purpose_attrs if a in allowed_attrs]
                if possible:
                    principal = cand
                    chosen_attr = random.choice(possible)
                    break
            # fallback: if no candidate found, pick a principal randomly and pick the first purpose attr (may cause overlap)
            if principal is None:
                principal = patient_to_doctor.get(patient) or (random.choice(doctors + billing) if (doctors + billing) else 'doc_0')
                chosen_attr = purpose_attrs[0] if purpose_attrs else 'clinical_note'
            lab = 1 if chosen_attr == 'lab_result' else 0
            clin = 1 if chosen_attr == 'clinical_note' else 0
            bill = 1 if chosen_attr == 'billing_info' else 0
            ts = rand_timestamp()
            return {
                'log_id': log_id, 'principal': principal, 'action': 'read_phi', 'resource': record,
                'lab_result': lab, 'clinical_note': clin, 'billing_info': bill, 'purpose': purpose, 'timestamp': ts, 'label': 'violation_gdpr_art18'
            }
        else:
            # fallback to a hipaa_auth if no restricted entries exist
            return make_violation_entry(log_id, doctors, billing, patients, phi_map, restricted_map, 'hipaa_auth', patient_to_doctor, unrestricted_map)


def generate_for_size(n, doctors, billing, patients, phi_map, phi_records, restricted_map, out_path, patient_to_doctor, unrestricted_map, role_access):
    rows = []
    num_viol = max(1, int(n * VIOLATION_RATE))
    num_benign = n - num_viol
    # prepare violation types roughly equally split
    viol_types = ['hipaa_auth', 'hipaa_min_necessary', 'gdpr_art18_restriction']
    viol_list = []
    for i in range(num_viol):
        viol_list.append(random.choice(viol_types))
    # shuffle slots
    items = []
    for i in range(num_benign):
        items.append(('benign', None))
    for v in viol_list:
        items.append(('viol', v))
    random.shuffle(items)

    # generate rows
    for idx, (kind, vtype) in enumerate(items):
        lid = f'log_{idx}'
        if kind == 'benign':
            entry = make_benign_entry(lid, doctors, billing, patients, phi_map, patient_to_doctor, unrestricted_map, role_access)
        else:
            entry = make_violation_entry(lid, doctors, billing, patients, phi_map, restricted_map, vtype, patient_to_doctor, unrestricted_map, role_access)
        rows.append(entry)

    # write CSV
    cols = ['log_id','principal','action','resource','lab_result','clinical_note','billing_info','purpose','timestamp','label']
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f'Wrote {len(rows)} rows to {out_path}')


def main():
    random.seed(0)
    kb = load_kb()
    doctors, billing, patients, phi_map, phi_records, restricted_map, patient_to_doctor, unrestricted_map, role_access = extract_entities(kb)
    for n in SIZES:
        out_file = OUT_DIR / f'staff_activity_{n}.csv'
        generate_for_size(n, doctors, billing, patients, phi_map, phi_records, restricted_map, out_file, patient_to_doctor, unrestricted_map, role_access)


if __name__ == '__main__':
    main()
