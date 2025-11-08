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
FILE_NAME = "activity_log01.csv"
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

SYSTEM_PROMPT = """
You are an expert cognitive workload classifier. Your task is to analyze user-provided window titles and categorize them into one of the three classes: 'High Load', 'Communication', or 'Low Load'. 
Use relational and semantic reasoning. For example:
- VS Code, terminals, and Notion planning are 'High Load' (Deep, complex work).
- Email, Discord, and Slack are 'Communication' (Reactive, interrupt-driven).
- Simple web browsing or media launchers are 'Low Load'.
You MUST return your answer in the specified JSON format.
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
                    # Exponential backoff using asyncio.sleep
                    await asyncio.sleep(1.0 * (2 ** attempt)) 
                
                # *** CRUCIAL FIX: Use await for the asynchronous client call ***
                response = await client.chat.completions.create( 
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": USER_PROMPT},
                    ],
                    tools=[tool_spec],
                    tool_choice={"type": "function", "function": {"name": "ActivityClassification"}},
                )

                tool_call = response.choices[0].message.tool_calls[0]
                arguments = tool_call.function.arguments
                
                return ActivityClassification.model_validate_json(arguments)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"FAILED classification for '{title[:30]}...' after {max_retries} attempts.")
                    return ActivityClassification(
                        category='UNCLASSIFIED_API_FAIL', 
                        confidence_reason=f"API failed after {max_retries} retries: {e}"
                    )
    return ActivityClassification(category='UNCLASSIFIED_ERROR', confidence_reason="Unknown error during classification.")


async def agent_1_classify_and_calculate_async():
    """Main function to orchestrate the asynchronous classification."""
    print(f"--- Running Agent 1: ASYNCHRONOUS Classification using {MODEL_NAME} ---")
    
    try:
        df = pd.read_csv(FILE_NAME)
        df = df.dropna(subset=['Window_Title']) 
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    except Exception as e:
        print(f"Error reading {FILE_NAME}: {e}")
        return

    unique_titles = df['Window_Title'].unique()
    
    print(f"Found {len(unique_titles)} unique titles to classify out of {len(df)} total log entries.")
    print(f"Starting classification with concurrency limit of {CONCURRENCY_LIMIT}...")

    # Create tasks for all unique titles
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    # Tasks are created using the async function
    classification_tasks = [call_llm_for_classification_with_retry(title, semaphore) for title in unique_titles]

    # **CRUCIAL FIX 4: Run tasks concurrently using asyncio.gather**
    results = await asyncio.gather(*classification_tasks)
    
    # Create cache from results
    classification_cache = {title: result for title, result in zip(unique_titles, results)}
        
    # Apply results back to the main DataFrame
    df['Category'] = df['Window_Title'].map(lambda x: classification_cache.get(x).category)
    df['Confidence_Reason'] = df['Window_Title'].map(lambda x: classification_cache.get(x).confidence_reason)

    print("\nClassification complete.")

    # 2. Calculate Metrics
    df['Duration_Seconds'] = 5 
    
    total_time = df['Duration_Seconds'].sum()
    category_times = df.groupby('Category')['Duration_Seconds'].sum()

    high_load_time = category_times.get('High Load', 0)
    comm_time = category_times.get('Communication', 0)
    
    # FQS Calculation
    productive_time = high_load_time + comm_time
    fqs_score = (high_load_time / productive_time) * 100 if productive_time > 0 else 0
    
    # --- INSIGHT 1: Focus Quality Score (FQS) ---
    # We add FQS_Score to the DataFrame before saving for Agent 2 to reuse
    df['FQS_Score'] = fqs_score
    
    print("\n--- Insight 1: Focus Quality Score (FQS) ---")
    print(f"Total Logged Time: {total_time / 3600:.2f} hours")
    print(f"High Load (Deep Work) Time: {high_load_time / 60:.2f} minutes")
    print(f"Communication (Reactive) Time: {comm_time / 60:.2f} minutes")
    print(f"FQS (Focus Quality Score, higher is better): {fqs_score:.2f}%")
    
    # Save the classified data for Agent 2
    df.to_csv(CLASSIFIED_FILE_NAME, index=False)
    print(f"\nClassification data saved to: {CLASSIFIED_FILE_NAME}")


if __name__ == '__main__':
    try:
        # Check for necessary packages visually (the runtime environment handles imports, but this helps)
        import sys
        if 'pandas' not in sys.modules or 'openai' not in sys.modules:
             pass 
        asyncio.run(agent_1_classify_and_calculate_async())
        
    except ImportError:
        print("\nERROR: Required Python packages not found. Please ensure you ran: pip install pandas pydantic openai\n")
    except Exception as e:
        if "OPENAI_KEY environment variable not set" in str(e):
             print(f"\nFATAL ERROR: {e}")
             print("Please set your OPENAI_KEY in your environment variables or in the .env file.")
        else:
             print(f"\nFATAL ERROR: {e}")