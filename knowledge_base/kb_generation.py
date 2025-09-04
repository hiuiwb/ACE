import pandas as pd
from faker import Faker
import random
from datetime import datetime, timedelta

# --- 1. CONFIGURATION ---
NUM_DOCTORS = 50
NUM_PATIENTS = 2000
NUM_BILLING_STAFF = 15
START_DATE = datetime(2025, 1, 1)

# Define principals with more realistic IDs
DOCTORS = [f'doc_{i}' for i in range(NUM_DOCTORS)]
PATIENTS = [f'pat_{i}' for i in range(NUM_PATIENTS)]
BILLING_STAFF = [f'bclerk_{i}' for i in range(NUM_BILLING_STAFF)] # Changed from 'billing_'
principals = DOCTORS + PATIENTS + BILLING_STAFF

# Define resources
PHI_RECORDS = {f'pat_{i}': f'phi_rec_{i}' for i in range(NUM_PATIENTS)}

# Special Principals for test scenarios
# This patient is guaranteed to have a research restriction for consistent testing
RESEARCH_RESTRICTED_PATIENT = "pat_25"

# Define all possible data processing purposes
PURPOSES = ['diagnosis', 'billing', 'research', 'marketing']

# --- 2. FACT GENERATION ---

def generate_core_facts():
    """
    Generates foundational, stateful facts for the hospital: roles, relationships,
    data ownership, resource types, and role-based permissions.
    """
    core_facts = []
    print("Generating core facts (roles, ownership, permissions)...")
    category_code = "CORE"

    # A. Roles for all principals
    for doc in DOCTORS: core_facts.append({"category": category_code, "fact_name": "has_role", "arg1": doc, "arg2": "doctor", "arg3": None})
    for pat in PATIENTS: core_facts.append({"category": category_code, "fact_name": "has_role", "arg1": pat, "arg2": "patient", "arg3": None})
    for staff in BILLING_STAFF: core_facts.append({"category": category_code, "fact_name": "has_role", "arg1": staff, "arg2": "billing_clerk", "arg3": None})

    # B. Relationships and Data Ownership
    for patient, record in PHI_RECORDS.items():
        doctor = random.choice(DOCTORS)
        core_facts.append({"category": category_code, "fact_name": "is_doctor_of", "arg1": doctor, "arg2": patient, "arg3": None})
        core_facts.append({"category": category_code, "fact_name": "owns_phi_record", "arg1": patient, "arg2": record, "arg3": None})
        core_facts.append({"category": category_code, "fact_name": "is_phi", "arg1": record, "arg2": None, "arg3": None})
        
    # C. Role Permissions (for 'Minimum Necessary' rule)
    # Note: we no longer generate per-record 'resource_type' facts here.
    # Permissions (which roles can access which attribute types) are still defined below.
    core_facts.append({"category": category_code, "fact_name": "role_can_access_type", "arg1": "doctor", "arg2": "clinical_note", "arg3": None})
    core_facts.append({"category": category_code, "fact_name": "role_can_access_type", "arg1": "doctor", "arg2": "lab_result", "arg3": None})
    core_facts.append({"category": category_code, "fact_name": "role_can_access_type", "arg1": "billing_clerk", "arg2": "billing_info", "arg3": None})
        
    return core_facts

def generate_consent_facts():
    """
    Generates a complete consent profile for every patient across all purposes.
    """
    consent_facts = []
    print("Generating personal consent facts for all purposes...")
    category_code = "CONSENT"
    
    for patient in PATIENTS:
        for purpose in PURPOSES:
            # Essential purposes are consented by default
            if purpose in ['diagnosis', 'billing']:
                consent_facts.append({"category": category_code, "fact_name": "has_unrestricted_status", "arg1": patient, "arg2": purpose, "arg3": None})
                continue

            # Handle the specific test case for research restriction
            if patient == RESEARCH_RESTRICTED_PATIENT and purpose == 'research':
                consent_facts.append({"category": category_code, "fact_name": "has_restriction", "arg1": patient, "arg2": "research", "arg3": None})
                continue
            
            # For optional purposes, generate random consent
            if random.random() < 0.7: # 70% of patients consent to optional purposes
                consent_facts.append({"category": category_code, "fact_name": "has_unrestricted_status", "arg1": patient, "arg2": purpose, "arg3": None})
            else:
                consent_facts.append({"category": category_code, "fact_name": "has_restriction", "arg1": patient, "arg2": purpose, "arg3": None})

    return consent_facts

# --- 3. MAIN EXECUTION ---
if __name__ == "__main__":
    Faker.seed(0)
    random.seed(0)
    
    # Generate facts from all categories
    all_facts = generate_core_facts() + generate_consent_facts()

    # Create a DataFrame
    kb_df = pd.DataFrame(all_facts)
    
    # Add a unique KB_id as the first column
    kb_df.insert(0, 'kb_id', range(1, len(kb_df) + 1))
    
    # Add default timestamps for facts
    kb_df['start_date'] = START_DATE.strftime('%Y-%m-%d')
    kb_df['end_date'] = (START_DATE + timedelta(days=365*2)).strftime('%Y-%m-%d')

    # Reorder columns for clarity
    kb_df = kb_df[['kb_id', 'category', 'fact_name', 'arg1', 'arg2', 'arg3', 'start_date', 'end_date']]

    # Save to CSV
    kb_df.to_csv("knowledge_base/knowledge_base.csv", index=False)

    print(f"\n--- Hospital Knowledge Base Generation Complete ---")
    print(f"Generated {len(kb_df)} facts across 2 categories and saved to 'knowledge_base.csv'.")
    print("KB now contains a complete consent profile for every patient across all purposes.")