import React from "react";
import Container from "react-bootstrap/Container";
import "../styles/About.css";

class About extends React.Component {
  render() {
    return (
      <div className="about-page">
        <Container>
          <div className="about-hero">
            <h1>About Cognitive Health Coach</h1>
            <p className="subtitle">Measuring what matters: Focus, Sustainability & Wellbeing</p>
          </div>

          {/* What is this section */}
          <section className="about-section">
            <h2>What is Cognitive Health Coach?</h2>
            <p>
              Most productivity tools track <strong>what you do</strong>. We measure <strong>how sustainable it is</strong>.
            </p>
            <p>
              Cognitive-Metabolic AI Coach monitors your work patterns in real-time to detect burnout risk 
              and optimize your focus. Using multi-agent LLM reasoning, we analyze:
            </p>
            <ul>
              <li>Your focus quality (deep work vs. distractions)</li>
              <li>Cognitive fragmentation (context switching cost)</li>
              <li>Burnout patterns (evening work, breaks, session continuity)</li>
            </ul>
          </section>

          {/* Metrics section */}
          <section className="about-section">
            <h2>Our Three Core Metrics</h2>
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-icon">📈</div>
                <h3>Focus Quality Score (FQS)</h3>
                <p>
                  Percentage of your productive time spent on deep work vs. reactive tasks.
                </p>
                <div className="metric-detail">
                  <span className="label">Target:</span>
                  <span className="value">80%+</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-icon">⚡</div>
                <h3>Context Switch Cost (CSC)</h3>
                <p>
                  Neurological disruption cost from tab-switching and task-switching measured per hour.
                </p>
                <div className="metric-detail">
                  <span className="label">Healthy:</span>
                  <span className="value">&lt;1.5 s/hr</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-icon">🔴</div>
                <h3>Burnout Risk Score</h3>
                <p>
                  Composite AI assessment based on work duration, breaks, circadian disruption, and switching patterns.
                </p>
                <div className="metric-detail">
                  <span className="label">1-3:</span>
                  <span className="value">Healthy | 7-10: At Risk</span>
                </div>
              </div>
            </div>
          </section>

          {/* Science section */}
          <section className="about-section">
            <h2>Research Foundation</h2>
            <p>
              Our methodology is grounded in cognitive neuroscience and workplace wellness research:
            </p>
            <div className="research-list">
              <div className="research-item">
                <h4>Ultradian Rhythms (Kleitman, 1961)</h4>
                <p>
                  Peak cognitive focus is 90-120 minutes, followed by biological need for recovery. 
                  Working beyond this without breaks decreases efficiency and increases error rates.
                </p>
              </div>

              <div className="research-item">
                <h4>Context Switching Penalty (Ophir et al., 2009)</h4>
                <p>
                  Heavy multitaskers are worse at filtering irrelevant information and organizing material. 
                  Each switch costs 23+ minutes of attention recovery time.
                </p>
              </div>

              <div className="research-item">
                <h4>Circadian Rhythm & Cortisol (Walker, 2017)</h4>
                <p>
                  Evening work spikes cortisol levels, impairing sleep quality and causing 30% worse performance the next day. 
                  Morning focus is neurologically more valuable than evening work.
                </p>
              </div>

              <div className="research-item">
                <h4>Prefrontal Cortex Recovery</h4>
                <p>
                  Just 10 minutes of genuine rest recovers approximately 40% of cognitive capacity. 
                  Short breaks dramatically extend sustainable focus duration.
                </p>
              </div>
            </div>
          </section>

          {/* Technology section */}
          <section className="about-section">
            <h2>Our Technology Stack</h2>
            <div className="tech-grid">
              <div className="tech-card">
                <h4>Multi-Agent LLM System</h4>
                <p>
                  OpenAI-powered agents specialize in classification, fragmentation analysis, and burnout detection.
                </p>
              </div>

              <div className="tech-card">
                <h4>Privacy-First Architecture</h4>
                <p>
                  No keystroke logging. No video surveillance. Only window titles and timestamps collected.
                </p>
              </div>

              <div className="tech-card">
                <h4>Real-Time Processing</h4>
                <p>
                  Immediate insights delivered as you work. No waiting for end-of-day reports.
                </p>
              </div>

              <div className="tech-card">
                <h4>Personalized Prescriptions</h4>
                <p>
                  AI coaches provide context-specific, actionable recommendations for your unique work style.
                </p>
              </div>
            </div>
          </section>

          {/* Why it matters section */}
          <section className="about-section">
            <h2>Why This Matters</h2>
            <div className="impact-stats">
              <div className="stat">
                <div className="stat-number">$406B</div>
                <div className="stat-label">Annual cost to US companies from employee disengagement</div>
              </div>

              <div className="stat">
                <div className="stat-number">$1T</div>
                <div className="stat-label">Global annual cost of burnout-related lost productivity</div>
              </div>

              <div className="stat">
                <div className="stat-number">50%</div>
                <div className="stat-label">Of 2021 resignations attributed to mental health issues</div>
              </div>
            </div>

            <p className="impact-text">
              Early burnout detection + personalized coaching = reduced turnover, better retention, 
              healthier workforce, and sustainable high performance.
            </p>
          </section>

          {/* Team section */}
          <section className="about-section about-footer">
            <p>Built With ❤️</p>
            <p>
              Cognitive Health Coach was built at <strong>Princeton Hack 2025</strong> by a passionate team 
              of engineers and researchers committed to employee wellbeing.
            </p>
            <p className="contact">
              Have questions? Reach out to us at <strong>hello@cognitivehealthcoach.tech</strong>
            </p>
          </section>
        </Container>
      </div>
    );
  }
}

export default About;