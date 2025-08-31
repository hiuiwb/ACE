import pandas as pd
from faker import Faker
import random
from datetime import datetime, timedelta

# --- 1. CONFIGURATION ---
NUM_DOCTORS = 20
NUM_PATIENTS = 200
NUM_BILLING_STAFF = 5 # Added a new role for 'Minimum Necessary' rule
START_DATE = datetime(2025, 1, 1)

# Define principals
DOCTORS = [f'doc_{i}' for i in range(NUM_DOCTORS)]
PATIENTS = [f'pat_{i}' for i in range(NUM_PATIENTS)]
BILLING_STAFF = [f'billing_{i}' for i in range(NUM_BILLING_STAFF)]
principals = DOCTORS + PATIENTS + BILLING_STAFF

# Define resources
PHI_RECORDS = [f'phi_rec_{i}' for i in range(NUM_PATIENTS)]

# Special principals for test scenarios
DEACTIVATED_PATIENT = "pat_15"
RESTRICTED_PATIENT = "pat_25"

# --- 2. FACT GENERATION ---

def generate_hospital_facts():
    """Generates foundational facts for the hospital, including new resource types and permissions."""
    facts = []
    print("Generating core hospital facts...")
    
    # A. Roles for all principals
    for doc in DOCTORS: facts.append({"category": "CORE", "fact_name": "has_role", "arg1": doc, "arg2": "doctor", "arg3": None})
    for pat in PATIENTS: facts.append({"category": "CORE", "fact_name": "has_role", "arg1": pat, "arg2": "patient", "arg3": None})
    for staff in BILLING_STAFF: facts.append({"category": "CORE", "fact_name": "has_role", "arg1": staff, "arg2": "billing_clerk", "arg3": None})

    # B. Relationships and Data Ownership
    for i, patient in enumerate(PATIENTS):
        doctor = random.choice(DOCTORS)
        facts.append({"category": "CORE", "fact_name": "is_doctor_of", "arg1": doctor, "arg2": patient, "arg3": None})
        facts.append({"category": "CORE", "fact_name": "owns_phi_record", "arg1": patient, "arg2": PHI_RECORDS[i], "arg3": None})
        facts.append({"category": "CORE", "fact_name": "is_phi", "arg1": PHI_RECORDS[i], "arg2": None, "arg3": None})

    # --- ADDED SECTION ---
    # C. Resource Types and Role Permissions (for 'hipaa_min_necessary' rule)
    resource_types = ['clinical_note', 'lab_result', 'billing_info']
    for record in PHI_RECORDS:
        rtype = random.choice(resource_types)
        facts.append({"category": "CORE", "fact_name": "resource_type", "arg1": record, "arg2": rtype, "arg3": None})
    
    # Define which roles can access which types
    facts.append({"category": "CORE", "fact_name": "role_can_access_type", "arg1": "doctor", "arg2": "clinical_note", "arg3": None})
    facts.append({"category": "CORE", "fact_name": "role_can_access_type", "arg1": "doctor", "arg2": "lab_result", "arg3": None})
    facts.append({"category": "CORE", "fact_name": "role_can_access_type", "arg1": "billing_clerk", "arg2": "billing_info", "arg3": None})
    # --- END ADDED SECTION ---

    # D. Consent: Define restrictions
    for patient in PATIENTS:
        if patient == RESTRICTED_PATIENT:
            facts.append({"category": "CONSENT", "fact_name": "has_restriction", "arg1": patient, "arg2": "research", "arg3": None})
        else:
            facts.append({"category": "CONSENT", "fact_name": "has_unrestricted_status", "arg1": patient, "arg2": "research", "arg3": None})
            
    # E. Lifecycle: Create a deactivation request
    deactivation_date = datetime(2025, 6, 1)
    facts.append({"category": "LIFECYCLE", "fact_name": "deactivation_request", "arg1": DEACTIVATED_PATIENT, "arg2": deactivation_date.strftime('%Y-%m-%d'), "arg3": None})

    return facts

# --- 3. MAIN EXECUTION ---
if __name__ == "__main__":
    all_facts = generate_hospital_facts()
    kb_df = pd.DataFrame(all_facts)
    kb_df['start_date'] = START_DATE.strftime('%Y-%m-%d')
    kb_df['end_date'] = (START_DATE + timedelta(days=365*2)).strftime('%Y-%m-%d')
    kb_df = kb_df[['category', 'fact_name', 'arg1', 'arg2', 'arg3', 'start_date', 'end_date']]
    kb_df.to_csv("knowledge_base.csv", index=False)

    print(f"\n--- Hospital Knowledge Base Generation Complete ---")
    print(f"Generated {len(kb_df)} facts and saved to 'knowledge_base.csv'.")
    print("KB now includes 'resource_type' and 'role_can_access_type' facts for HIPAA Minimum Necessary rule.")