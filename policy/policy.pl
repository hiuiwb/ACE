% --- ACE: Compliance Policy File (HIPAA Scenario) ---
% This file contains formal compliance rules based on the HIPAA
% Privacy, Security, and Breach Notification Rules.

:- use_module(library(date)).

% --- DYNAMIC PREDICATE DECLARATIONS ---
% Predicates that will be asserted dynamically from the system log.
:- dynamic(read_phi/4).
:- dynamic(request_access/4).
:- dynamic(breach_discovered/3).

% --- HELPER PREDICATES ---
days_since(StartDateString, EndDateString, Days) :-
    parse_time(StartDateString, '%Y-%m-%d', StartStamp),
    parse_time(EndDateString, '%Y-%m-%d', EndStamp),
    Days is floor((EndStamp - StartStamp) / (24 * 3600)).

% --- COMPLIANCE VIOLATION RULES ---
% violation(RuleID, Principal, OffendingObjectID)

% --- Rule 1: Access Control Violation ---
% A doctor must be formally assigned to a patient to access their record.
violation('hipaa_access_control', Doctor, PHI_Record) :-
    read_phi(Doctor, PHI_Record, _Purpose, _EventID),
    has_role(Doctor, 'doctor'),
    owns_phi_record(Patient, PHI_Record),
    \+ is_doctor_of(Doctor, Patient).

% --- Rule 2: Minimum Necessary Violation ---
% A principal's role must permit them to access a specific type of data.
violation('hipaa_min_necessary', Principal, PHI_Record) :-
    read_phi(Principal, PHI_Record, _Purpose, _EventID),
    has_role(Principal, Role),
    resource_type(PHI_Record, Type),
    \+ role_can_access_type(Role, Type).

% --- Rule 3: Patient Right of Access Violation ---
% A patient's request for their data must be fulfilled within 30 days.
violation('hipaa_patient_access', Patient, RequestID) :-
    request_access(Patient, PHI_Record, RequestID, RequestDate),
    owns_phi_record(Patient, PHI_Record),
    current_date(Today),
    days_since(RequestDate, Today, Days),
    Days > 30,
    \+ request_fulfilled(RequestID).

% --- Rule 4: Breach Notification Violation ---
% Affected individuals must be notified of a data breach within 60 days.
violation('hipaa_breach_notification', Patient, BreachID) :-
    breach_discovered(BreachID, PatientsAffected, BreachDate),
    member(Patient, PatientsAffected), % Check for each affected patient
    current_date(Today),
    days_since(BreachDate, Today, Days),
    Days > 60,
    \+ notification_sent(BreachID, Patient).