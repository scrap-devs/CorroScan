import React from 'react'
import { useEffect } from 'react'
import { Link } from 'react-router-dom'

import '../styles/header.css'
import '../styles/general.css'
import '../styles/start.css'
import '../styles/footer.css'

import logo from '../icons/logo.png'

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

        <section className="requirements-section fade-in-text">
          <div className="requirements-container">
            <h2 className="requirements-heading">Image Guidelines</h2>
            <p className="requirements-subheading">
              For accurate results, ensure your image meets the following requirements.
            </p>

            <div className="requirements-grid">
              <div className="req-card">
                <div className="req-card-header req-required">Required</div>
                <ul className="req-list">
                  {REQUIREMENTS.map((r, i) => (
                    <li key={i} className="req-item">
                      <span className="req-dot req-dot-required" />
                      {r.text}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="req-card">
                <div className="req-card-header req-acceptable">Acceptable</div>
                <ul className="req-list">
                  {ACCEPTABLE.map((r, i) => (
                    <li key={i} className="req-item">
                      <span className="req-dot req-dot-acceptable" />
                      {r.text}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="req-card req-card-wide">
                <div className="req-card-header req-unsupported">Not Supported</div>
                <ul className="req-list">
                  {NOT_SUPPORTED.map((r, i) => (
                    <li key={i} className="req-item">
                      <span className="req-dot req-dot-unsupported" />
                      {r.text}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>
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
