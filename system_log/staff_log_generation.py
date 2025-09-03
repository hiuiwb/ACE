import pandas as pd
from faker import Faker
import random
from datetime import datetime, timedelta

# --- 1. CONFIGURATION (with Personalization) ---
NUM_LOG_ENTRIES = 1000
VIOLATION_RATE = 0.05 # Target violation rate (e.g., 5% of staff actions will be violations)
START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2025, 8, 30)
# Entities
DOCTORS = [f'doc_{i}' for i in range(20)]
PATIENTS = [f'pat_{i}' for i in range(200)]
BILLING_STAFF = [f'billing_{i}' for i in range(5)]
PHI_RECORDS = {f'pat_{i}': f'phi_rec_{i}' for i in range(200)}
# Special Principals for scenarios
DEACTIVATED_PATIENT = "pat_15"
RESTRICTED_PATIENT = "pat_25"
UNAUTHORIZED_ACCESS_PATIENT = "pat_50"

# --- MAPPING from purpose to the attributes that can be legitimately accessed ---
PURPOSE_TO_ATTRIBUTES = {
    "diagnosis": ["clinical_note", "lab_result"],
    "billing": ["billing_info"],
    "research": ["clinical_note", "lab_result"],
    "marketing": ["billing_info"] # Added marketing purpose
}

def create_log_entry(log_id, principal, action, resource, purpose, timestamp, label, accessed_types):
    """Helper to create a single log entry dictionary."""
    return {
        "log_id": log_id, "principal": principal, "action": action, "resource": resource,
        "lab_result": 1 if 'lab_result' in accessed_types else 0,
        "clinical_note": 1 if 'clinical_note' in accessed_types else 0,
        "billing_info": 1 if 'billing_info' in accessed_types else 0,
        "purpose": purpose, "timestamp": timestamp.isoformat(), "label": label
    }

# --- 2. SCENARIO GENERATION ---
if __name__ == "__main__":
    Faker.seed(0)
    random.seed(0)
    violating_entries = []
    log_counter = 0

    print("Generating Hospital Staff Activity Log with specific violation scenarios...")

    # --- Generate guaranteed test cases first ---
    # Scenario 1: HIPAA Authorization Violation
    violating_entries.append(create_log_entry(
        f"log_{log_counter}", DOCTORS[0], "read_phi", PHI_RECORDS[UNAUTHORIZED_ACCESS_PATIENT],
        "diagnosis", END_DATE - timedelta(days=10), "violation_hipaa_auth", ['clinical_note']
    )); log_counter += 1

    # Scenario 2: HIPAA Minimum Necessary Violation
    # A billing clerk's purpose is 'billing', but they access a 'clinical_note'.
    violating_entries.append(create_log_entry(
        f"log_{log_counter}", random.choice(BILLING_STAFF), "read_phi", PHI_RECORDS[PATIENTS[60]],
        "billing", END_DATE - timedelta(days=15), "violation_hipaa_min_necessary", ['clinical_note', 'billing_info']
    )); log_counter += 1

    # Scenario 3: GDPR Art. 18 Restriction Violation
    # A doctor reads the record of the restricted patient for the 'research' purpose.
    violating_entries.append(create_log_entry(
        f"log_{log_counter}", random.choice(DOCTORS), "read_phi", PHI_RECORDS[RESTRICTED_PATIENT],
        "research", END_DATE - timedelta(days=20), "violation_gdpr_art18", PURPOSE_TO_ATTRIBUTES['research']
    )); log_counter += 1

    # Scenario 4: GDPR Art. 17 Erasure Violation
    violating_entries.append(create_log_entry(
        f"log_{log_counter}", random.choice(DOCTORS), "read_phi", PHI_RECORDS[DEACTIVATED_PATIENT],
        "billing", datetime(2025, 6, 1) + timedelta(days=45), "violation_gdpr_art17", PURPOSE_TO_ATTRIBUTES['billing']
    )); log_counter += 1

    # --- Generate other random violations to meet VIOLATION_RATE ---
    target_num_violations = int(NUM_LOG_ENTRIES * VIOLATION_RATE)
    remaining_violations_needed = target_num_violations - len(violating_entries)
    
    if remaining_violations_needed > 0:
        print(f"Generating {remaining_violations_needed} additional random violations...")
        for i in range(remaining_violations_needed):
            violating_doctor = random.choice(DOCTORS)
            violating_patient = random.choice([p for p in PATIENTS if p != violating_doctor])
            violating_entries.append(create_log_entry(
                f"log_{log_counter}", violating_doctor, "read_phi", PHI_RECORDS[violating_patient],
                "diagnosis", Faker().date_time_between(start_date=START_DATE, end_date=END_DATE),
                "violation_hipaa_auth", PURPOSE_TO_ATTRIBUTES['diagnosis']
            )); log_counter += 1

    # --- Generate Benign (Compliant) Traffic ---
    num_benign_entries = NUM_LOG_ENTRIES - len(violating_entries)
    print(f"Generating {num_benign_entries} benign staff log entries...")
    
    benign_entries = []
    patient_doctor_map = {patient: random.choice(DOCTORS) for patient in PATIENTS}
    for i in range(num_benign_entries):
        patient = random.choice([p for p in PATIENTS if p != RESTRICTED_PATIENT]) # Pick non-restricted patient
        doctor = patient_doctor_map.get(patient, random.choice(DOCTORS))
        record = PHI_RECORDS[patient]
        
        # Select a random valid purpose and get the corresponding legitimate attributes
        purpose = random.choice(list(PURPOSE_TO_ATTRIBUTES.keys()))
        accessed_types = PURPOSE_TO_ATTRIBUTES[purpose]
        
        benign_entries.append(create_log_entry(
            f"log_{log_counter}", doctor, "read_phi", record, purpose,
            Faker().date_time_between(start_date=START_DATE, end_date=END_DATE), "benign", accessed_types
        )); log_counter += 1

    # --- Finalize and Save ---
    all_log_entries = violating_entries + benign_entries
    log_df = pd.DataFrame(all_log_entries)
    log_df.sort_values(by="timestamp", inplace=True, ignore_index=True)
    log_df.to_csv("staff_activity_log.csv", index=False)

    print(f"\n--- Hospital Staff Log Generation Complete ---")
    print(f"Generated {len(log_df)} total log entries and saved to 'staff_activity_log.csv'.")

    # --- Summary of Log Features ---
    print("\n--- Summary of Generated Log ---")
    num_violations = len(violating_entries)
    actual_violation_rate = num_violations / len(log_df) if len(log_df) > 0 else 0
    
    print(f"Total Entries: {len(log_df)}")
    print(f"Benign Entries: {len(benign_entries)}")
    print(f"Violating Entries: {num_violations} (Actual Rate: {actual_violation_rate:.2%})")
    
    if num_violations > 0:
        print("\nViolation Breakdown by Type:")
        violations_df = pd.DataFrame(violating_entries)
        print(violations_df['label'].value_counts().to_string())

