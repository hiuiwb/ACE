import pandas as pd
from pyswip import Prolog

class Auditor:
    """
    An engine for detecting compliance violations using a Prolog policy.
    It orchestrates the interaction between Python data and the Prolog logic engine.
    """
    def __init__(self, policy_file="policy.pl"):
        """Initializes the Prolog engine and loads the policy rules."""
        self.prolog = Prolog()
        self.prolog.consult(policy_file)
        print(f"Auditor initialized with policy '{policy_file}'.")

    def _format_fact(self, row):
        """Formats a row from the KB DataFrame into a Prolog fact string."""
        # Filters out empty/NaN arguments for facts with arity < 3
        args = [f"'{val}'" for val in [row.arg1, row.arg2, row.arg3] if pd.notna(val)]
        return f"{row.fact_name}({','.join(args)})"

    def _decode_prolog_result(self, term):
        """
        Safely decodes a term from pyswip if it's a byte string, 
        otherwise returns it as is. This handles pyswip's inconsistent return types.
        """
        if isinstance(term, bytes):
            return term.decode('utf-8')
        return term

    def load_kb_facts(self, kb_dataframe):
        """Asserts all facts from the Knowledge Base DataFrame into Prolog."""
        for _, row in kb_dataframe.iterrows():
            fact_string = self._format_fact(row)
            self.prolog.assertz(fact_string)
        print(f"Loaded {len(kb_dataframe)} facts into the Knowledge Base.")
    
    def run_audit(self, log_dataframe, current_date_str):
        """
        Audits a given log DataFrame against the loaded KB and returns a
        list of all detected violations.
        """
        all_violations = []
        print(f"Starting audit of {len(log_dataframe)} log entries...")
        
        # Assert the current date for the audit to ensure deterministic results
        self.prolog.assertz(f"current_date('{current_date_str}')")

        for _, entry in log_dataframe.iterrows():
            action = entry['action']
            action_fact = None

            # --- UPDATED: Handles all action types from both logs ---
            if action == 'read_phi':
                action_fact = (f"read_phi('{entry['principal']}', '{entry['resource']}', "
                               f"'{entry['purpose']}', '{entry['log_id']}')")
            elif action == 'request_access':
                # The resource column holds the PHI record ID for access requests
                request_date = entry['request_timestamp'].strftime('%Y-%m-%d')
                action_fact = (f"request_access('{entry['principal']}', '{entry['resource']}', "
                               f"'{entry['log_id']}', '{request_date}')")
            elif action == 'request_deactivation':
                request_date = entry['request_timestamp'].strftime('%Y-%m-%d')
                action_fact = (f"request_deactivation('{entry['principal']}', "
                               f"'{entry['log_id']}', '{request_date}')")
            
            # If the action is a known trigger, assert it and query for violations
            if action_fact:
                self.prolog.assertz(action_fact)

                query_result = list(self.prolog.query("violation(RuleID, Principal, ObjectID)"))
                
                if query_result:
                    for violation in query_result:
                        # Safely decode all parts of the result into standard strings
                        decoded_violation = {
                            'RuleID': self._decode_prolog_result(violation['RuleID']),
                            'Principal': self._decode_prolog_result(violation['Principal']),
                            'ObjectID': self._decode_prolog_result(violation['ObjectID']),
                            'timestamp': entry.get('timestamp') or entry.get('request_timestamp'),
                            'resource': entry['resource']
                        }
                        all_violations.append(decoded_violation)
                
                # Retract the temporary log entry fact to keep the state clean
                self.prolog.retract(action_fact)

        # Clean up the asserted date fact
        self.prolog.retract(f"current_date('{current_date_str}')")
        print(f"Audit complete. Found {len(all_violations)} violation(s).")
        return all_violations
