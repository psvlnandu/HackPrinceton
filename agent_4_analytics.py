import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import openai
import plotly.graph_objects as go
from dotenv import load_dotenv

"""
Agent 4: Analytics Engine
Analyzes all activity data and generates:
- Energy Levels Throughout Day
- Cognitive Load Index
- Flow State Detection
- Work-Life Balance Monitor
- Burnout Prediction
- Predictive Health Score
"""

load_dotenv(override=True)

# Config
API_HOST = os.getenv("API_HOST", "github")
CLASSIFIED_FILE = "classified_activity01.csv"
ENRICHED_FILE = "activity_log_enriched01.csv"
BURNOUT_FILE = "burnout_flags.json"
ANALYTICS_OUTPUT = "analytics_report.json"


if API_HOST == "github":
    client = openai.OpenAI(base_url="https://models.github.ai/inference", api_key=os.environ["GITHUB_TOKEN"])
    MODEL = os.getenv("GITHUB_MODEL", "openai/gpt-4o")

else:
    client = openai.AsyncOpenAI(api_key=os.environ["OPENAI_KEY"])
    MODEL = os.environ["OPENAI_MODEL"]

# ===== LOAD DATA =====
def load_data():
    """Load all necessary data files"""
    try:
        classified = pd.read_csv(CLASSIFIED_FILE) if Path(CLASSIFIED_FILE).exists() else None
        enriched = pd.read_csv(ENRICHED_FILE) if Path(ENRICHED_FILE).exists() else None
        burnout = json.load(open(BURNOUT_FILE)) if Path(BURNOUT_FILE).exists() else {}
        return classified, enriched, burnout
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return None, None, {}

classified_df, enriched_df, burnout_data = load_data()

# ===== 1. ENERGY LEVELS THROUGHOUT DAY =====
def analyze_energy_levels(classified_df):
    """Analyze energy and productivity by hour of day"""
    print("📊 Analyzing Energy Levels...")
    
    if classified_df is None:
        return {}
    
    # Group by hour
    classified_df['Timestamp'] = pd.to_datetime(classified_df['Timestamp'])
    classified_df['Hour'] = classified_df['Timestamp'].dt.hour
    
    hourly_stats = []
    for hour in range(24):
        hour_data = classified_df[classified_df['Hour'] == hour]
        if len(hour_data) == 0:
            continue
        
        total = len(hour_data)
        high_load = len(hour_data[hour_data['Category'] == 'High Load'])
        comm = len(hour_data[hour_data['Category'] == 'Communication'])
        low_load = len(hour_data[hour_data['Category'] == 'Low Load'])
        
        energy_pct = (high_load / total * 100) if total > 0 else 0
        context_switches = hour_data['Switching_Rate_Per_Hour'].mean() if 'Switching_Rate_Per_Hour' in hour_data.columns else 0
        
        hourly_stats.append({
            "hour": hour,
            "energy": round(energy_pct, 1),
            "high_load_pct": round(high_load / total * 100, 1),
            "comm_pct": round(comm / total * 100, 1),
            "low_load_pct": round(low_load / total * 100, 1),
            "context_switches": round(context_switches, 2),
            "activity_count": total
        })
    
    if not hourly_stats:
        return {}
    
    hourly_stats.sort(key=lambda x: x['energy'], reverse=True)
    peak_hours = [s['hour'] for s in hourly_stats[:2]]
    low_hours = [s['hour'] for s in hourly_stats[-2:]]
    peak_energy = hourly_stats[0]['energy']
    low_energy = hourly_stats[-1]['energy']
    
    return {
        "peak_hours": peak_hours,
        "peak_energy": peak_energy,
        "low_hours": low_hours,
        "low_energy": low_energy,
        "hourly_data": hourly_stats
    }

# ===== 2. COGNITIVE LOAD INDEX =====
def calculate_cognitive_load(classified_df):
    """Calculate current cognitive load"""
    print("🧠 Calculating Cognitive Load Index...")
    
    if classified_df is None or len(classified_df) == 0:
        return {}
    
    # Get last hour of data
    classified_df['Timestamp'] = pd.to_datetime(classified_df['Timestamp'])
    last_hour = classified_df[classified_df['Timestamp'] >= datetime.now() - timedelta(hours=1)]
    
    if len(last_hour) == 0:
        last_hour = classified_df.tail(12)  # Last ~60 seconds
    
    total = len(last_hour)
    high_load_count = len(last_hour[last_hour['Category'] == 'High Load'])
    comm_count = len(last_hour[last_hour['Category'] == 'Communication'])
    low_load_count = len(last_hour[last_hour['Category'] == 'Low Load'])
    
    # Context switches in last hour
    context_switches = last_hour['Switching_Rate_Per_Hour'].mean() if 'Switching_Rate_Per_Hour' in last_hour.columns else 0
    
    # Cognitive load calculation (0-10 scale)
    # High load adds cognitive demand, low load reduces it
    cognitive_load = (high_load_count / total * 10) + (comm_count / total * 4) - (low_load_count / total * 2)
    cognitive_load = min(10, max(0, cognitive_load))
    
    status = "HIGH" if cognitive_load > 7 else "MODERATE" if cognitive_load > 4 else "LOW"
    
    return {
        "current": round(cognitive_load, 1),
        "status": status,
        "high_load_pct": round(high_load_count / total * 100, 1),
        "comm_pct": round(comm_count / total * 100, 1),
        "low_load_pct": round(low_load_count / total * 100, 1),
        "context_switches": round(context_switches, 2)
    }

