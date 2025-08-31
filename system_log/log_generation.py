import pandas as pd
from faker import Faker
import random
import numpy as np
from datetime import datetime, timedelta

# --- 1. CONFIGURATION ---
NUM_LOG_ENTRIES = 1000
START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2025, 8, 30)
# Entities
DOCTORS = [f'doc_{i}' for i in range(20)]
PATIENTS = [f'pat_{i}' for i in range(200)]
PHI_RECORDS = [f'phi_rec_{i}' for i in range(200)]
# Special Principals
DEACTIVATED_PATIENT = "pat_15"
RESTRICTED_PATIENT = "pat_25"
UNFULFILLED_ACCESS_PATIENT = "pat_35"
FULFILLED_ACCESS_PATIENT = "pat_45"
# Resource types for 'Breadth'
RESOURCE_TYPES = {rec: random.choice(['lab_result', 'clinical_note', 'billing_info']) for rec in PHI_RECORDS}

# --- 2. VIOLATION SCENARIO GENERATORS ---

def generate_single_trigger_violations():
    """Generates one of each of the four main violation types."""
    entries = []
    # A. Auth Violation: doc_0 reads a record of pat_50 (not their patient)
    entries.append({"timestamp": (END_DATE - timedelta(days=10)).isoformat(), "principal": DOCTORS[0], "action": "read_phi", "resource": PHI_RECORDS[50], "purpose": "diagnosis", "request_id": f"evt_auth_single"})
    # B. Restriction Violation: Reading PHI for 'research' from the restricted patient
    entries.append({"timestamp": (END_DATE - timedelta(days=20)).isoformat(), "principal": DOCTORS[1], "action": "read_phi", "resource": PHI_RECORDS[25], "purpose": "research", "request_id": f"evt_restrict_single"})
    # C. Erasure Violation: Accessing data of a deactivated patient
    entries.append({"timestamp": (datetime(2025, 6, 1) + timedelta(days=45)).isoformat(), "principal": DOCTORS[2], "action": "read_phi", "resource": PHI_RECORDS[15], "purpose": "billing", "request_id": f"evt_erasure_single"})
    # D. Access Violation: An unfulfilled request
    req_date_bad = END_DATE - timedelta(days=40)
    entries.append({"timestamp": req_date_bad.isoformat(), "principal": UNFULFILLED_ACCESS_PATIENT, "action": "request_access", "resource": PHI_RECORDS[35], "purpose": None, "request_id": "acc_02_bad"})
    return entries

def generate_high_volume_violation(violator='doc_1', num_events=50):
    """Generates a burst of auth violations to test Volume."""
    entries = []
    start_time = END_DATE - timedelta(days=5)
    # This doctor reads 50 different records of patients not assigned to them
    for i in range(num_events):
        patient_index = 100 + i # Pick a range of patients not assigned to doc_1
        timestamp = start_time + timedelta(minutes=i)
        entries.append({"timestamp": timestamp.isoformat(), "principal": violator, "action": "read_phi", "resource": PHI_RECORDS[patient_index], "purpose": "diagnosis", "request_id": f"evt_vol_{i}"})
    return entries

def generate_high_duration_violation(violator='doc_2', num_events=10, days_spread=90):
    """Generates auth violations spread over time to test Duration."""
    entries = []
    time_points = np.linspace(0, days_spread, num_events)
    for i, days_ago in enumerate(time_points):
        patient_index = 150 + i
        timestamp = END_DATE - timedelta(days=int(days_ago))
        entries.append({"timestamp": timestamp.isoformat(), "principal": violator, "action": "read_phi", "resource": PHI_RECORDS[patient_index], "purpose": "diagnosis", "request_id": f"evt_dur_{i}"})
    return entries

def generate_high_breadth_violation(violator='doc_3', num_types=3):
    """Generates auth violations across different resource types to test Breadth."""
    entries = []
    resources_by_type = {rtype: [] for rtype in set(RESOURCE_TYPES.values())}
    for res, rtype in RESOURCE_TYPES.items(): resources_by_type[rtype].append(res)
    
    timestamp = END_DATE - timedelta(days=2)
    for i, rtype in enumerate(list(resources_by_type.keys())[:num_types]):
        if resources_by_type[rtype]:
            patient_index = 180 + i
            entries.append({"timestamp": (timestamp + timedelta(minutes=i)).isoformat(), "principal": violator, "action": "read_phi", "resource": PHI_RECORDS[patient_index], "purpose": "diagnosis", "request_id": f"evt_breadth_{i}"})
    return entries


# --- 3. MAIN EXECUTION ---
if __name__ == "__main__":
    Faker.seed(0)
    random.seed(0)
    all_log_entries = []
    print("Generating hospital log with patterns for all severity dimensions...")

    # --- Inject all violation scenarios ---
    all_log_entries.extend(generate_single_trigger_violations())
    all_log_entries.extend(generate_high_volume_violation())
    all_log_entries.extend(generate_high_duration_violation())
    all_log_entries.extend(generate_high_breadth_violation())
    
    # --- Generate compliant access request ---
    req_date_ok = END_DATE - timedelta(days=50)
    ful_date_ok = req_date_ok + timedelta(days=20)
    all_log_entries.append({"timestamp": req_date_ok.isoformat(), "principal": FULFILLED_ACCESS_PATIENT, "action": "request_access", "resource": PHI_RECORDS[45], "purpose": None, "request_id": "acc_01_ok"})
    all_log_entries.append({"timestamp": ful_date_ok.isoformat(), "principal": "hospital_system", "action": "provide_data", "resource": None, "purpose": None, "request_id": "acc_01_ok"})

    # --- Generate Benign Traffic ---
    num_benign_entries = NUM_LOG_ENTRIES - len(all_log_entries)
    print(f"Generating {num_benign_entries} benign log entries...")
    
    # In benign traffic, doctors only read records of their assigned patients
    patient_doctor_map = {patient: random.choice(DOCTORS) for patient in PATIENTS}
    for i in range(num_benign_entries):
        patient_idx = random.randint(0, len(PATIENTS)-1)
        patient = PATIENTS[patient_idx]
        doctor = patient_doctor_map[patient] # Get the correctly assigned doctor
        record = PHI_RECORDS[patient_idx]
        all_log_entries.append({"timestamp": Faker().date_time_between(start_date=START_DATE, end_date=END_DATE).isoformat(), "principal": doctor, "action": "read_phi", "resource": record, "purpose": "diagnosis", "request_id": f"evt_benign_{i}"})
        
    # --- Finalize and Save ---
    log_df = pd.DataFrame(all_log_entries)
    log_df.sort_values(by="timestamp", inplace=True, ignore_index=True)
    log_df.to_csv("system_log.csv", index=False)
    
    print(f"\n--- Hospital System Log Generation Complete ---")
    print(f"Generated {len(log_df)} total log entries.")
    print("Log now contains specific patterns to test Criticality, Volume, Duration, and Breadth.")