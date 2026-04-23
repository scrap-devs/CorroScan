import React from 'react'
import { useEffect } from 'react'
import { Link } from 'react-router-dom'

import '../styles/header.css'
import '../styles/general.css'
import '../styles/start.css'
import '../styles/footer.css'
import '../styles/features.css'
import '../styles/capabilities.css'

import logo from '../icons/logo.png'
import image from '../icons/image-analysis.svg'
import bolt from '../icons/bolt.png'
import shield from '../icons/shield.png'
import stack from '../icons/stack.png'
import search from '../icons/search-check.png'
import corrosion from '../icons/corrosion.webp'
import document from '../icons/document-search.png'

const REQUIREMENTS = [
  { text: 'Pitting corrosion — pits must be open at the sample surface edge (connected to the outer background)' },
  { text: 'Single metal sample per image with a dark/black background surrounding it' },
  { text: 'Optical or SEM microscopy image' },
  { text: 'Scale bar in the bottom-right corner is automatically excluded — keep it there if present' },
]

const ACCEPTABLE = [
  { text: 'Image noise and minor brightness variation across the sample' },
  { text: 'Polishing marks (fine parallel scratches on the surface) — filtered out automatically' },
  { text: 'Small circular inclusions or second-phase particles — filtered out automatically' },
  { text: 'Scale bar or measurement widget in the image corner' },
]

const NOT_SUPPORTED = [
  { text: 'Subsurface or buried pits not connected to the sample edge — these will not be detected' },
  { text: 'Other corrosion types (uniform, intergranular, crevice, stress corrosion cracking)' },
  { text: 'Multiple separate metal samples in a single image' },
]

const Home = () => {
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('active'); observer.unobserve(e.target) } }),
      { threshold: 0.1 }
    )
    window.document.querySelectorAll('.fade-in-text').forEach((el) => observer.observe(el))
    return () => observer.disconnect()
  }, [])

  return (
    <>
      <nav>
        <div className="header">
          <div className="header-left-section">
            <img className="header-logo" src={logo} alt="logo" />
            <div className="header-title">CorroScan</div>
          </div>
          <Link to="/extraction" className="header-start">Start Analysis</Link>
        </div>
      </nav>

      <main>
        <section className="start">
          <div className="start-container">
            <div className="start-header">
              <div className="start-header-word">Corrosion Analysis</div>
            </div>
            <div className="start-title">
              <div className="start-title-info">Pitting Corrosion</div>
              <div className="start-title-info">Morphology Analysis</div>
            </div>
            <div className="start-description">
              Upload a microscopy image to classify corrosion severity, measure corroded area,
              and generate a pit depth distribution — all in seconds.
            </div>
            <div className="start-buttons" style={{ marginBottom: '60px' }}>
              <Link to="/extraction" className="analysis-button">
                Start Analysis <span className="analysis-right-arrow">&#8594;</span>
              </Link>
            </div>
          </div>
        </section>

        <div id="features">
          <section>
            <div className="features-container">
              <div className="features-title-container">Powerful Features</div>
              <div className="features-subtitle">Everything you need for comprehensive corrosion morphology analysis</div>
              <div className="features-grid">
                <div className="features-image-analysis-card fade-in-text">
                  <div className="features-icon-container">
                    <img className="features-icon" src={image} />
                  </div>
                  <div className="features-card-title">Advanced Image Analysis</div>
                  <div className="features-card-info">Process high-resolution microscopy images with AI-powered detection algorithms for precise corrosion identification.</div>
                </div>
                <div className="features-processing-card fade-in-text">
                  <div className="features-icon-container">
                    <img className="features-icon" src={bolt} />
                  </div>
                  <div className="features-card-title">Real-time Processing</div>
                  <div className="features-card-info">Analyze images in seconds with our optimized pipeline, reducing turnaround time from hours to minutes.</div>
                </div>
                <div className="features-reporting-card fade-in-text">
                  <div className="features-icon-container">
                    <img className="features-icon" src={document} />
                  </div>
                  <div className="features-card-title">Comprehensive Reporting</div>
                  <div className="features-card-info">Generate detailed reports with quantitative metrics, visualizations, and actionable insights automatically.</div>
                </div>
                <div className="features-quality-assurance-card fade-in-text">
                  <div className="features-icon-container">
                    <img className="features-icon" src={shield} />
                  </div>
                  <div className="features-card-title">Quality Assurance</div>
                  <div className="features-card-info">Ensure consistency and reliability with automated validation and quality control measures.</div>
                </div>
                <div className="features-multi-scale-analysis-card fade-in-text">
                  <div className="features-icon-container">
                    <img className="features-icon" src={stack} />
                  </div>
                  <div className="features-card-title">Multi-Scale Analysis</div>
                  <div className="features-card-info">Examine corrosion at multiple magnifications from macro to nano-scale with seamless integration.</div>
                </div>
                <div className="features-ml-powered-card fade-in-text">
                  <div className="features-icon-container">
                    <img className="features-icon" src={search} />
                  </div>
                  <div className="features-card-title">ML-Powered Classification</div>
                  <div className="features-card-info">Leverage deep learning models trained on thousands of corrosion patterns for accurate type identification.</div>
                </div>
              </div>
            </div>
          </section>
        </div>


        <div id="capabilities">
          <section>
            <div className="capabilities-container">
              <h2 className="capabilities-title">Advanced Capabilities</h2>
              <p className="capabilities-subtitle">Specialized quantification data for corrosion analysis</p>
              <div className="capabilities-main">
                <div className="capabilities-image-container">
                  <img src={corrosion} alt="" className="corrosion-image" />
                </div>
                <div className="capabilities-info-container">
                  <div className="capabilities-info-section">
                    <div className="capabilities-info-title">
                      <h3>Confidence Score</h3>
                      <span>Model Accuracy</span>
                    </div>
                    <p className="capabilities-info-text">Certainty that the model is in its severity prediction</p>
                  </div>
                  <div className="capabilities-info-section">
                    <div className="capabilities-info-title">
                      <h3>Automated Quantification</h3>
                      <span>Pixel Counting & Area %</span>
                    </div>
                    <p className="capabilities-info-text">Outputs number of pixels identified as corrosion pits and its percentage</p>
                  </div>
                  <div className="capabilities-info-section">
                    <div className="capabilities-info-title">
                      <h3>Severity Classification</h3>
                      <span>Limited Accuracy</span>
                    </div>
                    <p className="capabilities-info-text">Map electrochemical activity and material interfaces</p>
                  </div>
                  <div className="capabilities-info-section">
                    <div className="capabilities-info-title">
                      <h3>Detailed Report</h3>
                      <span>Includes Descriptions</span>
                    </div>
                    <p className="capabilities-info-text">Exports PDF report containing all quantification data</p>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      </main>

      <footer>
        <div className="footer-bottom-container" style={{ width: '100%', padding: '0 40px', boxSizing: 'border-box', marginBottom: 0, height: '60px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <img src={logo} alt="" style={{ height: '20px', width: '20px' }} />
            <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px' }}>© 2026 CorroScan</span>
          </div>
        </div>
      </footer>
    </>
  )
}

export default Home
