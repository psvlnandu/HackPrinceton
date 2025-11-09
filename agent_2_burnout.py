import pandas as pd
import json
import os
import asyncio
from datetime import datetime
from pydantic import BaseModel, Field
import openai
from dotenv import load_dotenv

load_dotenv(override=True)

"""
AGENT 2B: BURNOUT PATTERN DETECTOR (LLM-POWERED)
Uses OpenAI LLM to analyze temporal patterns and detect burnout risk.
Input: activity_log_enriched01.csv
Output: burnout_flags.json
"""

INPUT_FILE = "activity_log_enriched01.csv"
OUTPUT_FILE = "burnout_flags.json"
CONCURRENCY_LIMIT = 10

# ===== LLM SETUP =====
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "github":
    client = openai.OpenAI(base_url="https://models.github.ai/inference", api_key=os.environ["GITHUB_TOKEN"])
    MODEL_NAME = os.getenv("GITHUB_MODEL", "openai/gpt-4o")
else:
    client = openai.OpenAI(api_key=os.environ["OPENAI_KEY"])
    MODEL_NAME = os.environ["OPENAI_MODEL"]

print(f'model name set to {MODEL_NAME}')

# ===== PYDANTIC MODELS =====

class BurnoutFlag(BaseModel):
    category: str = Field(description="e.g., 'Fragmentation', 'Sleep Disruption', 'Overwork', 'Session Pattern'")
    severity: int = Field(description="1-10 scale, where 10 is critical burnout risk")
    message: str = Field(description="Clear explanation of the detected pattern")
    prescription: str = Field(description="One specific, actionable recommendation")

class BurnoutAnalysis(BaseModel):
    burnout_risk_score: float = Field(description="Overall burnout risk, 1-10 scale")
    risk_level: str = Field(description="One of: 'HEALTHY 🟢', 'MODERATE 🟡', 'HIGH 🔴', 'CRITICAL ⛔'")
    top_insights: list[str] = Field(description="3-5 key insights about the user's work pattern")
    flags: list[BurnoutFlag] = Field(description="List of detected burnout risk flags")


# ===== LLM CALL =====

def call_llm_for_burnout_analysis(metrics_summary: str, semaphore: asyncio.Semaphore) -> BurnoutAnalysis:
    """
    Call LLM to analyze temporal metrics and detect burnout patterns.
    """
    
    SYSTEM_PROMPT = """
You are an expert Cognitive Health & Burnout Prevention Specialist with deep knowledge of:
- Circadian rhythms and sleep science (Walker, 2017)
- Attention and context-switching (Ophir et al., 2009)
- Ultradian work cycles (Kleitman, 1961)
- Digital ergonomics and sustainable productivity

Your task: Analyze the provided work metrics and detect burnout risk patterns. Be specific and data-driven.
Return a structured analysis with severity scores and actionable prescriptions.
"""

    USER_PROMPT = f"""
Analyze these work metrics for burnout risk:

{metrics_summary}

Consider:
1. Is the switching rate sustainable? (Normal: 20-40/hr, High: 60+/hr, Critical: 100+/hr)
2. Are sessions too brief (constant micro-switches) or too long (no breaks)?
3. Is there evening/early morning work disrupting circadian rhythm?
4. What is the total work duration and distribution pattern?
5. What specific interventions would help this person?

Return a BurnoutAnalysis JSON with specific severity scores and personalized prescriptions.
"""

    tool_spec = {
        "type": "function",
        "function": {
            "name": "BurnoutAnalysis",
            "description": "Analyze work patterns and detect burnout risk",
            "parameters": BurnoutAnalysis.model_json_schema()
        }
    }

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT},
            ],
            tools=[tool_spec],
            tool_choice={"type": "function", "function": {"name": "BurnoutAnalysis"}},
        )
        
        tool_call = response.choices[0].message.tool_calls[0]
        arguments = tool_call.function.arguments
        
        return BurnoutAnalysis.model_validate_json(arguments)
    
    except Exception as e:
        print(f"LLM call failed: {e}")
        # Return safe default
        return BurnoutAnalysis(
            burnout_risk_score=5.0,
            risk_level="MODERATE 🟡",
            top_insights=["LLM analysis unavailable"],
            flags=[]
        )


# ===== METRIC EXTRACTION =====

