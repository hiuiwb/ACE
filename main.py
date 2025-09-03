import pandas as pd
import data_loader
from auditor import Auditor
from scorer import ComplianceScorer

# --- 1. CONFIGURATION ---
POLICY_FILE = "policy/policy.pl"
KB_FILE = "knowledge_base/knowledge_base.csv"
STAFF_LOG_FILE = "system_log/staff_activity_log.csv"
PATIENT_LOG_FILE = "system_log/patient_request_log.csv"
AUDIT_DATE = "2025-08-31"

# Scoring model parameters
SCORING_WEIGHTS = {'C': 0.4, 'V': 0.3, 'T': 0.2, 'B': 0.1}
NORMALIZATION_CONSTANTS = {'V': 0.1, 'T': 0.05, 'B': 0.5}
# Rule criticalities now match the 5 rules in the final policy.pl
RULE_CRITICALITIES = {
    'hipaa_auth': 0.8,
    'hipaa_min_necessary': 0.7,
    'gdpr_art18_restriction': 0.8,
    'gdpr_art17_erasure': 0.9,
    'gdpr_art15_access': 0.7
}

# --- 2. Pre-processing function for patient request log ---
def preprocess_log_to_generate_facts(patient_log_df):
    """
    Scans the patient request log to find TIMELY fulfilled requests and
    returns a DataFrame of corresponding facts. A request is only considered
    fulfilled if the processing happened within the 30-day time limit.
    """
    print("Pre-processing patient log to identify fulfilled requests...")
    fulfilled_facts = []
    
    # Create mappings from request_id to request details for efficient lookup
    requests_df = patient_log_df[patient_log_df['action'].isin(['request_access', 'request_deactivation'])].copy()
    requests_df.set_index('log_id', inplace=True)
    
    fulfillments_df = patient_log_df[patient_log_df['process_timestamp'].notna()]
    
    for _, req in fulfillments_df.iterrows():
        request_id = req['log_id']
        # Check if the fulfillment was timely
        time_delta = req['process_timestamp'] - req['request_timestamp']
        
        if time_delta.days <= 30:
            action = req['action']
            if action == 'request_access':
                fulfilled_facts.append({"fact_name": "request_fulfilled", "arg1": request_id, "arg2": None, "arg3": None})
            elif action == 'request_deactivation':
                fulfilled_facts.append({"fact_name": "deactivation_fulfilled", "arg1": request_id, "arg2": None, "arg3": None})
    
    if fulfilled_facts:
        print(f"Found and generated {len(fulfilled_facts)} timely fulfillment facts.")
        return pd.DataFrame(fulfilled_facts)
    else:
        print("No timely fulfillment events found in patient log.")
        return pd.DataFrame()

# --- 3. Main orchestration script ---
def main():
    # --- Load Data and Print Summary ---
    kb_df = data_loader.load_knowledge_base(KB_FILE)
    staff_log_df = data_loader.load_staff_log(STAFF_LOG_FILE)
    patient_log_df = data_loader.load_patient_log(PATIENT_LOG_FILE)
    
    print("\n--- DATA LOADING SUMMARY ---")
    print(f"Knowledge Base: {len(kb_df)} facts")
    print("\nStaff Activity Log:")
    print(staff_log_df['action'].value_counts().to_string())
    print("\nPatient Request Log:")
    print(patient_log_df['action'].value_counts().to_string())

    # --- Pre-processing Step ---
    derived_facts_df = preprocess_log_to_generate_facts(patient_log_df)
    if not derived_facts_df.empty:
        kb_df = pd.concat([kb_df, derived_facts_df], ignore_index=True)

    # --- Initialize and Run the Audit ---
    ace_auditor = Auditor(POLICY_FILE)
    ace_auditor.load_kb_facts(kb_df)
    
    # Audit both logs and combine the results
    staff_violations = ace_auditor.run_audit(staff_log_df, AUDIT_DATE)
    patient_violations = ace_auditor.run_audit(patient_log_df, AUDIT_DATE)
    all_detected_violations = staff_violations + patient_violations

    # --- Initialize the Scorer ---
    scorer = ComplianceScorer(SCORING_WEIGHTS, NORMALIZATION_CONSTANTS, RULE_CRITICALITIES)

    # --- Summarize Violations and Print Results ---
    violations_df = pd.DataFrame(all_detected_violations) if all_detected_violations else pd.DataFrame()
    
    print("\n--- OVERALL AUDIT SUMMARY ---")
    if violations_df.empty:
        print("Congratulations! No compliance violations were detected.")
    else:
        num_violators = violations_df['Principal'].nunique()
        print(f"Total violations detected: {len(violations_df)}")
        print(f"Number of unique violators: {num_violators}")
        print("\nViolation Breakdown by Rule:")
        print(violations_df['RuleID'].value_counts().to_string())

    print("\n--- DETAILED SCORE ANALYSIS FOR VIOLATORS ---")
    
    principals_to_evaluate = sorted(list(violations_df['Principal'].unique())) if not violations_df.empty else []
    
    if not principals_to_evaluate:
        print("No violators to analyze.")
    else:
        for principal in principals_to_evaluate:
            print(f"\n--- Evaluating Principal: {principal} ---")
            
            final_score = scorer.calculate_final_score(all_detected_violations, principal_id=principal)
            print(f"Final Compliance Score: {final_score:.4f}")
            
            print("Violation Instances:")
            principal_violations = violations_df[violations_df['Principal'] == principal]
            print(principal_violations['RuleID'].value_counts().to_string())

if __name__ == "__main__":
    main()

