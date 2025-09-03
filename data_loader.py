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
    
    # Use the robust ISO8601 parser to handle timestamp variations
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')
    
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
    df = pd.read_csv(filepath)
    
    # Convert both timestamp columns
    df['request_timestamp'] = pd.to_datetime(df['request_timestamp'], format='ISO8601')
    # The process_timestamp can have missing values (NaT), which is handled correctly
    df['process_timestamp'] = pd.to_datetime(df['process_timestamp'], format='ISO8601', errors='coerce')

    return df
