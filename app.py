import streamlit as st
import pandas as pd
import requests
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import plotly.express as px
import time
import plotly.graph_objects as go
# Page config
st.set_page_config(page_title="Cognitive Health", layout="wide", initial_sidebar_state="expanded")

# Config
LOCAL_DATA_SERVER = "https://merry-vaporizable-bioclimatologically.ngrok-free.dev"
BASE_DIR = Path(__file__).parent.parent

# ===== HELPER FUNCTIONS =====
@st.cache_data(ttl=5)  # Refresh every 5 seconds
def fetch_latest_data():
    """Fetch data from local data.py server"""
    try:
        response = requests.get(f"{LOCAL_DATA_SERVER}/api/data", timeout=2)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Server returned error", "data": []}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to local server. Make sure data.py is running!", "data": []}
    except Exception as e:
        return {"error": str(e), "data": []}

def load_metrics():
    """Load metrics from CSV"""
    try:
        if (BASE_DIR / "classified_activity01.csv").exists():
            classified = pd.read_csv(BASE_DIR / "classified_activity01.csv")
            if len(classified) > 0:
                return classified
    except:
        pass
    return None

def load_burnout():
    """Load burnout data"""
    try:
        if (BASE_DIR / "burnout_flags.json").exists():
            with open(BASE_DIR / "burnout_flags.json") as f:
                return json.load(f)
    except:
        pass
    return {}

def run_pipeline():
    """Run analysis pipeline"""
    try:
        with st.spinner("🔄 Running analysis pipeline..."):
            result = subprocess.run(
                ["python", "pipeline.py"],
                capture_output=True,
                text=True,
                cwd=str(BASE_DIR),
                timeout=100
            )
            
            if result.returncode == 0:
                st.success("✅ Pipeline completed successfully!")
                st.rerun()
            else:
                st.error(f"⚠️ Pipeline error: {result.stderr[:200]}")
    except Exception as e:
        st.error(f"❌ Failed to run pipeline: {str(e)}")

def load_analytics():
    """Load analytics report"""
    try:
        if Path("analytics_report.json").exists():
            with open("analytics_report.json") as f:
                return json.load(f)
    except:
        pass
    return None

# ===== MAIN UI =====
st.title("📊 Cognitive Metabolic Health Dashboard")
st.markdown("**Real-time monitoring** of your cognitive health")

# ===== SIDEBAR =====
with st.sidebar:
    st.header("⚙️ Controls")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Run Pipeline", width='stretch'):
            run_pipeline()
    
    with col2:
        if st.button("🔄 Refresh", width='stretch'):
            st.rerun()
    
    st.divider()
    
    # Server status
    data_response = fetch_latest_data()
    if "error" in data_response and data_response["error"]:
        st.error(f"⚠️ Server: {data_response['error']}")
    else:
        st.success(f"✅ Connected! ({data_response.get('count', 0)} activities)")
    
    st.divider()
    
    st.subheader("📁 Data Source")
    st.caption("📍 Local: data.py (http://localhost:5000)")
    st.caption("📍 Cloud: Codespace (Analysis)")

# ===== FETCH DATA =====
data_response = fetch_latest_data()
classified = load_metrics()
burnout = load_burnout()
analytics = load_analytics()

