import streamlit as st
import pandas as pd
import json
import subprocess
from pathlib import Path
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

# Page config
st.set_page_config(page_title="Cognitive Health", layout="wide", initial_sidebar_state="expanded")

# Title and description
st.title("📊 Cognitive Metabolic Health Dashboard")
st.markdown("Real-time monitoring of your cognitive health and burnout risk")

# Initialize paths
BASE_DIR = Path(__file__).parent.parent

DATA_FILES = {
    "enriched": BASE_DIR / "activity_log_enriched01.csv",
    "classified": BASE_DIR / "classified_activity01.csv",
    "fragmented": BASE_DIR / "fragmented_activity01.csv",
    "burnout": BASE_DIR / "burnout_flags.json",
    "health_report": BASE_DIR / "final_health_report.json",
}

def safe_read_csv(filepath):
    """Read CSV safely"""
    try:
        if Path(filepath).exists():
            return pd.read_csv(filepath)
        return None
    except Exception as e:
        st.error(f"Error reading {filepath}: {str(e)}")
        return None

def safe_read_json(filepath):
    """Read JSON safely"""
    try:
        if Path(filepath).exists():
            with open(filepath, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        st.error(f"Error reading {filepath}: {str(e)}")
        return None

def get_metrics():
    """Extract key metrics from data files"""
    enriched = safe_read_csv(DATA_FILES["enriched"])
    burnout = safe_read_json(DATA_FILES["burnout"])
    
    metrics = {
        "total_hours": 0,
        "fqs": 0,
        "csc": 0,
        "burnout_score": 0,
        "burnout_level": "Unknown",
    }
    
    if enriched is not None and len(enriched) > 0:
        last_row = enriched.iloc[-1]
        metrics["total_hours"] = round(len(enriched) * 5 / 3600, 2)
        metrics["fqs"] = last_row.get("FQS_Score", 0) if "FQS_Score" in enriched.columns else 0
        metrics["csc"] = last_row.get("CSC_Score", 0) if "CSC_Score" in enriched.columns else 0
    
    if burnout is not None and isinstance(burnout, dict):
        metrics["burnout_score"] = burnout.get("burnout_risk_score", 0)
        metrics["burnout_level"] = burnout.get("risk_level", "Unknown")
    
    return metrics

def run_pipeline():
    """Execute the analysis pipeline"""
    try:
        with st.spinner("🔄 Running analysis pipeline..."):
            result = subprocess.run(
                ["python", "pipeline.py"],
                capture_output=True,
                text=True,
                cwd=str(BASE_DIR)
            )
            
            if result.returncode == 0:
                st.success("✅ Pipeline completed successfully!")
                return True
            else:
                st.error(f"⚠️ Pipeline error: {result.stderr}")
                return False
    except Exception as e:
        st.error(f"❌ Failed to run pipeline: {str(e)}")
        return False

# ===== SIDEBAR =====
with st.sidebar:
    st.header("⚙️ Controls")
    
    if st.button("🚀 Run Analysis Pipeline", use_container_width=True):
        run_pipeline()
        st.rerun()
    
    st.divider()
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()
    
    st.divider()
    
    st.markdown("### 📁 Data Files")
    for key, path in DATA_FILES.items():
        exists = "✅" if Path(path).exists() else "❌"
        st.caption(f"{exists} {key}: {path.name}")

# ===== MAIN CONTENT =====

# Get current metrics
metrics = get_metrics()

# Metrics cards
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Focus Quality Score", f"{metrics['fqs']:.1f}%", "Deep work %")

with col2:
    st.metric("Context Switch Cost", f"{metrics['csc']:.2f}s", "Per hour")
    
with col3:
    st.metric("Burnout Risk", f"{metrics['burnout_score']:.1f}/10", metrics['burnout_level'])

with col4:
    st.metric("Session Time", f"{metrics['total_hours']:.1f}h", "Hours logged")

st.divider()

# ===== INSIGHTS SECTION =====
st.header("📈 Insights & Analysis")

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Activity Breakdown", "Time Distribution", "Health Report"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 Current Status")
        
        # Burnout level indicator
        if metrics['burnout_score'] < 3:
            status = "✅ Healthy"
            color = "green"
        elif metrics['burnout_score'] < 6:
            status = "🟡 Moderate Risk"
            color = "orange"
        else:
            status = "🔴 High Risk"
            color = "red"
        
        st.markdown(f"### {status}")
        st.progress(min(metrics['burnout_score'] / 10, 1.0))
        
        # CSC status
        if metrics['csc'] < 1.5:
            csc_status = "✅ Healthy - Few interruptions"
        elif metrics['csc'] < 3:
            csc_status = "🟡 Moderate - Some context switching"
        else:
            csc_status = "🔴 High - Frequent interruptions"
        
        st.markdown(f"**Context Switching:** {csc_status}")
    
    with col2:
        st.subheader("💡 Recommendations")
        
        health_report = safe_read_json(DATA_FILES["health_report"])
        if health_report and isinstance(health_report, dict):
            for key, value in health_report.items():
                if isinstance(value, str):
                    st.info(f"**{key.replace('_', ' ').title()}:**\n{value}")
        else:
            st.info("Run the pipeline to generate recommendations")

with tab2:
    st.subheader("📊 Activity Classification Breakdown")
    
    classified = safe_read_csv(DATA_FILES["classified"])
    if classified is not None and len(classified) > 0:
        if "Category" in classified.columns:
            category_counts = classified["Category"].value_counts()
            
            fig = px.pie(
                values=category_counts.values,
                names=category_counts.index,
                title="Time Distribution by Activity Category"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(category_counts.reset_index(), use_container_width=True)
        else:
            st.warning("No 'Category' column in classified data")
    else:
        st.info("No classified data available. Run the pipeline first.")

with tab3:
    st.subheader("⏰ Time Distribution by Hour")
    
    enriched = safe_read_csv(DATA_FILES["enriched"])
    if enriched is not None and len(enriched) > 0:
        if "Hour_of_Day" in enriched.columns:
            hourly_data = enriched["Hour_of_Day"].value_counts().sort_index()
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=hourly_data.index,
                y=hourly_data.values,
                marker_color='#1f77b4',
                name='Activity Count'
            ))
            fig.update_layout(
                title="Activity Frequency by Hour of Day",
                xaxis_title="Hour of Day",
                yaxis_title="Number of Activities",
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No 'Hour_of_Day' column in enriched data")
    else:
        st.info("No enriched data available.")

with tab4:
    st.subheader("📋 Detailed Health Report")
    
    health_report = safe_read_json(DATA_FILES["health_report"])
    if health_report:
        st.json(health_report)
    else:
        st.info("No health report generated yet. Run the pipeline.")

# ===== FOOTER =====
st.divider()
st.markdown("""
---
**How to use:**
1. Ensure `data.py` is collecting activity data on your machine
2. Click "Run Analysis Pipeline" to process the data
3. View insights and metrics in real-time
4. Check recommendations for burnout prevention

**Data Files Location:** `{}`
""".format(BASE_DIR))