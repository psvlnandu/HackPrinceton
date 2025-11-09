import os
from pydantic import BaseModel, Field
import openai
from dotenv import load_dotenv
import pandas as pd
import time
import asyncio
"""
    Agent 1 (Classification) - 
    Uses LLM to categorize window titles into cognitive load buckets 
    (High Load/Communication/Low Load) and calculates Focus Quality Score (FQS)
"""
load_dotenv(override=True)

API_HOST = os.getenv("API_HOST", "github")
FILE_NAME = "activity_log_enriched01.csv"
CLASSIFIED_FILE_NAME = "classified_activity01.csv"
CONCURRENCY_LIMIT = 50 

if API_HOST == "github":
    client = openai.OpenAI(base_url="https://models.github.ai/inference", api_key=os.environ["GITHUB_TOKEN"])
    MODEL_NAME = os.getenv("GITHUB_MODEL", "openai/gpt-4o")

else:
    client = openai.AsyncOpenAI(api_key=os.environ["OPENAI_KEY"])
    MODEL_NAME = os.environ["OPENAI_MODEL"]

print(f'model name set to {MODEL_NAME}')
# Defines the three valid categories for the LLM to choose from


class ActivityClassification(BaseModel):
    category: str = Field(description="One of 'High Load', 'Communication', or 'Low Load'.")
    confidence_reason: str = Field(description="A brief explanation of why this window title belongs in the assigned category.")
    app_name: str = Field(description="The name of the application or platform (e.g., VSCode, Claude, Chrome, Slack, Codespaces)")
    app_type: str = Field(description="Type of app: 'Development', 'AI_Assistant', 'Browser', 'Communication', 'Editor', 'Other'")

SYSTEM_PROMPT = """
You are an expert cognitive workload classifier for knowledge workers.

Your task: Analyze window titles and classify each into ONE of three categories based on cognitive demand and work type.

CATEGORIES:

'High Load' - Deep, focused work requiring sustained attention and mental effort:
- Requires active creation, problem-solving, or complex thinking
- Examples: coding (VS Code, IDE), writing complex documents, design work (Photoshop, Blender, AutoCAD), data analysis, debugging, technical planning
- If someone is ACTIVELY WORKING on a task that requires concentration, it's HIGH LOAD

'Communication' - Reactive, interrupt-driven activities with low cognitive commitment:
- Designed for back-and-forth interaction
- Examples: Slack, Discord, Teams, Gmail, Outlook, Zoom, Meetings, social media while chatting
- Often context-switches and breaks focus

'Low Load' - Passive consumption or system tasks requiring minimal cognitive effort:
- No active creation or problem-solving
- Examples: casual browsing, Netflix, YouTube (watching), music players, file explorers, system settings
- Simple, routine actions

DECISION RULES (in order of importance):
1. PURPOSE over app name - "Claude for debugging" = HIGH LOAD (you're working), "ChatGPT scrolling" = LOW LOAD
2. If it involves CODING, DESIGN, ANALYSIS, PLANNING, DEBUGGING → HIGH LOAD
3. If it's COLLABORATIVE COMMUNICATION (Slack, Teams, Email) → COMMUNICATION
4. If it's PASSIVE CONSUMPTION (YouTube, Netflix, browsing) → LOW LOAD
5. Ambiguous cases: "Is the user actively creating/solving something?" → HIGH LOAD. "Passively consuming?" → LOW LOAD

Be concise in your reasoning. Classify with confidence - the LLM knows the difference between work and play.
"""

async def call_llm_for_classification_with_retry(title: str, semaphore: asyncio.Semaphore, max_retries: int = 5) -> ActivityClassification:
    """Calls the LLM API safely within the concurrency limit and retries on failure."""
    USER_PROMPT = f"Classify the following Window Title: '{title}'"
    
    tool_spec = {
        "type": "function",
        "function": {
            "name": "ActivityClassification",
            "description": "Classify the user's desktop activity based on the window title.",
            "parameters": ActivityClassification.model_json_schema()
        }
    }
    async with semaphore:
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    await asyncio.sleep(1.0 * (2 ** attempt))
                
                response = await client.chat.completions.create( 
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": USER_PROMPT},
                    ],
                    tools=[tool_spec],
                    tool_choice={"type": "function", "function": {"name": "ActivityClassification"}},
                    temperature=0.3,  # More deterministic for classification
                )
                tool_call = response.choices[0].message.tool_calls[0]
                arguments = tool_call.function.arguments
                
                return ActivityClassification.model_validate_json(arguments)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"❌ FAILED: '{title[:40]}...' after {max_retries} attempts")
                    return ActivityClassification(
                        category='UNCLASSIFIED_API_FAIL', 
                        confidence_reason=f"API error: {str(e)[:50]}"
                    )
    
    return ActivityClassification(category='UNCLASSIFIED_ERROR', confidence_reason="Unknown error")

async def agent_1_classify_and_calculate_async():
    """Main function to orchestrate async classification."""
    print(f"--- Running Agent 1: Classification using {MODEL_NAME} ---\n")
    
    try:
        df = pd.read_csv(FILE_NAME)
        df = df.dropna(subset=['Window_Title']) 
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    except Exception as e:
        print(f"❌ Error reading {FILE_NAME}: {e}")
        return
    
    unique_titles = df['Window_Title'].unique()
    print(f"📊 Found {len(unique_titles)} unique titles to classify out of {len(df)} total entries\n")
    
    # Create classification tasks
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    classification_tasks = [call_llm_for_classification_with_retry(title, semaphore) for title in unique_titles]
    
    print(f"🔄 Starting async classification (concurrency: {CONCURRENCY_LIMIT})...")
    results = await asyncio.gather(*classification_tasks)
    
    # Create classification cache
    classification_cache = {title: result for title, result in zip(unique_titles, results)}
    
    # Apply classifications to DataFrame
    df['Category'] = df['Window_Title'].map(lambda x: classification_cache.get(x).category)
    df['Confidence_Reason'] = df['Window_Title'].map(lambda x: classification_cache.get(x).confidence_reason)
    df['App_Name'] = df['Window_Title'].map(lambda x: classification_cache.get(x).app_name)
    df['App_Type'] = df['Window_Title'].map(lambda x: classification_cache.get(x).app_type)
    
    print("✅ Classification complete!\n")
    
    # ===== CALCULATE METRICS =====
    df['Duration_Seconds'] = 5  # Each row = 5 seconds
    
    total_time = df['Duration_Seconds'].sum()
    category_times = df.groupby('Category')['Duration_Seconds'].sum()
    
    high_load_time = category_times.get('High Load', 0)
    comm_time = category_times.get('Communication', 0)
    low_load_time = category_times.get('Low Load', 0)
    
    # FQS Calculation: % of time spent in High Load (deep work)
    fqs_score = (high_load_time / total_time * 100) if total_time > 0 else 0
    
    # Add FQS to DataFrame for downstream agents
    df['FQS_Score'] = fqs_score
    
    # Calculate hour of day for Energy Levels agent
    df['Hour_of_Day'] = df['Timestamp'].dt.hour
    
    
    # Save for downstream agents
    df.to_csv(CLASSIFIED_FILE_NAME, index=False)

if __name__ == '__main__':
    try:
        asyncio.run(agent_1_classify_and_calculate_async())
    except ImportError as e:
        print(f"ERROR: Missing packages - {e}")
        print("Run: pip install pandas pydantic openai python-dotenv")
    except Exception as e:
        if "OPENAI_KEY" in str(e):
            print(f"FATAL: {e}")
            print("Set OPENAI_KEY in .env or environment variables")
        else:
            print(f"FATAL: {e}")