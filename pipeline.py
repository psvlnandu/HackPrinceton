#!/usr/bin/env python3
"""
PIPELINE ORCHESTRATOR
Runs the complete analysis pipeline in sequence:
1. Enrich CSV
2. Agent 1: Classification
3. Agent 2A: Fragmentation
4. Agent 2B: Burnout Detection
5. Agent 3: Health Synthesis

Usage: python pipeline.py
"""

import subprocess
import sys
import time
from datetime import datetime

def run_command(cmd, description):
    """Run a command and report status"""
    print(f"\n{'='*70}")
    print(f"⏳ {description}")
    print(f"{'='*70}")
    
    start_time = time.time()
    try:
        result = subprocess.run(cmd, shell=True, capture_output=False, text=True)
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            print(f"{description} - COMPLETED ({elapsed:.1f}s)")
            return True
        else:
            print(f"{description} - FAILED")
            return False
    except Exception as e:
        print(f"{description} - ERROR: {e}")
        return False

def main():
    print(f"\n{'='*70}")
    print(f"COGNITIVE HEALTH COACH - ANALYSIS PIPELINE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    
    steps = [
        ("python util.py", "Step 1: Enriching CSV with temporal features"),
        ("python agent_1_classification.py", "Step 2: Agent 1 - Classifying activities (FQS)"),
        ("python agent_2_fragmentation.py", "Step 3: Agent 2A - Analyzing fragmentation (CSC)"),
        ("python agent_2_burnout.py", "Step 4: Agent 2B - Detecting burnout patterns"),
        ("python agent_3_synthesis.py", "Step 5: Agent 3 - Synthesizing health report"),
    ]
    
    completed = 0
    failed = 0
    
    for cmd, description in steps:
        if run_command(cmd, description):
            completed += 1
        else:
            failed += 1
            print(f"Continuing despite error...")
    
    # Final Report
    print(f"\n{'='*70}")
    print(f"PIPELINE COMPLETE")
    print(f"{'='*70}")
    print(f"Completed: {completed}/{len(steps)}")
    print(f"Failed: {failed}/{len(steps)}")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nOutput files generated:")
    print(f"   • activity_log_enriched01.csv")
    print(f"   • classified_activity01.csv")
    print(f"   • fragmented_activity01.csv")
    print(f"   • burnout_flags.json")
    print(f"   • final_health_report.json")
    print(f"\nRefresh your website to see updated metrics!")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()