# ===== 3. FLOW STATE DETECTION =====
def detect_flow_state(classified_df):
    """Detect flow state sessions"""
    print("🔥 Detecting Flow State...")
    
    if classified_df is None or len(classified_df) < 12:
        return {}
    
    classified_df['Timestamp'] = pd.to_datetime(classified_df['Timestamp'])
    classified_df = classified_df.sort_values('Timestamp')
    
    flow_sessions = []
    in_flow = False
    flow_start = None
    flow_app = None
    flow_count = 0
    
    for idx, row in classified_df.iterrows():
        if row['Category'] == 'High Load':
            if not in_flow:
                in_flow = True
                flow_start = row['Timestamp']
                flow_app = row['Window_Title'][:30]
                flow_count = 1
            else:
                flow_count += 1
        else:
            if in_flow and flow_count >= 12:  # At least 60 seconds in flow
                duration_min = flow_count * 5 / 60
                if duration_min >= 5:  # At least 5 minutes
                    flow_sessions.append({
                        "start": flow_start.strftime("%I:%M %p"),
                        "duration_minutes": round(duration_min, 0),
                        "app": flow_app,
                        "confidence": min(0.95, 0.6 + (flow_count / 100))
                    })
            in_flow = False
            flow_count = 0
    
    return {
        "flow_detected": len(flow_sessions) > 0,
        "session_count": len(flow_sessions),
        "sessions": flow_sessions[-3:] if flow_sessions else []  # Last 3 sessions
    }

# ===== 4. WORK-LIFE BALANCE MONITOR =====
def calculate_work_life_balance(classified_df):
    """Calculate work-life balance metrics"""
    print("⚖️ Analyzing Work-Life Balance...")
    
    if classified_df is None or len(classified_df) == 0:
        return {}
    
    classified_df['Timestamp'] = pd.to_datetime(classified_df['Timestamp'])
    
    # Today's stats
    today = datetime.now().date()
    today_data = classified_df[classified_df['Timestamp'].dt.date == today]
    
    if len(today_data) == 0:
        return {}
    
    total_time = len(today_data) * 5 / 3600  # Convert to hours
    high_load_time = len(today_data[today_data['Category'] == 'High Load']) * 5 / 3600
    break_time = len(today_data[today_data['Category'] == 'Low Load']) * 5 / 3600
    
    balance_score = (break_time / total_time * 10) if total_time > 0 else 0
    
    status = "BALANCED" if 6 <= total_time <= 9 else "OVERWORKING" if total_time > 9 else "UNDERWORKING"
    
    return {
        "total_hours": round(total_time, 1),
        "work_hours": round(high_load_time, 1),
        "break_hours": round(break_time, 1),
        "target_hours": 8,
        "balance_score": round(min(10, balance_score), 1),
        "status": status,
        "excess_hours": round(max(0, total_time - 8), 1)
    }

# ===== 5. BURNOUT PREDICTION =====
def predict_burnout_trend(burnout_data):
    """Predict burnout trajectory"""
    print("📈 Predicting Burnout Trend...")
    
    current_burnout = burnout_data.get("burnout_risk_score", 5)
    
    # Simulate trend (in production, would use historical data)
    # For now, use current as proxy
    trajectory = "STABLE"
    if current_burnout > 7:
        trajectory = "RISING"
        days_to_critical = max(1, int((10 - current_burnout) / 0.3))
    elif current_burnout > 5:
        trajectory = "MODERATE"
        days_to_critical = 7
    else:
        trajectory = "IMPROVING"
        days_to_critical = 14
    
    predicted_7days = min(10, current_burnout + (0.3 if trajectory == "RISING" else -0.2))
    
    return {
        "current": round(current_burnout, 1),
        "trajectory": trajectory,
        "days_to_critical": days_to_critical,
        "predicted_7days": round(predicted_7days, 1),
        "risk_level": "CRITICAL" if current_burnout > 8 else "HIGH" if current_burnout > 6 else "MODERATE"
    }

