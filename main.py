import pandas as pd
import data_loader
from auditor import Auditor
from scorer import ComplianceScorer

# --- CONFIGURATION ---
POLICY_FILE = "policy/policy.pl"
KB_FILE = "knowledge_base/knowledge_base.csv"
LOG_FILE = "system_log/system_log.csv"
AUDIT_DATE = "2025-08-31"

# Scoring model parameters
SCORING_WEIGHTS = {'C': 0.4, 'V': 0.3, 'T': 0.2, 'B': 0.1}
NORMALIZATION_CONSTANTS = {'V': 0.1, 'T': 0.05, 'B': 0.5}
RULE_CRITICALITIES = {
    'hipaa_access_control': 0.8,
    'gdpr_art18': 0.8,
    'gdpr_art17': 0.9,
    'gdpr_art15': 0.7
}

# --- THIS IS THE MISSING FUNCTION ---
def preprocess_log_to_generate_facts(log_df):
    """
    Scans the log for fulfillment events and returns a DataFrame of facts
    to be added to the Knowledge Base.
    """
    print("Pre-processing log to identify fulfilled requests...")
    fulfilled_facts = []
    
    # Find fulfilled access requests
    fulfilled_access_ids = set(log_df[log_df['action'] == 'provide_data']['request_id'])
    for req_id in fulfilled_access_ids:
        fulfilled_facts.append({"fact_name": "request_fulfilled", "arg1": req_id, "arg2": None, "arg3": None})
        
    # Find fulfilled deactivation requests
    fulfilled_deact_ids = set(log_df[log_df['action'] == 'fulfill_deactivation']['request_id'])
    for req_id in fulfilled_deact_ids:
        fulfilled_facts.append({"fact_name": "deactivation_fulfilled", "arg1": req_id, "arg2": None, "arg3": None})
        
    if fulfilled_facts:
        print(f"Found and generated {len(fulfilled_facts)} fulfillment facts.")
        return pd.DataFrame(fulfilled_facts)
    else:
        print("No fulfillment events found in log.")
        return pd.DataFrame()

def main():
    """Main orchestration script for the compliance evaluation."""
    kb_df = data_loader.load_knowledge_base(KB_FILE)
    log_df = data_loader.load_system_log(LOG_FILE)

    # --- Pre-processing Step ---
    derived_facts_df = preprocess_log_to_generate_facts(log_df)
    if not derived_facts_df.empty:
        # Add the derived facts to the main Knowledge Base
        kb_df = pd.concat([kb_df, derived_facts_df], ignore_index=True)

    # Initialize and run the audit
    ace_auditor = Auditor(POLICY_FILE)
    ace_auditor.load_kb_facts(kb_df)
    all_detected_violations = ace_auditor.run_full_audit(log_df, AUDIT_DATE)

    # Initialize the scorer
    scorer = ComplianceScorer(SCORING_WEIGHTS, NORMALIZATION_CONSTANTS, RULE_CRITICALITIES)

    # --- Summarize and print results ---
    violations_df = pd.DataFrame(all_detected_violations) if all_detected_violations else pd.DataFrame()
    print("\n--- DETAILED VIOLATION SUMMARY & SCORES ---")
    
    # Evaluate all unique principals who had a violation detected
    principals_to_evaluate = sorted(list(violations_df['Principal'].unique())) if not violations_df.empty else []
    
    for principal in principals_to_evaluate:
        print(f"\n--- Evaluating Principal: {principal} ---")
        principal_violations = violations_df[violations_df['Principal'] == principal]
        print("Detected Violations:")
        print(principal_violations[['RuleID', 'ObjectID', 'timestamp']].to_string(index=False))

        final_score = scorer.calculate_final_score(all_detected_violations, principal_id=principal)
        print(f"Final Compliance Score: {final_score:.4f}")

if __name__ == "__main__":
    main()