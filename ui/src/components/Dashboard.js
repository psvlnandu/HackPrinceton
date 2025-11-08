import React from "react";
import Container from "react-bootstrap/Container";
import Button from "react-bootstrap/Button";
import Alert from "react-bootstrap/Alert";
import Spinner from "react-bootstrap/Spinner";
import "../styles/Dashboard.css";

class Dashboard extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      metrics: null,
      loading: false,
      pipelineRunning: false,
      message: null,
      autoRefreshEnabled: false,
      autoRefreshInterval: null,
    };
  }

  componentDidMount() {
    // Load metrics on page load
    this.fetchMetrics();
  }

  componentWillUnmount() {
    // Clear auto-refresh interval
    if (this.state.autoRefreshInterval) {
      clearInterval(this.state.autoRefreshInterval);
    }
  }

  fetchMetrics = async () => {
    this.setState({ loading: true });
    try {
      const response = await fetch("http://localhost:8000/api/metrics");
      const data = await response.json();
      this.setState({ 
        metrics: data,
        message: { type: "success", text: "✅ Metrics loaded successfully" }
      });
    } catch (error) {
      console.error("Error fetching metrics:", error);
      this.setState({
        message: { type: "danger", text: `❌ Error: ${error.message}` }
      });
    } finally {
      this.setState({ loading: false });
    }
  };

  runPipeline = async () => {
    this.setState({ 
      pipelineRunning: true,
      message: { type: "info", text: "⏳ Running analysis pipeline..." }
    });

    try {
      const response = await fetch("http://localhost:8000/api/run-pipeline", {
        method: "POST",
      });
      const data = await response.json();

      if (data.status.includes("✅")) {
        this.setState({
          message: { type: "success", text: "✅ Pipeline completed! Fetching new data..." }
        });
        
        // Wait a moment, then fetch updated metrics
        setTimeout(() => {
          this.fetchMetrics();
        }, 1000);
      } else {
        this.setState({
          message: { type: "warning", text: data.status }
        });
      }
    } catch (error) {
      console.error("Error running pipeline:", error);
      this.setState({
        message: { type: "danger", text: `❌ Pipeline error: ${error.message}` }
      });
    } finally {
      this.setState({ pipelineRunning: false });
    }
  };

  toggleAutoRefresh = () => {
    const { autoRefreshEnabled, autoRefreshInterval } = this.state;

    if (autoRefreshEnabled) {
      // Disable
      clearInterval(autoRefreshInterval);
      this.setState({
        autoRefreshEnabled: false,
        autoRefreshInterval: null,
        message: { type: "info", text: "Auto-refresh disabled" }
      });
    } else {
      // Enable (refresh every 60 seconds)
      const interval = setInterval(() => {
        this.runPipeline();
      }, 60000);

      this.setState({
        autoRefreshEnabled: true,
        autoRefreshInterval: interval,
        message: { type: "info", text: "✅ Auto-refresh enabled (every 60 sec)" }
      });
    }
  };

  render() {
    const { metrics, loading, pipelineRunning, message, autoRefreshEnabled } = this.state;

    return (
      <div className="dashboard-page">
        <Container>
          <div className="dashboard-header">
            <h1>📊 Dashboard</h1>
            <p className="subtitle">Real-time monitoring of your cognitive health</p>
          </div>

          {/* Messages */}
          {message && (
            <Alert variant={message.type} onClose={() => this.setState({ message: null })} dismissible>
              {message.text}
            </Alert>
          )}

          {/* Control Buttons */}
          <div className="dashboard-controls">
            <Button
              variant="primary"
              onClick={this.runPipeline}
              disabled={pipelineRunning || loading}
              className="control-btn"
            >
              {pipelineRunning ? (
                <>
                  <Spinner animation="border" size="sm" className="me-2" />
                  Running...
                </>
              ) : (
                <>🔄 Run Analysis Pipeline</>
              )}
            </Button>

            <Button
              variant={autoRefreshEnabled ? "danger" : "success"}
              onClick={this.toggleAutoRefresh}
              disabled={pipelineRunning}
              className="control-btn"
            >
              {autoRefreshEnabled ? "⏹️ Stop Auto-Refresh" : "▶️ Start Auto-Refresh (60s)"}
            </Button>

            <Button
              variant="secondary"
              onClick={this.fetchMetrics}
              disabled={loading}
              className="control-btn"
            >
              {loading ? (
                <>
                  <Spinner animation="border" size="sm" className="me-2" />
                  Fetching...
                </>
              ) : (
                <>📥 Refresh Data</>
              )}
            </Button>
          </div>

          {/* Metrics Display */}
          {loading ? (
            <div className="loading-state">
              <Spinner animation="border" role="status">
                <span className="visually-hidden">Loading...</span>
              </Spinner>
              <p>Loading metrics...</p>
            </div>
          ) : metrics && !metrics.error ? (
            <div className="metrics-grid">
              {/* FQS Card */}
              <div className="metric-card focus-quality">
                <div className="metric-icon">📈</div>
                <h3>Focus Quality Score</h3>
                <div className="metric-value">{metrics.fqs?.toFixed(1) || "—"}%</div>
                <p className="metric-label">Deep work percentage</p>
                <div className="progress">
                  <div 
                    className="progress-bar bg-success" 
                    style={{ width: `${metrics.fqs || 0}%` }}
                  ></div>
                </div>
              </div>

              {/* CSC Card */}
              <div className="metric-card context-switch">
                <div className="metric-icon">⚡</div>
                <h3>Context Switch Cost</h3>
                <div className="metric-value">{metrics.csc?.toFixed(2) || "—"}s</div>
                <p className="metric-label">Per hour cost</p>
                <div className="metric-status">
                  {metrics.csc < 1.5 ? "✅ Healthy" : metrics.csc < 3 ? "🟡 Moderate" : "🔴 High"}
                </div>
              </div>

              {/* Burnout Risk Card */}
              <div className="metric-card burnout-risk">
                <div className="metric-icon">🔴</div>
                <h3>Burnout Risk Score</h3>
                <div className="metric-value">{metrics.burnout_score?.toFixed(1) || "—"}/10</div>
                <p className="metric-label">{metrics.burnout_level || "Unknown"}</p>
              </div>

              {/* Session Duration Card */}
              <div className="metric-card session-time">
                <div className="metric-icon">⏱️</div>
                <h3>Total Session Time</h3>
                <div className="metric-value">{metrics.total_hours?.toFixed(1) || "—"}h</div>
                <p className="metric-label">Hours logged</p>
              </div>
            </div>
          ) : (
            <Alert variant="warning">
              No data available. Run the analysis pipeline first! 🔄
            </Alert>
          )}

          {/* Info Box */}
          <div className="info-box">
            <h4>💡 How to Use</h4>
            <ol>
              <li>Make sure <code>data.py</code> is running on your laptop</li>
              <li>Click <strong>"Run Analysis Pipeline"</strong> to process your activity data</li>
              <li>Dashboard updates with your FQS, CSC, and Burnout metrics</li>
              <li>Enable <strong>"Auto-Refresh"</strong> to run every 60 seconds</li>
            </ol>
          </div>
        </Container>
      </div>
    );
  }
}

export default Dashboard;