# ===== 6. PREDICTIVE HEALTH SCORE =====
def calculate_predictive_health_score(cognitive_load, work_life_balance, burnout_pred, flow_state, energy):
    """Calculate overall predictive health score"""
    print("❤️ Calculating Predictive Health Score...")
    
    # Component scores (0-10)
    burnout_component = 10 - burnout_pred.get("current", 5)
    balance_component = work_life_balance.get("balance_score", 5)
    load_component = 10 - cognitive_load.get("current", 5)
    recovery_component = balance_component * 0.8  # Related to balance
    flow_component = 5 + (len(flow_state.get("sessions", [])) * 1.5)  # More flow = healthier
    
    # Weighted average
    components = {
        "burnout": round(burnout_component, 1),
        "cognitive_load": round(load_component, 1),
        "work_life_balance": round(balance_component, 1),
        "recovery": round(recovery_component, 1),
        "flow_state": round(min(10, flow_component), 1)
    }
    
    overall_score = (
        burnout_component * 0.3 +
        balance_component * 0.25 +
        load_component * 0.2 +
        flow_component * 0.15 +
        recovery_component * 0.1
    ) / 1.0
    
    overall_score = round(min(10, max(0, overall_score)), 1)
    
    status = "CRITICAL" if overall_score < 3 else "HIGH_RISK" if overall_score < 5 else "MODERATE" if overall_score < 7 else "HEALTHY"
    
    # Prediction
    projected_7days = overall_score - 1 if burnout_pred["trajectory"] == "RISING" else overall_score + 0.5
    
    return {
        "overall": overall_score,
        "status": status,
        "components": components,
        "projection_7days": round(min(10, max(0, projected_7days)), 1),
        "recommendation": burnout_pred.get("risk_level", "MONITOR")
    }

# ===== GENERATE REPORT WITH LLM =====
def generate_ai_insights(energy, cognitive_load, flow_state, work_life_balance, burnout_pred, health_score):
    """Use LLM to generate actionable insights"""
    print("🤖 Generating AI Insights...")
    
    prompt = f"""
    Analyze this cognitive health data and provide BRIEF, ACTIONABLE insights:
    
    Energy Levels: Peak at {energy.get('peak_hours', [])} hours (Energy: {energy.get('peak_energy', 0)}%)
    Cognitive Load: {cognitive_load.get('current', 0)}/10 ({cognitive_load.get('status', 'UNKNOWN')})
    Flow State: {flow_state.get('session_count', 0)} sessions detected
    Work-Life Balance: {work_life_balance.get('total_hours', 0)}h (Status: {work_life_balance.get('status', 'UNKNOWN')})
    Burnout: {burnout_pred.get('current', 0)}/10 ({burnout_pred.get('trajectory', 'UNKNOWN')})
    Health Score: {health_score.get('overall', 0)}/10
    
    Provide 3-4 specific, actionable recommendations. Be concise and direct.
    """
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Could not generate insights: {str(e)}"

# ===== MAIN EXECUTION =====
def main():
    print("\n" + "="*60)
    print("AGENT 4: ANALYTICS ENGINE")
    print("="*60 + "\n")
    
    # Calculate all metrics
    energy = analyze_energy_levels(classified_df)
    cognitive_load = calculate_cognitive_load(classified_df)
    flow_state = detect_flow_state(classified_df)
    work_life_balance = calculate_work_life_balance(classified_df)
    burnout_pred = predict_burnout_trend(burnout_data)
    health_score = calculate_predictive_health_score(cognitive_load, work_life_balance, burnout_pred, flow_state, energy)
    
    # Generate AI insights
    ai_insights = generate_ai_insights(energy, cognitive_load, flow_state, work_life_balance, burnout_pred, health_score)
    
    # Compile report
    report = {
        "timestamp": datetime.now().isoformat(),
        "energy_levels": energy,
        "cognitive_load": cognitive_load,
        "flow_state": flow_state,
        "work_life_balance": work_life_balance,
        "burnout_prediction": burnout_pred,
        "predictive_health_score": health_score,
        "ai_insights": ai_insights
    }
    
    # Save report
    with open(ANALYTICS_OUTPUT, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ Analytics report saved to: {ANALYTICS_OUTPUT}")
    print("\n" + "="*60)
    print(f"HEALTH SCORE: {health_score.get('overall', 0)}/10 ({health_score.get('status', 'UNKNOWN')})")
    print(f"Burnout: {burnout_pred.get('current', 0)}/10 ({burnout_pred.get('trajectory', 'UNKNOWN')})")
    print(f"Cognitive Load: {cognitive_load.get('current', 0)}/10 ({cognitive_load.get('status', 'UNKNOWN')})")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()