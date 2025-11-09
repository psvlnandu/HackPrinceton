import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
import openai
from dotenv import load_dotenv
import faiss

"""
Agent 1: FAISS-Accelerated RAG Classification
Uses FAISS vector DB for instant semantic search + batch LLM classification
"""

load_dotenv(override=True)

API_HOST = os.getenv("API_HOST", "openai")
FILE_NAME = "activity_log_enriched01.csv"
CLASSIFIED_FILE_NAME = "classified_activity01.csv"
FAISS_INDEX_FILE = "classification_faiss.index"
FAISS_METADATA_FILE = "classification_metadata.json"

if API_HOST == "github":
    client = openai.OpenAI(base_url="https://models.github.ai/inference", api_key=os.environ["GITHUB_TOKEN"])
    MODEL_NAME = os.getenv("GITHUB_MODEL", "openai/gpt-4o")
else:
    client = openai.OpenAI(api_key=os.environ.get("OPENAI_KEY"))
    MODEL_NAME = "gpt-4o-mini"

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

print(f"Classification model: {MODEL_NAME}")
print(f"Embedding model: {EMBEDDING_MODEL}\n")

# ===== FAISS INDEX MANAGEMENT =====
def create_faiss_index():
    """Create new FAISS index"""
    return faiss.IndexFlatL2(EMBEDDING_DIM)

def load_or_create_faiss():
    """Load existing FAISS index or create new one"""
    if Path(FAISS_INDEX_FILE).exists() and Path(FAISS_METADATA_FILE).exists():
        print(f"Loading FAISS index from {FAISS_INDEX_FILE}...")
        index = faiss.read_index(FAISS_INDEX_FILE)
        with open(FAISS_METADATA_FILE, "r") as f:
            metadata = json.load(f)
        print(f"Loaded {len(metadata)} classifications in FAISS\n")
        return index, metadata
    else:
        print("Creating new FAISS index...\n")
        return create_faiss_index(), {}

def save_faiss_index(index, metadata):
    """Save FAISS index and metadata"""
    faiss.write_index(index, FAISS_INDEX_FILE)
    with open(FAISS_METADATA_FILE, "w") as f:
        json.dump(metadata, f)

# ===== EMBEDDING GENERATION =====
def get_embedding(text):
    """Get embedding for text"""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=str(text)
    )
    return np.array(response.data[0].embedding, dtype=np.float32)

# ===== FAISS SEARCH =====
def search_faiss(query_embedding, index, metadata, k=3):
    """Search FAISS for similar titles"""
    if len(metadata) == 0:
        return []
    
    query = np.array([query_embedding], dtype=np.float32)
    distances, indices = index.search(query, min(k, len(metadata)))
    
    results = []
    metadata_list = list(metadata.items())
    
    for idx, distance in zip(indices[0], distances[0]):
        if idx < len(metadata_list):
            title, classification = metadata_list[idx]
            results.append({
                "title": title,
                "classification": classification,
                "distance": float(distance)
            })
    
    return results

# ===== BATCH CLASSIFICATION =====
def batch_classify(titles, index, metadata):
    """Classify new titles in batch using FAISS + LLM"""
    classifications = {}
    
    for idx, title in enumerate(titles):
        if idx % 10 == 0:
            print(f"  Classifying {idx}/{len(titles)}...")
        
        try:
            title_embedding = get_embedding(title)
            similar = search_faiss(title_embedding, index, metadata, k=3)
            
            similar_info = "\n".join([
                f"- '{s['title']}' → {s['classification']['category']} (distance: {s['distance']:.2f})"
                for s in similar
            ])
            
            prompt = f"""Based on these similar titles:
{similar_info}

Classify: '{title}'

Categories: High Load, Communication, Low Load
Extract app name and type.

Respond ONLY as JSON (no markdown):
{{"category": "...", "confidence_reason": "...", "app_name": "...", "app_type": "..."}}
"""
            
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=150
            )
            
            response_text = response.choices[0].message.content.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            result = json.loads(response_text)
            classifications[title] = result
        
        except Exception as e:
            print(f"  Error classifying '{title[:50]}': {e}")
            classifications[title] = {
                "category": "UNCLASSIFIED_ERROR",
                "confidence_reason": str(e),
                "app_name": "Unknown",
                "app_type": "Other"
            }
    
    return classifications

# ===== MAIN EXECUTION =====
def main():
    print("\n" + "="*60)
    print("AGENT 1: FAISS-ACCELERATED CLASSIFICATION")
    print("="*60 + "\n")
    
    try:
        df = pd.read_csv(FILE_NAME)
        df = df.dropna(subset=['Window_Title'])
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    except Exception as e:
        print(f"Error reading {FILE_NAME}: {e}")
        return
    
    print(f"Loaded {len(df)} activities with {df['Window_Title'].nunique()} unique titles\n")
    
    # Check if already classified
    if Path(CLASSIFIED_FILE_NAME).exists():
        classified_df = pd.read_csv(CLASSIFIED_FILE_NAME)
        required_cols = ['Category', 'App_Name', 'App_Type']
        if all(col in classified_df.columns for col in required_cols):
            print(f"Already classified! Skipping...\n")
            return
    
    # Load FAISS index
    print("Step 1: Loading FAISS index...")
    faiss_index, faiss_metadata = load_or_create_faiss()
    
    unique_titles = df['Window_Title'].unique()
    
    # Find new titles
    new_titles = [t for t in unique_titles if t not in faiss_metadata]
    cached_titles = [t for t in unique_titles if t in faiss_metadata]
    
    print(f"Found {len(cached_titles)} cached titles, {len(new_titles)} new titles\n")
    
    # Classify new titles
    if len(new_titles) > 0:
        print(f"Step 2: Batch classifying {len(new_titles)} new titles...\n")
        new_classifications = batch_classify(new_titles, faiss_index, faiss_metadata)
        
        # Add to FAISS
        print("\nStep 3: Adding to FAISS index...")
        for title, classification in new_classifications.items():
            embedding = get_embedding(title)
            faiss_index.add(np.array([embedding], dtype=np.float32))
            faiss_metadata[title] = classification
        
        # Save FAISS
        save_faiss_index(faiss_index, faiss_metadata)
        print("Saved FAISS index\n")
    
    # Apply to dataframe
    print("Step 4: Applying classifications to dataframe...\n")
    
    df['Category'] = df['Window_Title'].map(lambda x: faiss_metadata[x]["category"])
    df['Confidence_Reason'] = df['Window_Title'].map(lambda x: faiss_metadata[x].get("confidence_reason", ""))
    df['App_Name'] = df['Window_Title'].map(lambda x: faiss_metadata[x].get("app_name", "Unknown"))
    df['App_Type'] = df['Window_Title'].map(lambda x: faiss_metadata[x].get("app_type", "Other"))
    df['FQS_Score'] = 0
    df['Hour_of_Day'] = df['Timestamp'].dt.hour
    
    category_times = df.groupby('Category').size()
    high_load_count = category_times.get('High Load', 0)
    total = len(df)
    fqs_score = (high_load_count / total * 100) if total > 0 else 0
    
    df['FQS_Score'] = fqs_score
    df.to_csv(CLASSIFIED_FILE_NAME, index=False)
    
    print("="*60)
    print(f"COMPLETED")
    print(f"New classifications: {len(new_titles)}")
    print(f"Total in FAISS: {len(faiss_metadata)}")
    print(f"FQS Score: {fqs_score:.1f}%")
    print("="*60 + "\n")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Fatal error: {e}")