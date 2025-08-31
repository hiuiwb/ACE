# data_loader.py

import pandas as pd

def load_knowledge_base(filepath="knowledge_base.csv"):
    """Loads the Knowledge Base facts from a CSV file."""
    print(f"Loading Knowledge Base from {filepath}...")
    return pd.read_csv(filepath)

def load_system_log(filepath="system_log.csv"):
    """
    Loads the System Log events from a CSV file and converts the
    timestamp column to a proper datetime object for calculations.
    """
    print(f"Loading System Log from {filepath}...")
    df = pd.read_csv(filepath)
    
    # Use the robust ISO8601 parser to handle timestamp variations
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')
    
    return df