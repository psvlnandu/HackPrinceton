import os
import pandas as pd
import openai
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import json
"""
    Agent 3 (Health Synthesis) - 
    Synthesizes Focus Quality Score (FQS) and Context Switch Cost (CSC) 
    into a final Digital Ergonomic Risk (DER) score with personalized recommendations.
    RAG-grounded LLM generates personalized health reports with risk scores and prescriptions
"""
load_dotenv(override=True)

API_HOST = os.getenv("API_HOST", "github")
FILE_NAME = "activity_log01.csv"
CLASSIFIED_FILE_NAME = "classified_activity01.csv"
CONCURRENCY_LIMIT = 50 

if API_HOST == "github":
    client = openai.OpenAI(base_url="https://models.github.ai/inference", api_key=os.environ["GITHUB_TOKEN"])
    MODEL_NAME = os.getenv("GITHUB_MODEL", "openai/gpt-4o")

else:
    # client = openai.AsyncOpenAI(api_key=os.environ["OPENAI_KEY"])
    client = openai.OpenAI(api_key=os.environ["OPENAI_KEY"])
    MODEL_NAME = os.environ["OPENAI_MODEL"]

print(f'model is set {MODEL_NAME}')
INPUT_FILE = "fragmented_activity01.csv"


class HealthReport(BaseModel):
    """Structured data model for the final health synthesis report."""
    risk_score_der: int = Field(description="The final Digital Ergonomic Risk (DER) score, scaled from 1 (Low Risk) to 10 (High Risk).")
    narrative_summary: str = Field(description="A concise, professional summary explaining the user's focus quality and fragmentation.")
    actionable_prescription: str = Field(description="One specific, immediate, non-generic health action based on the scores and RAG rules.")
# --- Functions (The LLM Call Logic) ---

def generate_final_json_output(report_data: HealthReport):
    """Saves the LLM's structured Pydantic output to a clean JSON file."""
    # Use model_dump_json to serialize the Pydantic object cleanly
    json_content = report_data.model_dump_json(indent=4)
    GLOBAL_OUTPUT_FILE = "final_health_report.json"
    with open(GLOBAL_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(json_content)
        
    print(f"\n✅ Report Generation Complete!")
    print(f"Final analysis saved to: {GLOBAL_OUTPUT_FILE}")
    print("\n--- JSON REPORT SNIPPET ---")
    # Print the first 500 characters for quick confirmation
    print(json_content[:500] + "\n...")

def agent_3_health_synthesis():
    print(f"--- Running Agent 3: Health Synthesis (LLM/RAG Reasoning) ---")
    
    try:
        df = pd.read_csv(INPUT_FILE)
    except FileNotFoundError:
        print(f"FATAL ERROR: Input file not found at '{INPUT_FILE}'. Please ensure Agent 2 ran successfully.")
        return

    # Extract the two core metrics (FQS and CSC) from the last row
    last_row = df.iloc[-1]
    fqs_score = last_row['FQS_Score']
    csc_score = last_row['CSC_Score']
    total_time_sec = df['Duration_Seconds'].sum() 
    total_time_min = total_time_sec / 60
    
    # --- RAG Rules (The Grounding Context) ---
    RAG_RULES = """
    Based on best practices in cognitive psychology and deep work:
    1. High Load activity below 65% of productive time indicates reactive workflow and poor planning.
    2. Context Switch Cost (CSC) above 1.5 seconds per hour is a HIGH neurological strain warning.
    3. FQS above 85% is excellent; focus on optimizing deep work block duration instead of fragmentation.
    4. If High Load time is high (over 45 minutes) and CSC is low, recommend sustaining focus with a scheduled 10-minute analog (non-digital) break.
    5. If FQS is low and CSC is high, the user is highly reactive; recommend time-blocking Communication apps.
    """

    # 1. Prepare the LLM Prompt
    METRICS_CONTEXT = f"""
    ANALYSIS METRICS:
    - Total Logged Duration: {total_time_min:.2f} minutes.
    - Focus Quality Score (FQS): {fqs_score:.2f}% (Percentage of deep work time in productive time).
    - Context Switch Cost (CSC): {csc_score:.2f} seconds (Normalized neurological cost per hour).
    """

    # The prompt explicitly asks for JSON and references the metrics/rules
    SYSTEM_PROMPT = f"""
    You are a professional Cognitive Health Consultant. Your task is to generate a highly specific, personalized health report by synthesizing the provided RAG_RULES and the user's METRICS_CONTEXT.
    
    RAG_RULES: {RAG_RULES}
    METRICS_CONTEXT: {METRICS_CONTEXT}
    
    Your response MUST be a single, flat JSON object that STRICTLY adheres to the following structure. 
    DO NOT include any root key like 'HealthReport'. The fields must be: 'risk_score_der' (int), 'narrative_summary' (string), and 'actionable_prescription' (string).
    """
    
    print(METRICS_CONTEXT)
    # 2. Call LLM with Structured Output (Using robust JSON format)
    # --- START OF MISSING LOGIC BLOCK ---
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}],
            response_format={"type": "json_object"} 
        )
        
        # Extract the raw JSON string from the response
        raw_json_string = response.choices[0].message.content
        
        # Validate and parse the output using Pydantic
        report_data = HealthReport.model_validate_json(raw_json_string) 

        generate_final_json_output(report_data)

    except Exception as e:
        print(f"\nFATAL ERROR during LLM Synthesis: {e}")
        if 'JSONDecodeError' in str(e) or 'model_validate_json' in str(e):
            print(f"JSON Structure Failure. Raw LLM output was:\n{raw_json_string}")
        print(f"exception:\n{e}")
    # --- END OF MISSING LOGIC BLOCK ---

if __name__ == '__main__':
    agent_3_health_synthesis()