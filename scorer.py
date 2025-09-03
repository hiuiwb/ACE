import pandas as pd
import numpy as np

class ComplianceScorer:
    """
    Calculates a fine-grained compliance score from a list of violations
    based on the formal model defined in the research paper.
    """
    def __init__(self, weights, normalization_constants, rule_criticalities):
        """
        Initializes the scorer with the necessary parameters from the model.
        
        Args:
            weights (dict): The convex combination weights (wC, wV, wT, wB).
            normalization_constants (dict): The k-values for normalization (kV, kT, kB).
            rule_criticalities (dict): A mapping of rule_id to its criticality score (Ci).
        """
        self.weights = weights
        self.k = normalization_constants
        self.rule_criticalities = rule_criticalities
        print("Compliance Scorer initialized.")

    def _normalize(self, value, k_const):
        """Applies the negative exponential normalization from Definition 3.8."""
        return 1 - np.exp(-k_const * float(value))

    def calculate_final_score(self, violations, principal_id, time_window_days=30):
        """
        Calculates the final compliance score for a principal based on the
        'worst-offense' approach from Definition 3.10.
        
        Args:
            violations (list): A list of violation dictionaries from the Auditor.
            principal_id (str): The ID of the principal to score.
            time_window_days (int): The look-back period for the evaluation.
            
        Returns:
            float: The final compliance score, bounded between 0.0 and 1.0.
        """
        if not violations:
            return 1.0 # Perfect compliance if there are no violations at all

        violations_df = pd.DataFrame(violations)
        
        # Filter for the specific principal and time window
        end_date = violations_df['timestamp'].max()
        start_date = end_date - pd.Timedelta(days=time_window_days)
        principal_violations = violations_df[
            (violations_df['Principal'] == principal_id) &
            (violations_df['timestamp'] >= start_date)
        ]

        if principal_violations.empty:
            return 1.0 # Perfect compliance for this principal in this window

        # Group individual violations by rule to form "Violation Instances" (Def 3.6)
        grouped = principal_violations.groupby('RuleID')
        
        max_severity = 0.0

        for rule_id, group in grouped:
            # 1. Calculate Magnitude Metrics (Def 3.6)
            volume = group['resource'].nunique()
            duration = (group['timestamp'].max() - group['timestamp'].min()).days + 1
            # Note: A full implementation of Breadth would require joining with the
            # Knowledge Base to get resource types. For this script, we simplify
            # it to 1, representing a single category of violation.
            breadth = 1 

            # 2. Normalize Components (Def 3.8)
            s_v = self._normalize(volume, self.k['V'])
            s_t = self._normalize(duration, self.k['T'])
            s_b = self._normalize(breadth, self.k['B'])
            criticality = self.rule_criticalities.get(rule_id, 0.5) # Default criticality

            # 3. Calculate Violation Severity Score (Def 3.9)
            severity_score = (self.weights['C'] * criticality +
                              self.weights['V'] * s_v +
                              self.weights['T'] * s_t +
                              self.weights['B'] * s_b)
            
            if severity_score > max_severity:
                max_severity = severity_score

        # 4. Compute Final Principal Compliance Score (Def 3.10)
        compliance_score = 1.0 - max_severity
        
        return max(0.0, compliance_score) # Ensure score is not negative
