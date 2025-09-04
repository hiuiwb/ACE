import pandas as pd

def load_knowledge_base(filepath="knowledge_base.csv"):
    """
    Loads the Knowledge Base facts from a CSV file.
    
    Args:
        filepath (str): The path to the knowledge_base.csv file.
    
    Returns:
        pandas.DataFrame: A DataFrame containing the knowledge base facts.
    """
    print(f"Loading Knowledge Base from {filepath}...")
    return pd.read_csv(filepath)

def load_staff_log(filepath="staff_activity_log.csv"):
    """
    Loads the Hospital Staff Activity Log from a CSV file and converts the
    timestamp column to a proper datetime object for calculations.
    
    Args:
        filepath (str): The path to the staff_activity_log.csv file.
        
    Returns:
        pandas.DataFrame: A DataFrame containing the staff log events.
    """
    print(f"Loading Staff Activity Log from {filepath}...")
    df = pd.read_csv(filepath)
    
    # Robust parsing: let pandas infer ISO dates; invalid parse -> NaT
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    return df

def load_patient_log(filepath="patient_request_log.csv"):
    """
    Loads the Patient Request Log from a CSV file and converts both
    timestamp columns to proper datetime objects.
    
    Args:
        filepath (str): The path to the patient_request_log.csv file.
        
    Returns:
        pandas.DataFrame: A DataFrame containing the patient request events.
    """
    print(f"Loading Patient Request Log from {filepath}...")
    # Read timestamps as raw strings to avoid pandas silently converting unusual tokens to NaN
    df = pd.read_csv(filepath, dtype=str)

    # Restore numeric flag columns to integers if present
    for col in ('lab_result', 'clinical_note', 'billing_info'):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # Normalize and parse timestamp columns robustly
    for ts_col in ('request_timestamp', 'process_timestamp'):
        if ts_col in df.columns:
            # Ensure string, strip whitespace and surrounding quotes
            df[ts_col] = df[ts_col].astype(str).str.strip()
            df[ts_col] = df[ts_col].str.strip('"').str.strip("'")
            # Convert obvious null-like strings to real NaN so to_datetime will coerce
            df[ts_col] = df[ts_col].replace({'nan': None, 'None': None, '': None})
            # Try common ISO formats explicitly to handle microsecond and second-only cases reliably
            series = df[ts_col]
            parsed = pd.to_datetime(series, format='%Y-%m-%dT%H:%M:%S.%f', errors='coerce')
            mask = parsed.isna()
            if mask.any():
                parsed2 = pd.to_datetime(series[mask], format='%Y-%m-%dT%H:%M:%S', errors='coerce')
                parsed.loc[mask] = parsed2
            # final fallback to pandas flexible parser
            still_mask = parsed.isna()
            if still_mask.any():
                parsed.loc[still_mask] = pd.to_datetime(series[still_mask], errors='coerce')
            df[ts_col] = parsed

    return df
