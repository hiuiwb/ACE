import pandas as pd
import io
import tempfile
from pyswip import Prolog
from datetime import datetime

# --- 1. The Policy Logic for Article 15 (DEBUGGING VERSION) ---
POLICY_RULES = """
:- use_module(library(date)).
:- dynamic(request_access/4).

days_since(StartDateString, EndDateString, Days) :-
    parse_time(StartDateString, '%Y-%m-%d', StartStamp),
    parse_time(EndDateString, '%Y-%m-%d', EndStamp),
    Days is floor((EndStamp - StartStamp) / (24 * 3600)).

% --- DEBUGGING INSTRUCTIONS ---
% Run this file once. It should find 2 violations.
% Then, comment out VERSION 1 and uncomment VERSION 2 and run again.
% If it still works, comment out VERSION 2 and uncomment VERSION 3.
% The step where it stops working will reveal the bug.

% --- VERSION 1: Test the most basic conditions ---
% Does the system correctly link an access request to the data owner?
violation('gdpr_art15_v1', Principal, RequestID) :-
    request_access(Principal, Resource, RequestID, _RequestDate),
    owns_data(Principal, Resource).

% --- VERSION 2: Add the fulfillment check ---
% Is the system correctly checking that the request is unfulfilled?
/*
violation('gdpr_art15_v2', Principal, RequestID) :-
    request_access(Principal, Resource, RequestID, _RequestDate),
    owns_data(Principal, Resource),
    \+ request_fulfilled(RequestID).
*/

% --- VERSION 3: The Full Rule with the Date Check ---
% Is the time logic working correctly?
/*
violation('gdpr_art15_v3', Principal, RequestID) :-
    request_access(Principal, Resource, RequestID, RequestDate),
    owns_data(Principal, Resource),
    current_date(Today),
    days_since(RequestDate, Today, Days),
    Days > 30,
    \+ request_fulfilled(RequestID).
*/
"""

# --- 2. The Test Data ---
KNOWLEDGE_BASE_DATA = """fact_name,arg1,arg2,arg3
owns_data,user_A,res_A_data,
owns_data,user_B,res_B_data,
"""

SYSTEM_LOG_DATA = """timestamp,principal,action,resource,purpose,request_id
2025-06-10T10:00:00,user_A,request_access,res_A_data,,acc_01
2025-06-15T11:00:00,user_B,request_access,res_B_data,,acc_02
2025-07-05T11:30:00,system,provide_data,,,acc_02
2025-06-20T12:00:00,user_C,request_access,res_A_data,,acc_03
"""

# --- 3. The Auditor Class and Main Script (No changes needed here) ---
class Auditor:
    def __init__(self, policy_file):
        self.prolog = Prolog()
        self.prolog.consult(policy_file)
        print(f"Auditor initialized with policy '{policy_file}'.")
    def _format_fact(self, row):
        args = [f"'{val}'" for val in [row.arg1, row.arg2, row.arg3] if pd.notna(val)]
        return f"{row.fact_name}({','.join(args)})"
    def _decode_prolog_result(self, term):
        if isinstance(term, bytes): return term.decode('utf-8')
        return term
    def load_kb_facts(self, kb_dataframe):
        for _, row in kb_dataframe.iterrows():
            self.prolog.assertz(self._format_fact(row))
        print(f"Loaded {len(kb_dataframe)} facts into the Knowledge Base.")
    def run_full_audit(self, log_dataframe, current_date_str):
        all_violations = []
        self.prolog.assertz(f"current_date('{current_date_str}')")
        for _, entry in log_dataframe.iterrows():
            if entry['action'] == 'request_access':
                request_date = entry['timestamp'].strftime('%Y-%m-%d')
                action_fact = f"request_access('{entry['principal']}', '{entry['resource']}', '{entry['request_id']}', '{request_date}')"
                self.prolog.assertz(action_fact)
                query_result = list(self.prolog.query("violation(RuleID, Principal, ObjectID)"))
                if query_result:
                    for violation in query_result:
                        decoded = {'RuleID': self._decode_prolog_result(violation['RuleID']), 'Principal': self._decode_prolog_result(violation['Principal']), 'ObjectID': self._decode_prolog_result(violation['ObjectID'])}
                        all_violations.append(decoded)
                self.prolog.retract(action_fact)
        self.prolog.retract(f"current_date('{current_date_str}')")
        print(f"Audit complete. Found {len(all_violations)} violation(s).")
        return all_violations

def preprocess_log_to_generate_facts(log_df):
    fulfilled_facts = []
    fulfilled_ids = set(log_df[log_df['action'] == 'provide_data']['request_id'])
    for req_id in fulfilled_ids:
        fulfilled_facts.append({"fact_name": "request_fulfilled", "arg1": req_id, "arg2": None, "arg3": None})
    return pd.DataFrame(fulfilled_facts)

def main():
    print("--- Starting Standalone Test for GDPR Article 15 ---")
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.pl', delete=False) as pf:
        pf.write(POLICY_RULES)
        policy_file_path = pf.name

    kb_df = pd.read_csv(io.StringIO(KNOWLEDGE_BASE_DATA), comment='#')
    log_df = pd.read_csv(io.StringIO(SYSTEM_LOG_DATA), comment='#')
    log_df['timestamp'] = pd.to_datetime(log_df['timestamp'], format='ISO8601')
    
    derived_facts_df = preprocess_log_to_generate_facts(log_df)
    kb_df = pd.concat([kb_df, derived_facts_df], ignore_index=True)
    
    audit_date = "2025-08-31"

    ace_auditor = Auditor(policy_file=policy_file_path)
    ace_auditor.load_kb_facts(kb_df)
    audit_log = log_df[log_df['action'] == 'request_access']
    all_violations = ace_auditor.run_full_audit(audit_log, audit_date)

    print("\n--- TEST RESULTS ---")
    if not all_violations:
        print("No violations were detected.")
    else:
        results_df = pd.DataFrame(all_violations)
        print("The following violations were detected:")
        print(results_df.to_string(index=False))

if __name__ == "__main__":
    main()