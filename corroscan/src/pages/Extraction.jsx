import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import jsPDF from 'jspdf'
import logo from '../icons/logo.png'
import '../styles/header.css'
import '../styles/extraction.css'

const Extraction = () => {
  const [dragging,   setDragging]   = useState(false)
  const [imageFile,  setImageFile]  = useState(null)
  const [preview,    setPreview]    = useState(null)
  const [loading,    setLoading]    = useState(false)
  const [results,    setResults]    = useState(null)
  const [error,      setError]      = useState(null)
  const [filePath,   setFilePath]   = useState(null)

  // Scale bar drawing state
  const [scaleMode,     setScaleMode]     = useState(false)
  const [scaleLine,     setScaleLine]     = useState(null)   // {x1,y1,x2,y2} in canvas coords
  const [scaleValue,    setScaleValue]    = useState('')     // e.g. "150"
  const [scaleUnit,     setScaleUnit]     = useState('µm')   // µm or mm
  const [pixelsPerUnit, setPixelsPerUnit] = useState(null)
  const [drawing,       setDrawing]       = useState(false)
  const [drawStart,     setDrawStart]     = useState(null)

  const inputRef  = useRef(null)
  const canvasRef = useRef(null)
  const imgRef    = useRef(null)

  const handleFile = (file) => {
    if (!file || !file.type.startsWith('image/')) {
      setError('Please upload an image file.')
      return
    }
    setError(null)
    setResults(null)
    setScaleLine(null)
    setScaleValue('')
    setPixelsPerUnit(null)
    setScaleMode(false)
    setImageFile(file)
    setFilePath(file.path || file.webkitRelativePath || file.name)
    setPreview(URL.createObjectURL(file))
  }

  const onDrop      = (e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]) }
  const onDragOver  = (e) => { e.preventDefault(); setDragging(true) }
  const onDragLeave = ()  => setDragging(false)
  const onFileInput = (e) => handleFile(e.target.files[0])

  // Redraw canvas whenever scaleLine changes
  useEffect(() => {
    if (!canvasRef.current || !imgRef.current) return
    const canvas = canvasRef.current
    const img    = imgRef.current
    canvas.width  = img.clientWidth
    canvas.height = img.clientHeight
    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    if (scaleLine) {
      const { x1, y1, x2, y2 } = scaleLine
      ctx.strokeStyle = '#facc15'
      ctx.lineWidth   = 3
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke()
      // End caps
      const capLen = 10
      const angle  = Math.atan2(y2 - y1, x2 - x1) + Math.PI / 2
      ;[[x1,y1],[x2,y2]].forEach(([cx,cy]) => {
        ctx.beginPath()
        ctx.moveTo(cx + Math.cos(angle)*capLen/2, cy + Math.sin(angle)*capLen/2)
        ctx.lineTo(cx - Math.cos(angle)*capLen/2, cy - Math.sin(angle)*capLen/2)
        ctx.stroke()
      })
      // Label
      const px = Math.round(Math.hypot(x2-x1, y2-y1))
      ctx.fillStyle = '#facc15'
      ctx.font = 'bold 13px sans-serif'
      ctx.fillText(`${px}px`, (x1+x2)/2 + 6, (y1+y2)/2 - 6)
    }
  }, [scaleLine])

  const getCanvasCoords = (e) => {
    const rect = canvasRef.current.getBoundingClientRect()
    return { x: e.clientX - rect.left, y: e.clientY - rect.top }
  }

  const onCanvasMouseDown = (e) => {
    if (!scaleMode) return
    setDrawing(true)
    const pt = getCanvasCoords(e)
    setDrawStart(pt)
    setScaleLine({ x1: pt.x, y1: pt.y, x2: pt.x, y2: pt.y })
  }

  const onCanvasMouseMove = (e) => {
    if (!drawing || !drawStart) return
    const pt = getCanvasCoords(e)
    setScaleLine({ x1: drawStart.x, y1: drawStart.y, x2: pt.x, y2: pt.y })
  }

  const onCanvasMouseUp = () => setDrawing(false)

  const applyScale = () => {
    if (!scaleLine || !scaleValue || isNaN(parseFloat(scaleValue))) return
    const { x1, y1, x2, y2 } = scaleLine
    // Scale the pixel distance back to original image coords
    const img         = imgRef.current
    const scaleX      = img.naturalWidth  / img.clientWidth
    const linePx      = Math.hypot(x2 - x1, y2 - y1) * scaleX
    const ppu         = linePx / parseFloat(scaleValue)
    setPixelsPerUnit(ppu)
  }

  const realArea = () => {
    if (!results || !pixelsPerUnit) return null
    const area = results.corroded_px / (pixelsPerUnit ** 2)
    return { value: area.toFixed(4), unit: `${scaleUnit}²` }
  }

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
    const wrappedPath = pdf.splitTextToSize(`File: ${filePath}`, pageW - margin * 2)
    pdf.text(wrappedPath, margin, y); y += wrappedPath.length * 5 + 4

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
    pdf.text(`Confidence: ${(results.confidence * 100).toFixed(1)}%`, margin, y); y += 5
    pdf.setFontSize(9); pdf.setTextColor(100, 100, 100)
    pdf.text('How certain the model is in its severity prediction. Above 85% is considered reliable.', margin, y); y += 7

    pdf.setFontSize(11); pdf.setTextColor(40, 40, 40)
    pdf.text(`Corroded Pixels: ${results.corroded_px.toLocaleString()}`, margin, y); y += 5
    pdf.setFontSize(9); pdf.setTextColor(100, 100, 100)
    pdf.text('Number of pixels identified as corrosion pits. Black background is excluded.', margin, y); y += 7

    pdf.setFontSize(11); pdf.setTextColor(40, 40, 40)
    pdf.text(`Sample Area Corroded: ${results.corroded_pct}%`, margin, y); y += 5
    pdf.setFontSize(9); pdf.setTextColor(100, 100, 100)
    pdf.text('Corroded pixels as a percentage of the metal sample area only (black background excluded).', margin, y); y += 7

    const area = realArea()
    if (area) {
      pdf.setFontSize(11); pdf.setTextColor(40, 40, 40)
      pdf.text(`Corroded Area: ${area.value} ${area.unit}`, margin, y); y += 5
      pdf.setFontSize(9); pdf.setTextColor(100, 100, 100)
      pdf.text(`Calculated from user-defined scale: 1 ${scaleUnit} = ${(results.corroded_px / parseFloat(area.value) ** 0.5).toFixed(1)} px`, margin, y); y += 7
    }

    y += 2
    // Probabilities
    pdf.setFontSize(11); pdf.setTextColor(20, 20, 20)
    pdf.text('Class Probabilities:', margin, y); y += 5
    pdf.setFontSize(9); pdf.setTextColor(100, 100, 100)
    pdf.text("The model's probability score for each severity class. Both scores sum to 100%.", margin, y); y += 6
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
    const colW = (pageW - margin * 2 - 6) / 2
    const colH = colW * 0.68

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

  const area = realArea()

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
          {!preview && (
            <div
              className={`drop-zone${dragging ? ' dragging' : ''}`}
              onDrop={onDrop}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onClick={() => inputRef.current.click()}
            >
              <input ref={inputRef} type="file" accept="image/*" onChange={onFileInput} style={{ display: 'none' }} />
              <div className="drop-placeholder">
                <div className="drop-icon">↑</div>
                <div className="drop-text">Drag & drop your image here</div>
                <div className="drop-subtext">or click to browse</div>
              </div>
            </div>
          )}

          {/* Image + canvas overlay for scale drawing */}
          {preview && (
            <div className="image-canvas-wrapper">
              <img
                ref={imgRef}
                src={preview}
                alt="Uploaded"
                className="drop-preview"
                draggable={false}
              />
              <canvas
                ref={canvasRef}
                className={`scale-canvas${scaleMode ? ' active' : ''}`}
                onMouseDown={onCanvasMouseDown}
                onMouseMove={onCanvasMouseMove}
                onMouseUp={onCanvasMouseUp}
                onMouseLeave={onCanvasMouseUp}
              />
            </div>
          )}

          {/* Scale bar tool */}
          {preview && (
            <div className="scale-tool">
              <button
                className={`scale-toggle-btn${scaleMode ? ' active' : ''}`}
                onClick={() => { setScaleMode(m => !m); setScaleLine(null); setPixelsPerUnit(null) }}
              >
                {scaleMode ? 'Cancel Scale Drawing' : 'Draw Scale Bar'}
              </button>
              {scaleMode && (
                <div className="scale-inputs">
                  <span className="scale-instruction">Click and drag on the image to mark the scale bar length</span>
                  {scaleLine && (
                    <>
                      <span className="scale-px-label">
                        Line: {Math.round(Math.hypot(scaleLine.x2 - scaleLine.x1, scaleLine.y2 - scaleLine.y1))} px (display) drawn
                      </span>
                      <div className="scale-value-row">
                        <span>This line =</span>
                        <input
                          type="number"
                          className="scale-value-input"
                          value={scaleValue}
                          onChange={e => setScaleValue(e.target.value)}
                          placeholder="e.g. 150"
                          min="0"
                        />
                        <select className="scale-unit-select" value={scaleUnit} onChange={e => setScaleUnit(e.target.value)}>
                          <option value="µm">µm</option>
                          <option value="mm">mm</option>
                          <option value="nm">nm</option>
                        </select>
                        <button className="apply-scale-btn" onClick={applyScale} disabled={!scaleValue}>
                          Apply
                        </button>
                      </div>
                      {pixelsPerUnit && (
                        <span className="scale-set-label">
                          Scale set: {pixelsPerUnit.toFixed(2)} px / {scaleUnit}
                        </span>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          )}

          {error && <div className="extraction-error">{error}</div>}

          {preview && !loading && (
            <div className="action-row">
              <button className="analyze-btn" onClick={analyse}>
                {results ? 'Re-Analyse' : 'Analyse Image'}
              </button>
              <button className="change-btn" onClick={() => { setPreview(null); setImageFile(null); setResults(null); setScaleLine(null); setPixelsPerUnit(null); setScaleMode(false) }}>
                Change Image
              </button>
            </div>
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
                    {area && (
                      <div className="stat-card highlight">
                        <div className="stat-value">{area.value}</div>
                        <div className="stat-label">Corroded Area ({area.unit})</div>
                        <div className="stat-note">from scale bar</div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Stat explanations */}
                <div className="stat-explanations">
                  <div className="stat-explanation-row">
                    <span className="stat-explanation-label">Confidence</span>
                    <span className="stat-explanation-text">How certain the model is in its severity prediction. Above 85% is considered reliable.</span>
                  </div>
                  <div className="stat-explanation-row">
                    <span className="stat-explanation-label">Corroded Pixels</span>
                    <span className="stat-explanation-text">Number of pixels identified as corrosion pits. Black background is excluded from the count.</span>
                  </div>
                  <div className="stat-explanation-row">
                    <span className="stat-explanation-label">Sample Area Corroded</span>
                    <span className="stat-explanation-text">Corroded pixels as a percentage of the visible metal sample only — black background is not counted.</span>
                  </div>
                  {area && (
                    <div className="stat-explanation-row">
                      <span className="stat-explanation-label">Corroded Area</span>
                      <span className="stat-explanation-text">Real-world area calculated from the scale bar you drew. Based on {pixelsPerUnit.toFixed(2)} px/{scaleUnit}.</span>
                    </div>
                  )}
                </div>

                {/* Probability bars */}
                <div className="prob-section">
                  <div className="prob-header-text">The model scores each severity class — both scores sum to 100%.</div>
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
