#!/usr/bin/env python3
"""
PIPELINE ORCHESTRATOR - PARALLEL EXECUTION
Runs the analysis pipeline with parallel execution where possible:

Dependency Graph:
  util.py (required first)
    |
    +-- Agent 1: Classification
    +-- Agent 2A: Fragmentation    } Run in parallel
    +-- Agent 2B: Burnout Detection
    |
    +-- Agent 4: Advanced Analytics
    |
    +-- Agent 3: Health Synthesis (final)

Usage: python pipeline.py
"""

import subprocess
import sys
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class PipelineExecutor:
    def __init__(self):
        self.results = {}
        self.lock = threading.Lock()
    
    def run_command(self, cmd, description, stage_name):
        """Run a command in a thread and track results"""
        print(f"[{stage_name}] Starting: {description}")
        
        start_time = time.time()
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
            elapsed = time.time() - start_time
            
            with self.lock:
                if result.returncode == 0:
                    self.results[stage_name] = {
                        'status': 'SUCCESS',
                        'time': elapsed,
                        'description': description
                    }
                    print(f"[{stage_name}] COMPLETED ({elapsed:.1f}s)")
                    return True
                else:
                    self.results[stage_name] = {
                        'status': 'FAILED',
                        'time': elapsed,
                        'description': description,
                        'error': result.stderr
                    }
                    print(f"[{stage_name}] FAILED ({result.stderr[:100]})")
                    return False
        
        except subprocess.TimeoutExpired:
            with self.lock:
                self.results[stage_name] = {
                    'status': 'TIMEOUT',
                    'description': description
                }
            print(f"[{stage_name}] TIMEOUT (>120s)")
            return False
        
        except Exception as e:
            with self.lock:
                self.results[stage_name] = {
                    'status': 'ERROR',
                    'description': description,
                    'error': str(e)
                }
            print(f"[{stage_name}] ERROR: {e}")
            return False

def main():
    print("\n" + "="*70)
    print("COGNITIVE HEALTH COACH - ANALYSIS PIPELINE")
    print("Started at:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("="*70 + "\n")
    
    executor = PipelineExecutor()
    
    # STAGE 1: Initial Enrichment (required first)
    print("[STAGE 1] Running initial data enrichment...")
    success = executor.run_command(
        "python util.py",
        "Enriching CSV with temporal features",
        "UTIL"
    )
    
    if not success:
        print("\nFATAL: Initial enrichment failed. Cannot proceed.")
        return
    
    print("\n[STAGE 2] Running parallel agent analysis...\n")
    
    # STAGE 2: Parallel agents (1, 2A, 2B)
    parallel_tasks = [
        ("python agent_1_RAG_Classification.py", "Agent 1 - RAG Classifying activities", "AGENT1"),
        ("python agent_2_fragmentation.py", "Agent 2A - Analyzing fragmentation", "AGENT2A"),
        ("python agent_2_burnout.py", "Agent 2B - Detecting burnout patterns", "AGENT2B"),
    ]
    
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = []
        for cmd, desc, stage in parallel_tasks:
            future = pool.submit(executor.run_command, cmd, desc, stage)
            futures.append((future, stage))
        
        for future, stage in futures:
            future.result()
    
    print("\n[STAGE 2] Parallel analysis complete\n")
    
    # Check if critical agents succeeded
    required_agents = ['AGENT1', 'AGENT2A', 'AGENT2B']
    if not all(executor.results.get(agent, {}).get('status') == 'SUCCESS' for agent in required_agents):
        print("WARNING: Some agents failed, but continuing with available data...\n")
    
    # STAGE 3: Advanced Analytics (depends on stages 1-2)
    print("[STAGE 3] Running advanced analytics...\n")
    executor.run_command(
        "python agent_4_analytics.py",
        "Agent 4 - Advanced Analytics",
        "AGENT4"
    )
    
    print("\n")
    
    # STAGE 4: Final synthesis (depends on all previous)
    print("[STAGE 4] Running health synthesis...\n")
    executor.run_command(
        "python agent_3_synthesis.py",
        "Agent 3 - Synthesizing health report",
        "AGENT3"
    )
    
    # Final Report
    print("\n" + "="*70)
    print("PIPELINE EXECUTION COMPLETE")
    print("="*70)
    
    total_time = sum(r.get('time', 0) for r in executor.results.values() if isinstance(r, dict))
    
    successful = sum(1 for r in executor.results.values() if isinstance(r, dict) and r.get('status') == 'SUCCESS')
    failed = sum(1 for r in executor.results.values() if isinstance(r, dict) and r.get('status') != 'SUCCESS')
    
    print(f"\nResults Summary:")
    print(f"  Total stages: {len(executor.results)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total time: {total_time:.1f}s")
    
    print(f"\nDetailed Results:")
    for stage, result in executor.results.items():
        if isinstance(result, dict):
            status = result.get('status', 'UNKNOWN')
            time_taken = result.get('time', 0)
            print(f"  [{stage}] {status} ({time_taken:.1f}s) - {result.get('description', '')}")
    
  
    
if __name__ == "__main__":
    main()