# ===== METRICS DISPLAY =====
if "error" not in data_response or not data_response["error"]:
    # Calculate metrics from received data
    activities = data_response.get("data", [])
    
    fqs = burnout.get("burnout_risk_score", 0) if burnout else 0
    csc = 2.5  # Placeholder
    burnout_score = burnout.get("burnout_risk_score", 0) if burnout else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📈 Focus Quality", f"{fqs:.1f}%", "Deep work")
    
    with col2:
        st.metric("⚡ Context Switches", f"{csc:.2f}s", "Per hour")
    
    with col3:
        st.metric("🔴 Burnout Risk", f"{burnout_score:.1f}/10", "Risk level")
    
    with col4:
        st.metric("📝 Activities", f"{len(activities)}", "Logged today")
    
    st.divider()
    
    # ===== TABS =====
    tab1, tab2, tab3, tab4= st.tabs(["Overview", "Activity Breakdown", "Insights", "Analytics"])
    
    with tab1:
        st.subheader("Current Status")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if burnout_score < 3:
                status = "✅ Healthy"
            elif burnout_score < 6:
                status = "🟡 Moderate Risk"
            else:
                status = "🔴 High Risk"
            
            st.markdown(f"### {status}")
            st.progress(min(burnout_score / 10, 1.0))
            st.markdown(f"**Burnout Score:** {burnout_score:.1f}/10")
        
        with col2:
            st.markdown("### 📝 Recent Activities")
            if len(activities) > 0:
                # Show last 10 activities
                for activity in activities[-10:]:
                    st.caption(f"⏰ {activity['timestamp']}")
                    st.caption(f"🪟 {activity['window_title'][:70]}")
                    st.divider()
            else:
                st.info("No activities recorded yet. Make sure data.py is running!")
    
    with tab2:
        st.subheader("Activity Breakdown")
        
        if classified is not None and len(classified) > 0:
            if "Category" in classified.columns:
                category_counts = classified["Category"].value_counts()
                
                # Top row: Pie chart and summary
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    fig = px.pie(
                        values=category_counts.values,
                        names=category_counts.index,
                        title="Time Distribution by Category"
                    )
                    st.plotly_chart(fig, width='stretch')
                
                with col2:
                    st.subheader("Category Summary")
                    
                    top_categories = category_counts.head(5)
                    
                    df_display = pd.DataFrame({
                        'Category': top_categories.index,
                        'Count': top_categories.values,
                        'Percentage': (top_categories.values / top_categories.sum() * 100).round(1)
                    })
                    
                    st.dataframe(
                        df_display,
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    st.metric("Total Activities", len(classified))
                
                st.divider()
                
                st.subheader("Top 5 Applications by Category")
                
                unique_categories = classified["Category"].unique()
                for category in sorted(unique_categories):
                    with st.container():
                        col1, col2, col3 = st.columns(3)
                        
                        category_data = classified[classified["Category"] == category]
                        
                        if "App_Name" in category_data.columns:
                            app_counts = category_data["App_Name"].value_counts().head(5)
                            
                            with col1:
                                st.write(f"**{category}**")
                                
                                for idx, (app, count) in enumerate(app_counts.items(), 1):
                                    pct = (count / len(category_data) * 100)
                                    st.write(f"{idx}. {app}")
                                    st.caption(f"{count} times ({pct:.1f}%)")
                            
                            with col2:
                                fig = px.bar(
                                    x=app_counts.values,
                                    y=app_counts.index,
                                    orientation='h',
                                    title=f"Top Apps - {category}",
                                    labels={'x': 'Count', 'y': 'App'},
                                    text=app_counts.values
                                )
                                fig.update_layout(height=250, showlegend=False)
                                st.plotly_chart(fig, width='stretch')
                            
                            with col3:
                                app_types = category_data["App_Type"].value_counts()
                                st.write(f"**App Types**")
                                for app_type, count in app_types.head(3).items():
                                    st.caption(f"{app_type}: {count}")
                                
                                st.divider()
                                
                                st.metric(
                                    f"{category} Total",
                                    len(category_data),
                                    f"{len(category_data)/len(classified)*100:.1f}%"
                                )
                        
                        st.divider()
                
        else:
            st.info("Run the pipeline to see activity breakdown")
        
    with tab3:
        st.subheader("💡 Insights & Recommendations")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("""
            ✅ **Focus Tips:**
            - Take breaks every 60 minutes
            - Batch similar tasks
            - Minimize notifications
            - Set focus time blocks
            """)
        
        with col2:
            health_report = {}
            try:
                if (BASE_DIR / "final_health_report.json").exists():
                    with open(BASE_DIR / "final_health_report.json") as f:
                        health_report = json.load(f)
            except:
                pass
            
            if health_report:
                st.success("**Your Health Report:**")
                for key, value in health_report.items():
                    st.write(f"**{key}:** {value}")
            else:
                st.info("Run the pipeline to generate your health report")
    
# ===== NEW: ANALYTICS TAB =====
    with tab4:
        st.title("📊 Advanced Analytics Dashboard")
        st.markdown("**YouTube Creator Studio-style insights into your cognitive health**\n")
        
        if analytics is None:
            st.warning("📌 Run the analysis pipeline first to see analytics")
        else:
            # ===== TOP SECTION: 4 KEY METRICS =====
            col1, col2, col3, col4 = st.columns(4)
            
            health_score = analytics.get("predictive_health_score", {})
            burnout = analytics.get("burnout_prediction", {})
            cog_load = analytics.get("cognitive_load", {})
            energy = analytics.get("energy_levels", {})
            
            with col1:
                st.metric(
                    "⚡ Energy Pattern",
                    f"{energy.get('peak_energy', 0):.0f}%",
                    f"Peak: {energy.get('peak_hours', ['N/A'])[0] if energy.get('peak_hours') else 'N/A'}am"
                )
            
            with col2:
                st.metric(
                    "🧠 Cognitive Load",
                    f"{cog_load.get('current', 0):.1f}/10",
                    cog_load.get('status', 'UNKNOWN')
                )
            
            with col3:
                st.metric(
                    "🔥 Flow Detected",
                    f"{analytics.get('flow_state', {}).get('session_count', 0)}",
                    "sessions"
                )
            
            with col4:
                st.metric(
                    "❤️ Health Score",
                    f"{health_score.get('overall', 0):.1f}/10",
                    health_score.get('status', 'UNKNOWN'),
                    delta_color="inverse"
                )
            
            st.divider()
            
            # ===== MIDDLE SECTION: 3-COLUMN LAYOUT =====
            col1, col2, col3 = st.columns(3)
            
            # Column 1: Energy Levels Throughout Day
            with col1:
                st.subheader("📈 Energy Levels by Hour")
                
                hourly_data = energy.get('hourly_data', [])
                if hourly_data:
                    df_hourly = pd.DataFrame(hourly_data)
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=df_hourly['hour'],
                        y=df_hourly['energy'],
                        marker_color='#1f77b4',
                        text=df_hourly['energy'],
                        textposition='auto',
                        name='Energy %'
                    ))
                    fig.update_layout(
                        title=None,
                        xaxis_title="Hour of Day",
                        yaxis_title="Energy %",
                        height=350,
                        showlegend=False,
                        hovermode='x unified'
                    )
                    # st.plotly_chart(fig, use_container_width=True)
                    st.plotly_chart(fig, width='stretch')
                    
                    st.caption(f"🔥 Peak: {energy.get('peak_hours', [])[0] if energy.get('peak_hours') else 'N/A'}am ({energy.get('peak_energy', 0):.0f}%)")
                    st.caption(f"📉 Low: {energy.get('low_hours', [])[0] if energy.get('low_hours') else 'N/A'}pm ({energy.get('low_energy', 0):.0f}%)")
            
            # Column 2: Cognitive Load Distribution
            with col2:
                st.subheader("🧠 Current Cognitive Load")
                
                cog_data = cog_load
                fig = go.Figure(data=[
                    go.Pie(
                        labels=['High Load', 'Communication', 'Low Load'],
                        values=[
                            cog_data.get('high_load_pct', 0),
                            cog_data.get('comm_pct', 0),
                            cog_data.get('low_load_pct', 0)
                        ],
                        hole=0.4,
                        marker_colors=['#FF6B6B', '#FFA500', '#4ECDC4']
                    )
                ])
                fig.update_layout(
                    title=None,
                    height=350,
                    showlegend=True
                )
                st.plotly_chart(fig, width='stretch')
                
                st.metric("Load Index", f"{cog_data.get('current', 0):.1f}/10", cog_data.get('status'))
            
            # Column 3: Flow State Sessions
            with col3:
                st.subheader("🔥 Flow State Sessions")
                
                flow_sessions = analytics.get('flow_state', {}).get('sessions', [])
                
                if flow_sessions:
                    for session in flow_sessions:
                        with st.container():
                            st.write(f"⏱️ **{session['start']}**")
                            st.write(f"Duration: {session['duration_minutes']:.0f} min")
                            st.write(f"App: {session['app']}")
                            st.write(f"Confidence: {session['confidence']*100:.0f}%")
                            st.divider()
                else:
                    st.info("No flow state detected yet")
            
            st.divider()
            
            # ===== BOTTOM SECTION: 3 ROWS =====
            
            # Row 1: Work-Life Balance
            st.subheader("⚖️ Work-Life Balance")
            col1, col2 = st.columns([2, 1])
            
            with col1:
                balance = analytics.get('work_life_balance', {})
                total_hours = balance.get('total_hours', 0)
                target = balance.get('target_hours', 8)
                
                fig = go.Figure(data=[
                    go.Bar(
                        x=['Target', 'Actual'],
                        y=[target, total_hours],
                        marker_color=['#90EE90', '#FF6B6B' if total_hours > 9 else '#4ECDC4'],
                        text=[f'{target}h', f'{total_hours}h'],
                        textposition='auto'
                    )
                ])
                fig.update_layout(
                    title=None,
                    height=300,
                    showlegend=False,
                    yaxis_title="Hours"
                )
                st.plotly_chart(fig, width='stretch')
            
            with col2:
                st.metric("Status", balance.get('status', 'UNKNOWN'))
                st.metric("Excess Hours", f"{balance.get('excess_hours', 0):.1f}h")
                st.metric("Balance Score", f"{balance.get('balance_score', 0):.1f}/10")
            
            # Row 2: Burnout Trajectory
            st.subheader("📉 Burnout Risk Trajectory")
            
            burnout_pred = analytics.get('burnout_prediction', {})
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Simulate 7-day trend
                current = burnout_pred.get('current', 5)
                trajectory = burnout_pred.get('trajectory', 'STABLE')
                
                if trajectory == "RISING":
                    trend_data = [current - 0.6*i for i in range(7)][::-1]
                elif trajectory == "IMPROVING":
                    trend_data = [current + 0.3*i for i in range(7)][::-1]
                else:
                    trend_data = [current + (0.1*i if i % 2 == 0 else -0.05*i) for i in range(7)]
                
                days = list(range(-6, 1))
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=days,
                    y=trend_data,
                    mode='lines+markers',
                    name='Burnout Score',
                    line=dict(color='#FF6B6B', width=3),
                    marker=dict(size=8)
                ))
                fig.add_hline(y=8, line_dash="dash", line_color="red", annotation_text="Critical")
                fig.add_hline(y=6, line_dash="dash", line_color="orange", annotation_text="High")
                
                fig.update_layout(
                    title=None,
                    xaxis_title="Days (0 = Today)",
                    yaxis_title="Burnout Score",
                    height=300,
                    hovermode='x unified'
                )
                st.plotly_chart(fig, width='stretch')
            
            with col2:
                st.metric("Current", f"{burnout_pred.get('current', 0):.1f}/10")
                st.metric("Trajectory", burnout_pred.get('trajectory', 'UNKNOWN'))
                st.metric("Risk Level", burnout_pred.get('risk_level', 'UNKNOWN'))
                if burnout_pred.get('trajectory') == 'RISING':
                    st.warning(f"⚠️ Critical in {burnout_pred.get('days_to_critical', 0)} days")
            
            # Row 3: Predictive Health Score Breakdown
            st.subheader("❤️ Predictive Health Score Breakdown")
            
            components = health_score.get('components', {})
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Horizontal bar chart
                component_names = list(components.keys())
                component_values = list(components.values())
                
                fig = go.Figure(data=[
                    go.Bar(
                        y=component_names,
                        x=component_values,
                        orientation='h',
                        marker_color=['#FF6B6B' if v < 3 else '#FFA500' if v < 5 else '#4ECDC4' for v in component_values],
                        text=component_values,
                        textposition='auto'
                    )
                ])
                fig.update_layout(
                    title=None,
                    xaxis_title="Score /10",
                    height=300,
                    showlegend=False,
                    xaxis=dict(range=[0, 10])
                )
                st.plotly_chart(fig, width='stretch')
            
            with col2:
                st.metric("Overall Health", f"{health_score.get('overall', 0):.1f}/10")
                st.metric("Status", health_score.get('status', 'UNKNOWN'), delta_color="inverse")
                st.metric("7-Day Projection", f"{health_score.get('projection_7days', 0):.1f}/10")
            
            st.divider()
            
            # ===== AI INSIGHTS =====
            st.subheader("🤖 AI-Generated Insights & Recommendations")
            
            ai_insights = analytics.get('ai_insights', '')
            if ai_insights:
                st.info(ai_insights)
            else:
                st.caption("No insights available yet")
        # ===== AUTO REFRESH =====
        st.divider()
        
        # Auto-refresh every 5 seconds
        time.sleep(1)
        st.rerun()

else:
    st.error("🚨 Cannot connect to local data server!")
    st.markdown("""
    ### Setup Instructions:
    
    1. **On your LOCAL machine**, run:
       ```bash
       python data.py
       ```
       This starts the HTTP server on http://localhost:5000
    
    2. **Keep data.py running** in the background
    
    3. **Then open this Streamlit app** in Codespace
    
    4. This dashboard will automatically fetch data from your local machine!
    """)