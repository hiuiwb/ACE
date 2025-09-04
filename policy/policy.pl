% --- ACE: Compliance Policy File (Hospital Scenario) ---
% This file contains formal compliance rules for a healthcare environment,
% covering both HIPAA-style authorization and GDPR data subject rights.

:- use_module(library(date)). % Use Prolog's library for date/time functions

% --- DYNAMIC PREDICATE DECLARATIONS ---
% Declare predicates that will be asserted dynamically from the system log.
:- dynamic(read_phi/4).
:- dynamic(request_access/4).
:- dynamic(request_deactivation/3).
:- dynamic(request_fulfilled/1).
:- dynamic(deactivation_fulfilled/1).


% --- HELPER PREDICATES ---

% Calculates days between two date strings (ISO-like). Uses parse_time/2
% to obtain epoch seconds, then computes whole days difference.
days_since(StartDateString, EndDateString, Days) :-
    catch(parse_time(StartDateString, StartStamp), _, fail),
    catch(parse_time(EndDateString, EndStamp), _, fail),
    Seconds is EndStamp - StartStamp,
    DaysFloat is Seconds / (24 * 3600),
    Days is floor(DaysFloat).


% --- COMPLIANCE VIOLATION RULES ---
% A violation is a predicate of the form:
% violation(RuleID, Principal, OffendingObjectID)

% --- Rule 1: Authorization Violation (HIPAA-style) ---
% A violation occurs if a doctor reads a PHI record belonging to a
% patient they are not formally assigned to in the Knowledge Base.
violation('hipaa_auth', Doctor, PHI_Record) :-
    read_phi(Doctor, PHI_Record, _Purpose, _EventID),
    has_role(Doctor, 'doctor'),
    owns_phi_record(Patient, PHI_Record),
    \+ is_doctor_of(Doctor, Patient).

% --- Rule 2: Minimum Necessary Violation (HIPAA-style) ---
% A violation occurs if a principal's role does not permit them to
% access the specific type of data contained in the record.
% violation('hipaa_min_necessary', Principal, PHI_Record) :-
%    read_phi(Principal, PHI_Record, _Purpose, _EventID),
%    has_role(Principal, Role),
%    resource_type(PHI_Record, Type),
%    \+ role_can_access_type(Role, Type).

% Add dynamic declaration for attribute-level read facts
:- dynamic(read_attribute/3).  % read_attribute(Principal, PHI_Record, AttributeAtom)

% --- Rule 2: Minimum Necessary Violation (attribute-aware) ---
% A violation occurs if a principal's role does not permit them to access any
% specific attribute contained in the record that they actually read.
violation('hipaa_min_necessary', Principal, PHI_Record) :-
    read_phi(Principal, PHI_Record, _Purpose, _EventID),
    has_role(Principal, Role),
    read_attribute(Principal, PHI_Record, Attribute),
    \+ role_can_access_type(Role, Attribute).

% --- Rule 3: GDPR Art. 18 (Restriction of Processing) ---
% A violation occurs if a patient's record is used for a 'Purpose'
% for which the patient does not have an 'unrestricted_status'.
violation('gdpr_art18_restriction', Principal, PHI_Record) :-
    read_phi(Principal, PHI_Record, Purpose, _EventID),
    owns_phi_record(Patient, PHI_Record),
    \+ has_unrestricted_status(Patient, Purpose).

% --- Rule 4: GDPR Art. 17 (Right to Erasure) ---
% A violation occurs if a deactivation request from a patient is older
% than 30 days and has not been marked as fulfilled.
% violation('gdpr_art17_erasure', Patient, RequestID) :-
%     request_deactivation(Patient, RequestID, RequestDate),
%     current_date(Today),
%     days_since(RequestDate, Today, Days),
%     Days > 30,
%     \+ deactivation_fulfilled(RequestID).

% --- Rule 5: GDPR Art. 15 (Right of Access) ---
% A violation occurs if a patient's valid access request is older than 30
% days and has not been marked as 'fulfilled' in the Knowledge Base.
% violation('gdpr_art15_access', Patient, RequestID) :-
%     request_access(Patient, _PHI_Record, RequestID, RequestDate),
%     current_date(Today),
%     days_since(RequestDate, Today, Days),
%     Days > 30,
%     \+ request_fulfilled(RequestID).

% --- Rule 4: GDPR Art. 17 (Right to Erasure) ---
% A violation occurs if a deactivation request from a patient is older
% than 30 days and has not been marked as fulfilled. We attribute the
% violation to the patient's assigned doctor.
violation('gdpr_art17_erasure', Doctor, RequestID) :-
    request_deactivation(Patient, RequestID, RequestDate),
    is_doctor_of(Doctor, Patient),
    current_date(Today),
    days_since(RequestDate, Today, Days),
    Days > 30,
    \+ deactivation_fulfilled(RequestID).

% --- Rule 5: GDPR Art. 15 (Right of Access) ---
% A violation occurs if a patient's valid access request is older than 30
% days and has not been marked as 'fulfilled' in the Knowledge Base.
% The violation is attributed to the doctor's responsibility to process it.
violation('gdpr_art15_access', Doctor, RequestID) :-
    request_access(Patient, _PHI_Record, RequestID, RequestDate),
    is_doctor_of(Doctor, Patient),
    current_date(Today),
    days_since(RequestDate, Today, Days),
    Days > 30,
    \+ request_fulfilled(RequestID).