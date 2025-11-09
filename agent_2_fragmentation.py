import pandas as pd
import numpy as np

"""
Agent 2A (Fragmentation) - 
Detects context switches with weighted costs based on disruption type
"""

INPUT_FILE = "activity_log_enriched01.csv"
OUTPUT_FILE = "fragmented_activity01.csv"

COST_MULTIPLIERS = {
    ('High Load', 'Communication'): 5,
    ('High Load', 'Low Load'): 3,
    ('Communication', 'High Load'): 4,
    ('Communication', 'Low Load'): 2,
    ('Low Load', 'High Load'): 3,
    ('Low Load', 'Communication'): 2,
    ('High Load', 'High Load'): 1,
    ('Communication', 'Communication'): 1,
    ('Low Load', 'Low Load'): 0.5,
    ('UNCLASSIFIED', 'UNCLASSIFIED'): 5,
}

def calculate_fragmentation_metrics():
    """Calculate Context Switch Cost (CSC)"""
    print("Running Agent 2A: Fragmentation Analyzer...")
    
    try:
        df = pd.read_csv(INPUT_FILE)
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    print(f"Loaded {len(df)} activity entries\n")
    
    # Check if Category column exists
    if 'Category' not in df.columns:
        print("Error: 'Category' column not found. Run Agent 1 first.")
        return
    
    # Add Duration column if it doesn't exist (default 5 seconds per row)
    if 'Duration_Seconds' not in df.columns:
        df['Duration_Seconds'] = 5
    
    # Identify context switches
    df['Previous_Category'] = df['Category'].shift(1)
    df['Previous_Category'].fillna(df['Category'].iloc[0], inplace=True)
    
    # Calculate switch cost
    def calculate_cost(row):
        switch_key = (row['Previous_Category'], row['Category'])
        cost = COST_MULTIPLIERS.get(switch_key, 1)
        return cost * 5
    
    df['Switch_Cost'] = df.apply(calculate_cost, axis=1)
    
    # Calculate CSC Score
    total_switch_cost = df['Switch_Cost'].sum()
    total_duration_seconds = df['Duration_Seconds'].sum()
    total_duration_hours = total_duration_seconds / 3600
    
    csc_score = total_switch_cost / total_duration_hours if total_duration_hours > 0 else 0
    
    total_switches = (df['Category'] != df['Previous_Category']).sum()
    
    print("="*60)
    print("Insight 2: Context Switch Cost (CSC)")
    print("="*60)
    print(f"Total Category Switches: {total_switches}")
    print(f"Total Weighted Switch Cost: {total_switch_cost:.2f} seconds")
    print(f"Total Duration: {total_duration_hours:.2f} hours")
    print(f"CSC Score (per hour): {csc_score:.2f} seconds")
    print("="*60 + "\n")
    
    df['CSC_Score'] = csc_score
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved to: {OUTPUT_FILE}\n")

if __name__ == '__main__':
    try:
        calculate_fragmentation_metrics()
    except Exception as e:
        print(f"Fatal error: {e}")