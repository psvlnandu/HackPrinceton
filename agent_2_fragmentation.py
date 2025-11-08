import pandas as pd
import numpy as np
"""
    Agent 2 (Fragmentation) - 
    Detects context switches with weighted costs based on disruption type → Context Switch Cost (CSC)
"""
# --- Configuration ---
INPUT_FILE = "classified_activity01.csv"
OUTPUT_FILE = "fragmented_activity01.csv"

# --- Context Switch Cost (CSC) Configuration ---
# Assigns a "cost" multiplier to each type of switch.
# High Load -> Communication is the most disruptive switch (High Cost)
# Low Load -> Low Load is the least disruptive (Low Cost)
COST_MULTIPLIERS = {
    ('High Load', 'Communication'): 5,
    ('High Load', 'Low Load'): 3,
    ('Communication', 'High Load'): 4,
    ('Communication', 'Low Load'): 2,
    ('Low Load', 'High Load'): 3,
    ('Low Load', 'Communication'): 2,
    # Switches within the same category are low cost
    ('High Load', 'High Load'): 1,
    ('Communication', 'Communication'): 1,
    ('Low Load', 'Low Load'): 0.5,
    # Unclassified switches should be penalized
    ('UNCLASSIFIED', 'UNCLASSIFIED'): 5,
}

def calculate_fragmentation_metrics():
    """
    Reads the classified data and calculates the Context Switch Cost (CSC).
    """
    print("--- Running Agent 2: Fragmentation Analyzer ---")
    
    try:
        df = pd.read_csv(INPUT_FILE)
    except FileNotFoundError:
        print(f"FATAL ERROR: Input file not found at '{INPUT_FILE}'. Please ensure Agent 1 ran successfully.")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    print(f"Successfully loaded {len(df)} activity entries.")
    
    # 1. Identify where a switch occurred
    # Shifts the 'Category' column up by 1 to compare the current row's category with the previous row's category.
    df['Previous_Category'] = df['Category'].shift(1)
    
    # The first row will be NaN, so we assume no switch cost for the start of the log.
    df['Previous_Category'].fillna(df['Category'].iloc[0], inplace=True)
    
    # 2. Calculate the Switch Cost Multiplier (CSC) for each time interval
    def calculate_cost(row):
        # Create a tuple of (Previous_Category, Current_Category)
        switch_key = (row['Previous_Category'], row['Category'])
        
        # Look up the multiplier defined in the dictionary. Default to 1 if categories are missing.
        cost = COST_MULTIPLIERS.get(switch_key, 1)
        
        # CSC is the total disruption cost for this 5-second interval.
        return cost * 5 # Multiplier * Duration_Seconds (5 seconds)

    # Apply the cost calculation across all rows
    df['Switch_Cost'] = df.apply(calculate_cost, axis=1)

    # 3. Calculate Total Context Switch Cost (CSC)
    total_switch_cost = df['Switch_Cost'].sum()
    total_duration_minutes = df['Duration_Seconds'].sum() / 60
    
    # CSC is normalized to represent cost per hour (higher is worse)
    csc_score = (total_switch_cost / total_duration_minutes) * 60 / 3600 # Cost per hour in seconds equivalent

    # 4. Generate Output Metrics
    total_switches = (df['Category'] != df['Previous_Category']).sum()
    
    print("\n--- Insight 2: Context Switch Cost (CSC) ---")
    print(f"Total Detected Category Switches: {total_switches}")
    print(f"Total Weighted Switch Cost (Disruption): {total_switch_cost:.2f} seconds equivalent")
    print(f"CSC Score (Normalized Cost per Hour): {csc_score:.2f} seconds")
    
    # Add CSC to the DataFrame for Agent 3
    df['CSC_Score'] = csc_score 

    # Save the file
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nFragmentation data successfully analyzed and saved to: {OUTPUT_FILE}")

if __name__ == '__main__':
    calculate_fragmentation_metrics()