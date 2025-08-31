# auditor.py

from pyswip import Prolog
import pandas as pd

class Auditor:
    """An engine for detecting compliance violations using a Prolog policy."""
    def __init__(self, policy_file="policy.pl"):
        self.prolog = Prolog()
        self.prolog.consult(policy_file)
        print(f"Auditor initialized with policy '{policy_file}'.")

    def _format_fact(self, row):
        """Formats a row from the KB DataFrame into a Prolog fact string."""
        args = [f"'{val}'" for val in [row.arg1, row.arg2, row.arg3] if pd.notna(val)]
        return f"{row.fact_name}({','.join(args)})"

    def _decode_prolog_result(self, term):
        """Safely decodes a term from pyswip if it's a byte string."""
        if isinstance(term, bytes):
            return term.decode('utf-8')
        return term

    def load_kb_facts(self, kb_dataframe):
        """Asserts all facts from the Knowledge Base DataFrame into Prolog."""
        for _, row in kb_dataframe.iterrows():
            fact_string = self._format_fact(row)
            self.prolog.assertz(fact_string)
        print(f"Loaded {len(kb_dataframe)} facts into the Knowledge Base.")
    
    def run_full_audit(self, log_dataframe, current_date_str):
        """Audits an entire system log and returns a list of detected violations."""
        all_violations = []
        print(f"Starting full audit of {len(log_dataframe)} log entries...")
        self.prolog.assertz(f"current_date('{current_date_str}')")

        for _, entry in log_dataframe.iterrows():
            action = entry['action']
            action_fact = None

            # Handle different action types from the hospital scenario log
            if action in ['read_phi', 'process']:
                action_fact = (f"{action}('{entry['principal']}', "
                               f"'{entry['resource']}', '{entry['purpose']}', '{entry['request_id']}')")
            elif action == 'request_access':
                request_date = entry['timestamp'].strftime('%Y-%m-%d')
                action_fact = (f"request_access('{entry['principal']}', "
                               f"'{entry['resource']}', '{entry['request_id']}', '{request_date}')")
            
            if action_fact:
                self.prolog.assertz(action_fact)
                query_result = list(self.prolog.query("violation(RuleID, Principal, ObjectID)"))
                if query_result:
                    for violation in query_result:
                        decoded_violation = {
                            'RuleID': self._decode_prolog_result(violation['RuleID']),
                            'Principal': self._decode_prolog_result(violation['Principal']),
                            'ObjectID': self._decode_prolog_result(violation['ObjectID']),
                            'timestamp': entry['timestamp'],
                            'resource': entry['resource']
                        }
                        all_violations.append(decoded_violation)
                self.prolog.retract(action_fact)

        self.prolog.retract(f"current_date('{current_date_str}')")
        print(f"Audit complete. Found {len(all_violations)} violation(s).")
        return all_violations