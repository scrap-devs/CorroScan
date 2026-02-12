import { useState } from 'react'
import './styles/header.css'
import './styles/general.css'
import './styles/start.css'
import logo from './icons/logo.png'

function App() {
  const [count, setCount] = useState(0)

  return (
    <>
      <nav>
        <div className="header">
          <div className="header-left-section">
            <img className="header-logo" src={logo} />
            <div className="header-title">Corroscan</div>
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
      </main>
    </>
  )
}

export default App
