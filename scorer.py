# scorer.py

import pandas as pd
import numpy as np

class ComplianceScorer:
    """Calculates a fine-grained compliance score from a list of violations."""
    def __init__(self, weights, normalization_constants, rule_criticalities):
        self.weights = weights
        self.k = normalization_constants
        self.rule_criticalities = rule_criticalities
        print("Compliance Scorer initialized.")

    def _normalize(self, value, k_const):
        """Applies the negative exponential normalization from Definition 3.8."""
        return 1 - np.exp(-k_const * float(value))

    def calculate_final_score(self, violations, principal_id, time_window_days=30):
        """Calculates the final compliance score based on the 'worst-offense' model."""
        if not violations:
            return 1.0

        violations_df = pd.DataFrame(violations)
        
        end_date = violations_df['timestamp'].max()
        start_date = end_date - pd.Timedelta(days=time_window_days)
        principal_violations = violations_df[
            (violations_df['Principal'] == principal_id) &
            (violations_df['timestamp'] >= start_date)
        ]

        if principal_violations.empty:
            return 1.0

        grouped = principal_violations.groupby('RuleID')
        max_severity = 0.0

        for rule_id, group in grouped:
            volume = group['resource'].nunique()
            duration = (group['timestamp'].max() - group['timestamp'].min()).days + 1
            breadth = 1 # Simplified for this experiment

            s_v = self._normalize(volume, self.k['V'])
            s_t = self._normalize(duration, self.k['T'])
            s_b = self._normalize(breadth, self.k['B'])
            criticality = self.rule_criticalities.get(rule_id, 0.5)

            severity_score = (self.weights['C'] * criticality +
                              self.weights['V'] * s_v +
                              self.weights['T'] * s_t +
                              self.weights['B'] * s_b)
            
            if severity_score > max_severity:
                max_severity = severity_score

        compliance_score = 1.0 - max_severity
        return max(0.0, compliance_score)