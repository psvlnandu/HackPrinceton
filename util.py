import pandas as pd
import numpy as np
from datetime import datetime

"""
CSV ENRICHER UTILITY (LLM-AWARE VERSION)
Purpose: Add ONLY temporal and session-based features to your existing CSV.
Does NOT classify apps/activities - trusts your Agent 1 LLM classification.

Input: activity_log01.csv (raw data from your logger)
Output: activity_log_enriched.csv (with temporal + session features)

Features added:
- Hour_of_Day, Day_of_Week, Is_Evening, Is_Early_Morning (time features)
- Session_Duration_Seconds (how long continuously in same window)
- Consecutive_Window_Count (how many times same window in a row)
- Time_Since_Last_Window_Change (seconds before switching)
- Window_Sequence (ordinal position in day's activity)
- Is_First_Activity_of_Hour (flag for pattern detection)

Then, Agent 1 will ADD the LLM classifications (Category, Confidence_Reason)
and these enriched features work together with that.
"""

def enrich_activity_log(input_file, output_file="activity_log_enriched.csv"):
    """
    Adds temporal and session features WITHOUT touching window title interpretation.
    """
    
    print(f"📖 Reading {input_file}...")
    df = pd.read_csv(input_file)
    
    # Ensure timestamp is datetime
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    
    print(f"✅ Loaded {len(df)} rows\n")
    
    # ===== PURE TEMPORAL FEATURES (No interpretation needed) =====
    
    print("⏰ Adding temporal features...")
    df['Hour_of_Day'] = df['Timestamp'].dt.hour
    df['Day_of_Week'] = df['Timestamp'].dt.day_name()
    df['Is_Evening'] = df['Hour_of_Day'] >= 18  # After 6 PM
    df['Is_Early_Morning'] = df['Hour_of_Day'] < 7  # Before 7 AM
    df['Minute_of_Day'] = df['Timestamp'].dt.hour * 60 + df['Timestamp'].dt.minute
    
    # ===== SESSION GROUPING (based on window title, not interpretation) =====
    
    print("🔄 Calculating session durations...")
    
    # Detect when window title changes
    df['Window_Changed'] = df['Window_Title'] != df['Window_Title'].shift(1)
    df['Window_Session_ID'] = df['Window_Changed'].cumsum()
    
    # For each row: how long have they been in THIS window so far?
    df['Session_Duration_Seconds'] = df.groupby('Window_Session_ID').cumcount() * 5 + 5
    
    # Total session length (when that session ends)
    session_lengths = df.groupby('Window_Session_ID')['Session_Duration_Seconds'].max()
    df['Total_Session_Duration_Seconds'] = df['Window_Session_ID'].map(session_lengths)
    
    # How many consecutive intervals in same window?
    df['Consecutive_Window_Count'] = df.groupby('Window_Session_ID').cumcount() + 1
    
    # ===== SWITCHING PATTERNS =====
    
    print("🔄 Analyzing switching behavior...")
    
    # Time since last window change
    df['Seconds_Since_Last_Switch'] = df.groupby('Window_Session_ID').cumcount() * 5
    
    # Count total number of switches up to this point
    df['Total_Switches_So_Far'] = df['Window_Session_ID'].apply(lambda x: (df['Window_Session_ID'] == x).sum())
    
    # How many unique windows seen in last 10 intervals (recent context switching)?
    # Use a manual loop instead of rolling.apply() which struggles with string data
    unique_windows_last_10 = []
    for i in range(len(df)):
        window_start = max(0, i - 9)  # Look at last 10 rows (including current)
        unique_count = df['Window_Title'].iloc[window_start:i+1].nunique()
        unique_windows_last_10.append(unique_count)
    df['Unique_Windows_Last_10'] = unique_windows_last_10
    
    # ===== TIME-BASED PATTERNS =====
    
    print("📊 Detecting time patterns...")
    
    # Is this the first entry of a new hour?
    df['Hour_Changed'] = df['Hour_of_Day'] != df['Hour_of_Day'].shift(1)
    df['Is_First_in_Hour'] = df['Hour_Changed'].astype(int)
    
    # Cumulative time worked (in seconds) from start of log
    df['Cumulative_Work_Seconds'] = np.arange(len(df)) * 5
    
    # Time of day buckets (for behavioral patterns)
    def get_time_bucket(hour):
        if 5 <= hour < 9:
            return 'Early_Morning'
        elif 9 <= hour < 12:
            return 'Morning'
        elif 12 <= hour < 14:
            return 'Midday'
        elif 14 <= hour < 17:
            return 'Afternoon'
        elif 17 <= hour < 20:
            return 'Evening'
        else:
            return 'Night'
    
    df['Time_Bucket'] = df['Hour_of_Day'].apply(get_time_bucket)
    
    # ===== ACTIVITY INTENSITY (based on switching, not classification) =====
    
    print("⚡ Calculating switching intensity...")
    
    # How many switches in the last 15 minutes (180 intervals * 5 sec = 900 sec)?
    # Manual calculation instead of rolling.apply()
    switches_last_15min = []
    for i in range(len(df)):
        window_start = max(0, i - 179)  # Last 180 intervals (15 min)
        window_data = df['Window_Title'].iloc[window_start:i+1]
        switches = (window_data != window_data.shift(1)).sum()
        switches_last_15min.append(switches)
    df['Switches_Last_15min'] = switches_last_15min
    
    # Switching rate: switches per hour
    df['Switching_Rate_Per_Hour'] = (df['Switches_Last_15min'] / 15) * 60
    
    # ===== CONTINUITY PATTERNS =====
    
    print("📈 Tracking activity continuity...")
    
    # Length of current session relative to average
    avg_session_length = df['Total_Session_Duration_Seconds'].mean()
    df['Session_Length_vs_Average'] = df['Total_Session_Duration_Seconds'] / avg_session_length
    
    # Is this session unusually long or short?
    df['Is_Extended_Session'] = df['Total_Session_Duration_Seconds'] > (avg_session_length * 2)
    df['Is_Brief_Session'] = df['Total_Session_Duration_Seconds'] < (avg_session_length * 0.5)
    
    # ===== CLEANUP =====
    
    df = df.drop(columns=['Window_Changed', 'Window_Session_ID', 'Hour_Changed'])
    
    # ===== SAVE =====
    
    print(f"\n✅ Enrichment complete!")
    print(f"📊 New columns added: {len(df.columns) - 2}")
    print(f"   (All purely temporal/structural—no activity interpretation)")
    
    df.to_csv(output_file, index=False)
    print(f"💾 Saved to: {output_file}\n")
    
    return df


