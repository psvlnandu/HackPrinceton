from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json
import os
import subprocess
from pathlib import Path
from datetime import datetime

app = FastAPI()

# Allow React frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Point to your CSV files (adjust paths as needed)
CSV_PATHS = {
    "enriched": "../activity_log_enriched01.csv",
    "classified": "../classified_activity01.csv",
    "fragmented": "../fragmented_activity01.csv",
    "burnout": "../burnout_flags.json",
    "health_report": "../final_health_report.json",
}

def safe_read_csv(filepath):
    """Safely read CSV and return as JSON"""
    try:
        if not os.path.exists(filepath):
            return {"error": f"File not found: {filepath}"}
        
        df = pd.read_csv(filepath)
        return df.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}

def safe_read_json(filepath):
    """Safely read JSON file"""
    try:
        if not os.path.exists(filepath):
            return {"error": f"File not found: {filepath}"}
        
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

# ===== API ENDPOINTS =====

@app.get("/api/health")
async def health_check():
    """Simple health check"""
    return {"status": "✅ Backend is running"}

@app.get("/api/metrics")
async def get_metrics():
    """Get aggregated metrics from all data sources"""
    
    # Read enriched data
    enriched = safe_read_csv(CSV_PATHS["enriched"])
    classified = safe_read_csv(CSV_PATHS["classified"])
    burnout = safe_read_json(CSV_PATHS["burnout"])
    health_report = safe_read_json(CSV_PATHS["health_report"])
    
    if isinstance(enriched, list) and len(enriched) > 0:
        last_row = enriched[-1]
        total_hours = len(enriched) * 5 / 3600
        
        # Extract metrics
        metrics = {
            "total_hours": round(total_hours, 2),
            "fqs": last_row.get("FQS_Score", 0) if isinstance(last_row, dict) else 0,
            "csc": last_row.get("CSC_Score", 0) if isinstance(last_row, dict) else 0,
            "switching_rate": last_row.get("Switching_Rate_Per_Hour", 0) if isinstance(last_row, dict) else 0,
            "burnout_score": burnout.get("burnout_risk_score", 0) if isinstance(burnout, dict) else 0,
            "burnout_level": burnout.get("risk_level", "Unknown") if isinstance(burnout, dict) else "Unknown",
            "health_report": health_report if isinstance(health_report, dict) else {},
        }
        
        return metrics
    
    return {"error": "No data available"}

@app.get("/api/dashboard")
async def get_dashboard_data():
    """Get data for dashboard visualization"""
    
    classified = safe_read_csv(CSV_PATHS["classified"])
    enriched = safe_read_csv(CSV_PATHS["enriched"])
    
    if not isinstance(classified, list) or len(classified) == 0:
        return {"error": "No classified data available"}
    
    # Calculate breakdown
    categories = {}
    for row in classified:
        if isinstance(row, dict):
            cat = row.get("Category", "Unknown")
            categories[cat] = categories.get(cat, 0) + 1
    
    # Time distribution
    time_by_hour = {}
    if isinstance(enriched, list):
        for row in enriched:
            if isinstance(row, dict) and "Hour_of_Day" in row:
                hour = int(row["Hour_of_Day"])
                time_by_hour[hour] = time_by_hour.get(hour, 0) + 1
    
    return {
        "category_breakdown": categories,
        "time_distribution": time_by_hour,
        "total_entries": len(classified),
    }

@app.get("/api/settings")
async def get_settings():
    """Get user settings (default values for now)"""
    return {
        "break_notifications": True,
        "focus_reminders": True,
        "daily_goal_hours": 6,
        "focus_goal_percent": 80,
        "peak_hours": "9-12, 14-17",
    }

@app.post("/api/settings")
async def update_settings(settings: dict):
    """Save user settings (in future, save to database)"""
    # For now, just echo back
    return {"status": "saved", "settings": settings}

@app.get("/api/burnout-flags")
async def get_burnout_flags():
    """Get detailed burnout flags"""
    burnout = safe_read_json(CSV_PATHS["burnout"])
    if isinstance(burnout, dict) and "flags" in burnout:
        return {"flags": burnout["flags"]}
    return {"flags": []}

@app.post("/api/run-pipeline")
async def run_pipeline():
    """
    Trigger the complete analysis pipeline
    Runs: enrich → classify → fragment → burnout → synthesis
    """
    try:
        # Run the pipeline script
        result = subprocess.run(
            ["python", "pipeline.py"],
            capture_output=True,
            text=True,
            cwd=".."  # Go up one level to repo root
        )
        
        if result.returncode == 0:
            return {
                "status": "✅ Pipeline completed successfully",
                "timestamp": datetime.now().isoformat(),
                "output": result.stdout,
            }
        else:
            return {
                "status": "⚠️ Pipeline completed with errors",
                "error": result.stderr,
                "output": result.stdout,
            }
    except Exception as e:
        return {
            "status": "❌ Pipeline failed",
            "error": str(e),
        }