def extract_metrics_summary(df: pd.DataFrame) -> str:
    """Extract key metrics from enriched data and format for LLM."""
    
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    
    total_hours = len(df) * 5 / 3600
    total_switches = (df['Window_Title'] != df['Window_Title'].shift(1)).sum()
    avg_switching_rate = df['Switching_Rate_Per_Hour'].mean()
    max_switching_rate = df['Switching_Rate_Per_Hour'].max()
    
    avg_session_seconds = df['Total_Session_Duration_Seconds'].mean()
    avg_session_minutes = avg_session_seconds / 60
    
    brief_session_pct = (df['Is_Brief_Session'].sum() / len(df)) * 100
    extended_session_pct = (df['Is_Extended_Session'].sum() / len(df)) * 100
    
    evening_work_pct = (df['Is_Evening'].sum() / len(df)) * 100
    early_morning_pct = (df['Is_Early_Morning'].sum() / len(df)) * 100
    
    by_hour = df.groupby('Hour_of_Day').size()
    hours_active = len(by_hour)
    
    time_buckets = df['Time_Bucket'].value_counts().to_dict()
    
    summary = f"""
WORK SESSION METRICS:
- Total logged time: {total_hours:.2f} hours
- Total window switches: {total_switches}
- Average switching rate: {avg_switching_rate:.1f} switches/hour
- Peak switching rate: {max_switching_rate:.1f} switches/hour
- Average session duration: {avg_session_minutes:.1f} minutes

SESSION PATTERNS:
- Brief sessions (<50% of average): {brief_session_pct:.1f}%
- Extended sessions (>200% of average): {extended_session_pct:.1f}%
- Unique windows detected: {df['Window_Title'].nunique()}

TEMPORAL PATTERNS:
- Evening work (after 6 PM): {evening_work_pct:.1f}%
- Early morning work (before 7 AM): {early_morning_pct:.1f}%
- Hours active: {hours_active}
- Time distribution: {time_buckets}

RECENT ACTIVITY INTENSITY:
- Max recent switching (last 15 min): {df['Switches_Last_15min'].max():.0f} switches
- Average unique windows in last 10 intervals: {df['Unique_Windows_Last_10'].mean():.1f}
"""
    
    return summary


# ===== MAIN EXECUTION =====

def run_burnout_detection():
    """Main execution function."""
    try:
        df = pd.read_csv(INPUT_FILE)
    except FileNotFoundError:
        print(f"ERROR: {INPUT_FILE} not found.")
        print(f"Make sure you ran: python util.py")
        return None
    
    print("--- Running Agent 2B: Burnout Pattern Detector (LLM-Powered) ---\n")
    
    # Extract metrics
    print("📊 Extracting metrics from enriched data...")
    metrics_summary = extract_metrics_summary(df)
    print(metrics_summary)
    
    # Call LLM for analysis
    print("\n🤖 Calling LLM for burnout analysis...")
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    analysis = call_llm_for_burnout_analysis(metrics_summary, semaphore)
    
    # ===== DISPLAY RESULTS =====
    print(f"\n{'='*70}")
    print(f"BURNOUT RISK SCORE: {analysis.burnout_risk_score}/10")
    print(f"RISK LEVEL: {analysis.risk_level}")
    print(f"{'='*70}\n")
    
    print("💡 KEY INSIGHTS:")
    for insight in analysis.top_insights:
        print(f"   • {insight}")
    
    if analysis.flags:
        print(f"\n🚨 DETECTED RISK FACTORS ({len(analysis.flags)} total):")
        for i, flag in enumerate(analysis.flags[:5], 1):  # Show top 5
            print(f"\n{i}. {flag.category} (Severity: {flag.severity}/10)")
            print(f"   📌 {flag.message}")
            print(f"   {flag.prescription}")
    
    # ===== SAVE REPORT =====
    report = {
        'timestamp': datetime.now().isoformat(),
        'burnout_risk_score': analysis.burnout_risk_score,
        'risk_level': analysis.risk_level,
        'top_insights': analysis.top_insights,
        'flags_detected': len(analysis.flags),
        'flags': [flag.model_dump() for flag in analysis.flags],
        'metrics_summary': metrics_summary
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(report, f, indent=2)
        
    return report


if __name__ == '__main__':
    run_burnout_detection()