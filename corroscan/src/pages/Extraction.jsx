import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import jsPDF from 'jspdf'
import logo from '../icons/logo.png'
import '../styles/header.css'
import '../styles/extraction.css'

const Extraction = () => {
  const [dragging,  setDragging]  = useState(false)
  const [imageFile, setImageFile] = useState(null)
  const [preview,   setPreview]   = useState(null)
  const [loading,   setLoading]   = useState(false)
  const [results,   setResults]   = useState(null)
  const [error,     setError]     = useState(null)
  const inputRef = useRef(null)

  const handleFile = (file) => {
    if (!file || !file.type.startsWith('image/')) {
      setError('Please upload an image file.')
      return
    }
    setError(null)
    setResults(null)
    setImageFile(file)
    setPreview(URL.createObjectURL(file))
  }

  const onDrop      = (e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]) }
  const onDragOver  = (e) => { e.preventDefault(); setDragging(true) }
  const onDragLeave = ()  => setDragging(false)
  const onFileInput = (e) => handleFile(e.target.files[0])

  const analyse = async () => {
    if (!imageFile) return
    setLoading(true)
    setError(null)

    const form = new FormData()
    form.append('image', imageFile)

    try {
      const res = await fetch('http://localhost:5000/analyze', { method: 'POST', body: form })
      if (!res.ok) throw new Error('Server error')
      setResults(await res.json())
    } catch {
      setError('Could not reach the analysis server. Make sure api.py is running (python api.py).')
    } finally {
      setLoading(false)
    }
  }

  const downloadPDF = () => {
    const pdf    = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
    const pageW  = pdf.internal.pageSize.getWidth()
    const pageH  = pdf.internal.pageSize.getHeight()
    const margin = 15
    let y = margin

    // Header
    pdf.setFontSize(22); pdf.setTextColor(20, 20, 20)
    pdf.text('CorroScan Analysis Report', margin, y); y += 9

    pdf.setFontSize(10); pdf.setTextColor(120, 120, 120)
    pdf.text(`Generated: ${new Date().toLocaleString()}`, margin, y); y += 5
    pdf.text(`File: ${imageFile.name}`, margin, y); y += 9

    pdf.setDrawColor(200, 200, 200)
    pdf.line(margin, y, pageW - margin, y); y += 8

    // Classification
    pdf.setFontSize(15); pdf.setTextColor(20, 20, 20)
    pdf.text('Classification Results', margin, y); y += 8

    const sev = results.severity
    pdf.setFontSize(13)
    pdf.setTextColor(...(sev === 'severe' ? [239, 68, 68] : [34, 197, 94]))
    pdf.text(`Severity: ${sev.toUpperCase()}`, margin, y); y += 7

    pdf.setFontSize(11); pdf.setTextColor(40, 40, 40)
    pdf.text(`Confidence: ${(results.confidence * 100).toFixed(1)}%`, margin, y); y += 6
    pdf.text(`Corroded Pixels: ${results.corroded_px.toLocaleString()}`, margin, y); y += 6
    pdf.text(`Image Corroded: ${results.corroded_pct}%`, margin, y); y += 9

    // Probabilities
    pdf.setFontSize(11); pdf.setTextColor(20, 20, 20)
    pdf.text('Class Probabilities:', margin, y); y += 6
    Object.entries(results.probabilities).forEach(([lbl, prob]) => {
      pdf.setFontSize(10); pdf.setTextColor(60, 60, 60)
      pdf.text(`  ${lbl}: ${(prob * 100).toFixed(1)}%`, margin, y); y += 5
    }); y += 5

    pdf.setDrawColor(200, 200, 200)
    pdf.line(margin, y, pageW - margin, y); y += 8

    // Images — 2 per row
    pdf.setFontSize(14); pdf.setTextColor(20, 20, 20)
    pdf.text('Image Analysis', margin, y); y += 8

    const imgKeys   = ['original', 'grayscale', 'segmentation', 'mask', 'edges']
    const imgLabels = ['Original', 'Grayscale', 'Corrosion Overlay', 'Corrosion Mask', 'Edge Detection']
    const colW   = (pageW - margin * 2 - 6) / 2
    const colH   = colW * 0.68

    imgKeys.forEach((key, i) => {
      const col = i % 2
      const x   = margin + col * (colW + 6)

      if (col === 0 && i > 0) y += colH + 10
      if (y + colH > pageH - margin) { pdf.addPage(); y = margin }

      pdf.addImage(`data:image/jpeg;base64,${results.images[key]}`, 'JPEG', x, y, colW, colH)
      pdf.setFontSize(9); pdf.setTextColor(80, 80, 80)
      pdf.text(imgLabels[i], x + colW / 2, y + colH + 5, { align: 'center' })
    })

    pdf.save(`corroscan-${imageFile.name.replace(/\.[^.]+$/, '')}.pdf`)
  }

  return (
    <>
      <nav>
        <div className="header">
          <div className="header-left-section">
            <img className="header-logo" src={logo} alt="logo" />
            <div className="header-title">CorroScan</div>
          </div>
          <Link to="/" className="header-start">← Home</Link>
        </div>
      </nav>

      <main className="extraction-main">
        <div className="extraction-container">
          <h1 className="extraction-title">Corrosion Analysis</h1>
          <p className="extraction-subtitle">Upload a pitting corrosion microscopy image to begin</p>

          {/* Drop zone */}
          <div
            className={`drop-zone${dragging ? ' dragging' : ''}${preview ? ' has-image' : ''}`}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onClick={() => inputRef.current.click()}
          >
            <input ref={inputRef} type="file" accept="image/*" onChange={onFileInput} style={{ display: 'none' }} />
            {preview
              ? <img src={preview} alt="Uploaded" className="drop-preview" />
              : (
                <div className="drop-placeholder">
                  <div className="drop-icon">↑</div>
                  <div className="drop-text">Drag & drop your image here</div>
                  <div className="drop-subtext">or click to browse</div>
                </div>
              )
            }
          </div>

          {error && <div className="extraction-error">{error}</div>}

          {preview && !loading && (
            <button className="analyze-btn" onClick={analyse}>
              {results ? 'Re-Analyse' : 'Analyse Image'}
            </button>
          )}

          {loading && (
            <div className="loading-container">
              <div className="spinner" />
              <div className="loading-text">Analysing image...</div>
            </div>
          )}

          {results && (
            <>
              <div className="results-section">
                {/* Severity + stats */}
                <div className="results-header">
                  <div className={`severity-badge ${results.severity}`}>
                    {results.severity.toUpperCase()}
                  </div>
                  <div className="results-stats">
                    <div className="stat-card">
                      <div className="stat-value">{(results.confidence * 100).toFixed(1)}%</div>
                      <div className="stat-label">Confidence</div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-value">{results.corroded_px.toLocaleString()}</div>
                      <div className="stat-label">Corroded Pixels</div>
                      <div className="stat-note">excl. background</div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-value">{results.corroded_pct}%</div>
                      <div className="stat-label">Sample Area Corroded</div>
                      <div className="stat-note">excl. background</div>
                    </div>
                  </div>
                </div>

                {/* Probability bars */}
                <div className="prob-section">
                  {Object.entries(results.probabilities).map(([lbl, prob]) => (
                    <div key={lbl} className="prob-row">
                      <span className="prob-label">{lbl}</span>
                      <div className="prob-bar-bg">
                        <div
                          className="prob-bar-fill"
                          style={{
                            width: `${prob * 100}%`,
                            backgroundColor: lbl === 'severe' ? '#ef4444' : '#22c55e',
                          }}
                        />
                      </div>
                      <span className="prob-value">{(prob * 100).toFixed(1)}%</span>
                    </div>
                  ))}
                </div>

                {/* Transformed images */}
                <h2 className="transforms-title">Image Analysis</h2>
                <div className="transforms-grid">
                  {[
                    { key: 'original',     label: 'Original' },
                    { key: 'grayscale',    label: 'Grayscale' },
                    { key: 'segmentation', label: 'Corrosion Overlay' },
                    { key: 'mask',         label: 'Corrosion Mask' },
                    { key: 'edges',        label: 'Edge Detection' },
                  ].map(({ key, label }) => (
                    <div key={key} className="transform-card">
                      <img
                        src={`data:image/jpeg;base64,${results.images[key]}`}
                        alt={label}
                        className="transform-img"
                      />
                      <div className="transform-label">{label}</div>
                    </div>
                  ))}
                </div>
              </div>

              <button className="pdf-btn" onClick={downloadPDF}>
                Download PDF Report
              </button>
            </>
          )}
        </div>
      </main>
    </>
  )
}

export default Extraction
