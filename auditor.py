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

    def _date_to_ymd(self, val):
        """
        Normalize a value to 'YYYY-MM-DD' string for Prolog facts.
        Accepts pandas.Timestamp, datetime, ISO strings or None.
        Returns None if the input is NaT/None/unparseable.
        """
        if pd.isna(val):
            return None
        if hasattr(val, 'strftime'):
            return val.strftime('%Y-%m-%d')
        try:
            return pd.to_datetime(val).strftime('%Y-%m-%d')
        except Exception:
            return None

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
            # if action == 'read_phi':
            #     action_fact = (f"read_phi('{entry['principal']}', '{entry['resource']}', "
            #                    f"'{entry['purpose']}', '{entry['log_id']}')")
            # elif action == 'request_access':
            #     # The resource column holds the PHI record ID for access requests
            #     request_date = entry['request_timestamp'].strftime('%Y-%m-%d')
            #     action_fact = (f"request_access('{entry['principal']}', '{entry['resource']}', "
            #                    f"'{entry['log_id']}', '{request_date}')")
            # elif action == 'request_deactivation':
            #     request_date = entry['request_timestamp'].strftime('%Y-%m-%d')
            #     action_fact = (f"request_deactivation('{entry['principal']}', "
            #                    f"'{entry['log_id']}', '{request_date}')")
            

            if action == 'read_phi':
                action_fact = (f"read_phi('{entry['principal']}', '{entry['resource']}', "
                               f"'{entry['purpose']}', '{entry['log_id']}')")
            elif action == 'request_access':
                # Use helper to tolerate strings or Timestamps
                request_date = self._date_to_ymd(entry.get('request_timestamp'))
                request_date_str = request_date if request_date is not None else ''
                action_fact = (f"request_access('{entry['principal']}', '{entry['resource']}', "
                               f"'{entry['log_id']}', '{request_date_str}')")
            elif action == 'request_deactivation':
                request_date = self._date_to_ymd(entry.get('request_timestamp'))
                request_date_str = request_date if request_date is not None else ''
                action_fact = (f"request_deactivation('{entry['principal']}', "
                               f"'{entry['log_id']}', '{request_date_str}')")


            # If the action is a known trigger, assert it and query for violations
            if action_fact:
                # For request facts, skip if the parsed request timestamp is NaT
                if action.startswith('request_'):
                    parsed_dt = entry.get('request_timestamp')
                    if pd.isna(parsed_dt):
                        print(f"Skipping assertion for {entry.get('log_id')} due to missing/invalid request date: raw_value={entry.get('request_timestamp')!r}")
                        continue

                # Log the exact fact we'll assert for easier tracing
                print(f"Asserting fact: {action_fact}")
                self.prolog.assertz(action_fact)

                # If this is a read_phi event, also assert attribute-level read facts
                attribute_facts = []
                if action == 'read_phi':
                    # Map DataFrame columns to attribute atoms used in policy
                    for col, attr in (('lab_result', 'lab_result'), ('clinical_note', 'clinical_note'), ('billing_info', 'billing_info')):
                        try:
                            val = entry.get(col)
                        except Exception:
                            val = None
                        # treat truthy (1 or '1') as read
                        if val in (1, '1', True):
                            fact = f"read_attribute('{entry['principal']}', '{entry['resource']}', {attr})"
                            attribute_facts.append(fact)
                            try:
                                self.prolog.assertz(fact)
                            except Exception:
                                # best-effort; continue if assertion fails
                                pass

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
                
                # Retract any attribute-level facts we asserted for this entry
                for af in attribute_facts:
                    try:
                        self.prolog.retractall(af)
                    except Exception:
                        try:
                            self.prolog.retract(af)
                        except Exception:
                            pass

                # Retract the temporary log entry fact to keep the state clean
                # Use retractall to avoid quoting/arity fragility
                try:
                    self.prolog.retractall(action_fact)
                except Exception:
                    # Fallback to simple retract if retractall isn't available for the term
                    try:
                        self.prolog.retract(action_fact)
                    except Exception:
                        pass

        # Clean up the asserted date fact
        self.prolog.retract(f"current_date('{current_date_str}')")
        print(f"Audit complete. Found {len(all_violations)} violation(s).")
        return all_violations