def print_enrichment_summary(df):
    """Print summary of enriched features."""
    print("\n" + "="*70)
    print("ENRICHMENT SUMMARY")
    print("="*70)
    
    total_hours = len(df) * 5 / 3600
    total_switches = (df['Window_Title'] != df['Window_Title'].shift(1)).sum()
    avg_session_length = df['Total_Session_Duration_Seconds'].mean()
    avg_switching_rate = df['Switching_Rate_Per_Hour'].mean()
    extended_sessions = df['Is_Extended_Session'].sum()
    brief_sessions = df['Is_Brief_Session'].sum()
    
    print(f"\n📊 TEMPORAL DATA:")
    print(f"   Total logged time: {total_hours:.2f} hours")
    print(f"   Evening work (after 6 PM): {(df['Is_Evening'].sum()/len(df)*100):.1f}%")
    print(f"   Early morning (<7 AM): {(df['Is_Early_Morning'].sum()/len(df)*100):.1f}%")
    
    print(f"\n🔄 SWITCHING PATTERNS:")
    print(f"   Total window switches: {total_switches}")
    print(f"   Average switching rate: {avg_switching_rate:.1f} switches/hour")
    print(f"   Unique windows detected: {df['Window_Title'].nunique()}")
    
    print(f"\n⏱️  SESSION PATTERNS:")
    print(f"   Average session duration: {avg_session_length/60:.1f} minutes")
    print(f"   Extended sessions (>2x avg): {extended_sessions}")
    print(f"   Brief sessions (<0.5x avg): {brief_sessions}")
    print(f"   Max recent switching (last 15 min): {df['Switches_Last_15min'].max()}")
    
    print(f"\n⏰ TIME DISTRIBUTION:")
    time_by_bucket = df['Time_Bucket'].value_counts()
    for bucket, count in time_by_bucket.items():
        pct = count / len(df) * 100
        print(f"   {bucket}: {pct:.1f}%")
    
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    # Enrich your existing CSV
    enriched = enrich_activity_log("activity_log01.csv", output_file="activity_log_enriched01.csv")
    
    # Print summary stats
    print_enrichment_summary(enriched)
    
    # Show sample
    print("SAMPLE OF ENRICHED DATA:")
    sample_cols = [
        'Timestamp', 'Hour_of_Day', 'Session_Duration_Seconds',
        'Consecutive_Window_Count', 'Switching_Rate_Per_Hour',
        'Is_Extended_Session', 'Time_Bucket'
    ]
    print(enriched[sample_cols].head(15))