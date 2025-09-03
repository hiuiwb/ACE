import pandas as pd
from faker import Faker
import random
from datetime import datetime, timedelta

# --- 1. CONFIGURATION (with Personalization) ---
NUM_REQUESTS = 50
VIOLATION_RATE = 0.5 # Target violation rate (e.g., 50% of requests will be fulfilled late)
START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2025, 8, 30)
# Entities
PATIENTS = [f'pat_{i}' for i in range(200)]
PHI_RECORDS = {f'pat_{i}': f'phi_rec_{i}' for i in range(200)}
# Special Principals
UNFULFILLED_ACCESS_PATIENT = "pat_35"
FULFILLED_ACCESS_PATIENT = "pat_45"
DEACTIVATED_PATIENT_REQUEST = "pat_15" # Patient who will request deactivation

# The types of data a patient can request access to
REQUESTABLE_ATTRIBUTES = ['lab_result', 'clinical_note', 'billing_info']

def create_request_entry(log_id, principal, action, resource, req_time, proc_time, label, accessed_types=[]):
    """Helper to create a patient request log entry with specific attributes."""
    return {
        "log_id": log_id, "principal": principal, "action": action, "resource": resource,
        "lab_result": 1 if 'lab_result' in accessed_types else 0,
        "clinical_note": 1 if 'clinical_note' in accessed_types else 0,
        "billing_info": 1 if 'billing_info' in accessed_types else 0,
        "request_timestamp": req_time.isoformat(),
        "process_timestamp": proc_time.isoformat() if proc_time else None,
        "label": label
    }

# --- 2. SCENARIO GENERATION ---
if __name__ == "__main__":
    Faker.seed(0)
    random.seed(0)
    all_request_entries = []
    log_counter = 0

    print("Generating Patient Request Log with specific scenarios...")

    # --- Generate guaranteed test cases first ---
    # Scenario 1: GDPR Art. 15 Compliant Access Request
    req_time_ok = END_DATE - timedelta(days=50)
    proc_time_ok = req_time_ok + timedelta(days=20) # Within 30 days
    all_request_entries.append(create_request_entry(
        f"req_{log_counter}", FULFILLED_ACCESS_PATIENT, "request_access", PHI_RECORDS[FULFILLED_ACCESS_PATIENT],
        req_time_ok, proc_time_ok, "benign", ['clinical_note', 'billing_info'] # Patient requests two types
    )); log_counter += 1

    # Scenario 2: GDPR Art. 15 Non-Compliant Access Request (Violation)
    req_time_bad = END_DATE - timedelta(days=40)
    all_request_entries.append(create_request_entry(
        f"req_{log_counter}", UNFULFILLED_ACCESS_PATIENT, "request_access", PHI_RECORDS[UNFULFILLED_ACCESS_PATIENT],
        req_time_bad, None, "violation_gdpr_art15", ['lab_result'] # Patient requests one type
    )); log_counter += 1
    
    # Scenario 3: GDPR Art. 17 Deactivation Request (will be fulfilled late, causing violation)
    req_time_deact = datetime(2025, 6, 1)
    proc_time_deact_late = req_time_deact + timedelta(days=35)
    all_request_entries.append(create_request_entry(
        f"req_{log_counter}", DEACTIVATED_PATIENT_REQUEST, "request_deactivation", PHI_RECORDS[DEACTIVATED_PATIENT_REQUEST],
        req_time_deact, proc_time_deact_late, "violation_gdpr_art17"
    )); log_counter += 1

    # --- Generate other random requests ---
    num_other_requests = NUM_REQUESTS - len(all_request_entries)
    print(f"Generating {num_other_requests} other random request entries...")
    for i in range(num_other_requests):
        patient = random.choice(PATIENTS)
        req_time = Faker().date_time_between(start_date=START_DATE, end_date=END_DATE - timedelta(days=40))
        
        # Randomly choose which attributes the patient requests
        num_attrs_requested = random.randint(1, len(REQUESTABLE_ATTRIBUTES))
        requested_attrs = random.sample(REQUESTABLE_ATTRIBUTES, num_attrs_requested)
        
        # Use VIOLATION_RATE to determine if the request is fulfilled late
        if random.random() < VIOLATION_RATE:
            proc_time = req_time + timedelta(days=random.randint(31, 60))
            label = "violation_gdpr_art15"
        else:
            proc_time = req_time + timedelta(days=random.randint(1, 29))
            label = "benign"
        
        all_request_entries.append(create_request_entry(
            f"req_{log_counter}", patient, "request_access", PHI_RECORDS[patient],
            req_time, proc_time, label, requested_attrs
        )); log_counter += 1

    # --- Finalize and Save ---
    log_df = pd.DataFrame(all_request_entries)
    log_df.sort_values(by="request_timestamp", inplace=True, ignore_index=True)
    log_df.to_csv("patient_request_log.csv", index=False)
    
    print(f"\n--- Patient Request Log Generation Complete ---")
    print(f"Generated {len(log_df)} total request entries and saved to 'patient_request_log.csv'.")

    # --- Summary of Log Features ---
    print("\n--- Summary of Generated Log ---")
    num_violations = len(log_df[log_df['label'] != 'benign'])
    actual_violation_rate = num_violations / len(log_df) if len(log_df) > 0 else 0
    
    print(f"Total Entries: {len(log_df)}")
    print(f"Benign Entries: {len(log_df[log_df['label'] == 'benign'])}")
    print(f"Violating Entries: {num_violations} (Actual Rate: {actual_violation_rate:.2%})")
    
    if num_violations > 0:
        print("\nViolation Breakdown by Type:")
        print(log_df['label'].value_counts().to_string())

