import pandas as pd
import numpy as np

class ComplianceScorer:
    """
    Calculates a fine-grained compliance score from a list of violations
    based on the formal model defined in the research paper.
    """
    def __init__(self, weights, normalization_constants, rule_criticalities, kb_path=None):
        """
        Initializes the scorer with the necessary parameters from the model.
        
        Args:
            weights (dict): The convex combination weights (wC, wV, wT, wB).
            normalization_constants (dict): The k-values for normalization (kV, kT, kB).
            rule_criticalities (dict): A mapping of rule_id to its criticality score (Ci).
        """
        # validate and normalize inputs
        self.weights = self._validate_and_normalize_weights(weights)
        self.k = self._validate_normalization_constants(normalization_constants)
        self.rule_criticalities = self._validate_rule_criticalities(rule_criticalities)

        # optional KB path (CSV produced by the KB generator)
        self.kb_path = kb_path
        self._resource_type_map = None
        if kb_path:
            try:
                self._resource_type_map = self._load_kb_resource_types(kb_path)
            except Exception:
                # don't fail construction on KB load problems; fallback later
                self._resource_type_map = None

        print("Compliance Scorer initialized.")

    def _validate_and_normalize_weights(self, weights):
        # expect dict with keys 'C','V','T','B'
        required = {'C', 'V', 'T', 'B'}
        if not required.issubset(set(weights.keys())):
            raise ValueError(f"weights must contain keys {required}")
        vals = np.array([weights[k] for k in ['C','V','T','B']], dtype=float)
        s = vals.sum()
        if s <= 0:
            raise ValueError('weights must sum to a positive value')
        if not np.isclose(s, 1.0):
            # normalize to a convex combination
            vals = vals / s
        return dict(zip(['C','V','T','B'], vals.tolist()))

    def _validate_normalization_constants(self, k):
        # expect dict with keys 'V','T','B' and positive values
        for kk in ['V','T','B']:
            if kk not in k:
                raise ValueError(f"normalization_constants must include '{kk}'")
            if float(k[kk]) <= 0:
                raise ValueError(f"normalization constant {kk} must be positive")
        return {kk: float(k[kk]) for kk in ['V','T','B']}

    def _validate_rule_criticalities(self, rc):
        # ensure values are in [0,1]; missing entries will be handled later
        out = {}
        for k, v in rc.items():
            fv = float(v)
            if fv < 0 or fv > 1:
                raise ValueError(f'criticality for {k} must be in [0,1]')
            out[k] = fv
        return out

    def _load_kb_resource_types(self, kb_path):
        """Load resource->type facts from the KB CSV if available.

        Looks for fact_name == 'resource_type' and returns a dict mapping resource->type.
        If none found, returns an empty dict.
        """
        import csv
        m = {}
        with open(kb_path, newline='') as fh:
            reader = csv.DictReader(fh)
            for r in reader:
                fact = r.get('fact_name')
                if fact == 'resource_type':
                    res = r.get('arg1')
                    typ = r.get('arg2')
                    if res and typ:
                        m[res] = typ
        return m

    def _get_resource_type(self, resource_id):
        """Return the resource type according to the KB mapping, or None if unknown."""
        if not self._resource_type_map:
            return None
        return self._resource_type_map.get(resource_id)

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
        # coerce/parse timestamp column to datetimes if needed
        if 'timestamp' in violations_df.columns:
            violations_df['timestamp'] = pd.to_datetime(violations_df['timestamp'])
        
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
            # Breadth: number of distinct resource types involved in the violation instance.
            # If a KB mapping was provided at construction, use it; otherwise fall back to 1.
            breadth = 1
            try:
                types = set()
                for res in group['resource'].unique():
                    t = self._get_resource_type(res)
                    if t:
                        types.add(t)
                if len(types) > 0:
                    breadth = len(types)
            except Exception:
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

            # store per-rule details for optional breakdown export
            try:
                row = {
                    'RuleID': rule_id,
                    'volume': int(volume),
                    'duration_days': int(duration),
                    'breadth': int(breadth),
                    's_v': float(s_v),
                    's_t': float(s_t),
                    's_b': float(s_b),
                    'criticality': float(criticality),
                    'severity': float(severity_score)
                }
                if 'breakdown' not in locals():
                    breakdown = []
                breakdown.append(row)
            except Exception:
                pass

        # 4. Compute Final Principal Compliance Score (Def 3.10)
        compliance_score = 1.0 - max_severity

        final = max(0.0, compliance_score) # Ensure score is not negative
        # if caller requested a breakdown, return it as well (backwards compatible)
        if 'breakdown' in locals():
            bd_df = pd.DataFrame(breakdown)
            bd_df = bd_df.sort_values('severity', ascending=False).reset_index(drop=True)
            return final, bd_df
        return final

    def export_breakdown(self, breakdown_df, path):
        """Save a per-rule breakdown DataFrame to CSV for external analysis."""
        if breakdown_df is None or breakdown_df.empty:
            raise ValueError('breakdown_df must be a non-empty pandas DataFrame')
        breakdown_df.to_csv(path, index=False)
