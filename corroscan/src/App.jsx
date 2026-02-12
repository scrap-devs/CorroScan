import { useState } from 'react'
import './styles/header.css'
import './styles/general.css'
import './styles/start.css'
import './styles/features.css'
import logo from './icons/logo.png'

function App() {
  const [count, setCount] = useState(0)

  return (
    <>
      <nav>
        <div className="header">
          <div className="header-left-section">
            <img className="header-logo" src={logo} />
            <div className="header-title">CorroScan</div>
          </div>
          <div className="header-middle-section">
            <a>Features</a>
            <a>Capabilities</a>
            <a>Industries</a>
            <a>Technology</a>
          </div>
          <div className="header-right-section">
            <div className="header-start">
              Get Started
            </div>
          </div>
        </div>
      </nav>

      <main>
        <section className="start">
          <div className="start-container">
            <div className="start-header">
              <div className="start-header-word">Advanced Materials Analysis</div>
            </div>
            <div className="start-title">
              <div className="start-title-info">Corrosion</div>
              <div className="start-title-info">Morphology Analysis</div>
              <div className="start-title-info">Platform</div>
            </div>
            <div className="start-description">
              Leverage cutting-edge AI and machine learning to analyze, classify, and quantify corrosion patterns with unprecedented accuracy and speed.
            </div>
            <div className="start-buttons">
              <button className="analysis-button">Start Analysis <span className="analysis-right-arrow">&#8594;</span></button>
              <button className="demo-button">Start Demo</button>
            </div>
            <div className="start-stats">
              <div className="accuracy-stat">
                <div className="main-stat">99%</div>
                <div className="sub-stat">Accuracy</div>
              </div>
              <div className="faster-analysis-stat">
                <div className="main-stat">10x</div>
                <div className="sub-stat">Faster Analysis</div>
              </div>
              <div className="corrosion-type-stat">
                <div className="main-stat">8+</div>
                <div className="sub-stat">Corrosion Types</div>
              </div>
            </div>
          </div>
        </section>

        <section>
          <div className="features-container">
            <div className="features-title-container">Powerful Features</div>
            <div className="features-subtitle">Everything you need for comprehensive corrosion morphology analysis</div>
            <div className="features-grid">
              <div className="features-image-analysis-card">
                <div className="features-card-title">Advanced Image Analysis</div>
                <div className="features-card-info">Process high-resolution microscopy images with AI-powered detection algorithms for precise corrosion identification.</div>
              </div>
              <div className="features-processing-card">
                <div className="features-card-title">Real-time Processing</div>
                <div className="features-card-info">Analyze images in seconds with our optimized pipeline, reducing turnaround time from hours to minutes.</div>
              </div>
              <div className="features-reporting-card">
                <div className="features-card-title">Comprehensive Reporting</div>
                <div className="features-card-info">Generate detailed reports with quantitative metrics, visualizations, and actionable insights automatically.</div>
              </div>
              <div className="features-quality-assurance-card">
                <div className="features-card-title">Quality Assurance</div>
                <div className="features-card-info">Ensure consistency and reliability with automated validation and quality control measures.</div>
              </div>
              <div className="features-multi-scale-analysis-card">
                <div className="features-card-title">Multi-Scale Analysis</div>
                <div className="features-card-info">Examine corrosion at multiple magnifications from macro to nano-scale with seamless integration.</div>
              </div>
              <div className="features-ml-powered-card">
                <div className="features-card-title">ML-Powered Classification</div>
                <div className="features-card-info">Leverage deep learning models trained on thousands of corrosion patterns for accurate type identification.</div>
              </div>
            </div>


          </div>
        </section>
      </main>
    </>
  )
}

export default App
