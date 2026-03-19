import React from 'react'
import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';

import '../styles/header.css'
import '../styles/general.css'
import '../styles/start.css'
import '../styles/features.css'
import '../styles/capabilities.css'
import '../styles/footer.css'

import logo from '../icons/logo.png'
import image from '../icons/image-analysis.svg'
import bolt from '../icons/bolt.png'
import document from '../icons/document-search.png'
import shield from '../icons/shield.png'
import stack from '../icons/stack.png'
import search from '../icons/search-check.png'
import corrosion from '../icons/corrosion.webp'
import heart from '../icons/heart.png'

const Home = () => {
    const [count, setCount] = useState(0)

  useEffect(() => {
    const observerOptions = {
      threshold: 0.1, // Trigger when 10% of the text is visible
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('active');
          // Once it fades in, we don't need to watch it anymore
          observer.unobserve(entry.target);
        }
      });
    }, observerOptions);

    // Use window.document to be 100% sure we are hitting the browser's document
    const elements = window.document.querySelectorAll('.fade-in-text');

    elements.forEach((el) => {
      observer.observe(el);
    });

    return () => observer.disconnect();
  }, []); // The empty array ensures this only runs once on startup



    return (
        <>
            <nav>
                <div className="header">
                    <div className="header-left-section">
                        <img className="header-logo" src={logo} />
                        <div className="header-title">CorroScan</div>
                    </div>
                    <div className="header-middle-section">
                        <a href="#features">Features</a>
                        <a href="#capabilities">Capabilities</a>
                        <a>Industries</a>
                        <a>Technology</a>
                    </div>
                    <div className="header-right-section" />
                    <Link to="/extraction" className="header-start">Get Started</Link>
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
                            <Link to="/extraction" className="analysis-button">Start Analysis <span className="analysis-right-arrow">&#8594;</span></Link>
                            <button className="demo-button">Start Demo</button>
                        </div>
                        <div className="start-stats">
                            <div className="accuracy-stat fade-in-text">
                                <div className="main-stat">99%</div>
                                <div className="sub-stat">Accuracy</div>
                            </div>
                            <div className="faster-analysis-stat fade-in-text">
                                <div className="main-stat">10x</div>
                                <div className="sub-stat">Faster Analysis</div>
                            </div>
                            <div className="corrosion-type-stat fade-in-text">
                                <div className="main-stat">8+</div>
                                <div className="sub-stat">Corrosion Types</div>
                            </div>
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
                            <p className="capabilities-subtitle">Specialized tools for every type of corrosion analysis</p>
                            <div className="capabilities-main">
                                <div className="capabilities-image-container">
                                    <img src={corrosion} alt="" className="corrosion-image" />
                                </div>
                                <div className="capabilities-info-container">
                                    <div className="capabilities-info-section">
                                        <div className="capabilities-info-title">
                                            <h3>Pitting Corrosion Detection</h3>
                                            <span>±0.5μm precision</span>
                                        </div>
                                        <p className="capabilities-info-text">Identify and measure localized pitting with sub-micron accuracy</p>
                                    </div>
                                    <div className="capabilities-info-section">
                                        <div className="capabilities-info-title">
                                            <h3>Stress Corrosion Cracking</h3>
                                            <span>3D reconstruction</span>
                                        </div>
                                        <p className="capabilities-info-text">Analyze crack propagation patterns and stress fields</p>
                                    </div>
                                    <div className="capabilities-info-section">
                                        <div className="capabilities-info-title">
                                            <h3>Galvanic Corrosion</h3>
                                            <span>Multi-material support</span>
                                        </div>
                                        <p className="capabilities-info-text">Map electrochemical activity and material interfaces</p>
                                    </div>
                                    <div className="capabilities-info-section">
                                        <div className="capabilities-info-title">
                                            <h3>Crevice Corrosion</h3>
                                            <span>Deep learning enhanced</span>
                                        </div>
                                        <p className="capabilities-info-text">Detect and characterize hidden corrosion in tight spaces</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>
                </div>

                <div id="technology">
                    <section className="technology">
                        <div className="technology-grid">
                            <div className="technology-left">
                                <h3>Powered by Cutting-Edge Technology</h3>
                                <p>Our platform leverages state-of-the-art machine learning and computer vision techniques to deliver unparalleled accuracy in corrosion analysis.</p>

                            </div>
                            <div className="technology-right"></div>
                        </div>
                    </section>
                </div>

                <div id="industries">
                    <section>
                        <div className="industries-container">
                            <div className="industries-header">
                                <h3>Industry Applications</h3>
                                <p>Reliable resource across organizations</p>
                            </div>
                            <div className="industries-grid">
                                <div className="infrastructure-card"></div>
                                <div></div>
                                <div></div>
                                <div></div>
                            </div>
                        </div>
                    </section>
                </div>

            </main >


            <footer>
                <div className="footer-container">
                    <div className="footer-left">
                        <div className="footer-headers">
                            <img src={logo} alt="" className="logo-icon" />
                            <div className="footer-titles">CorroScan</div>
                        </div>
                        <div className="logo-info">Advanced corrosion morphology analysis powered by AI and machine learning.</div>
                    </div>
                    <div className="footer-middle-left">
                        <div className="footer-headers">
                            <div className="footer-titles">Product</div>
                        </div>
                        <div className="footer-product-info">
                            <p>Features</p>
                            <p>Pricing</p>
                            <p>Documentation</p>
                            <p>Company</p>
                        </div>
                    </div>
                    <div className="footer-middle-right">
                        <div className="footer-headers">
                            <div className="footer-titles">Company</div>
                        </div>
                        <div className="footer-company-info">
                            <p>About</p>
                            <p>Blog</p>
                            <p>Careers</p>
                            <p>Contact</p>
                        </div>
                    </div>
                    <div className="footer-right">
                        <div className="footer-headers">
                            <div className="footer-titles">Legal</div>
                        </div>
                        <div className="footer-legal-info">
                            <p>Privacy</p>
                            <p>Terms</p>
                            <p>Security</p>
                            <p>Compliance</p>
                        </div>
                    </div>
                </div>
                <div className="footer-bottom-container">
                    <div className="footer-copyright">© 2026 CorroScan. All rights reserved.</div>
                    <div className="footer-icons">
                        <img src={heart} />
                    </div>
                </div>
            </footer>
        </>
    )
}

export default Home