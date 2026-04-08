# CorroScan

Corrosion severity analysis tool for optical microscopy images. Upload a microscope image, and CorroScan classifies corrosion severity, segments corroded area, and produces a pit depth probability distribution.

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 + Vite |
| Backend | Python + Flask |
| Model | EfficientNet-B0 (PyTorch) fine-tuned on pitting corrosion data |
| Image processing | OpenCV, NumPy, SciPy |

## Running locally

### 1. Python backend

```bash
cd corroscan/CNNmodel
pip install -r requirements.txt
python api.py
# API available at http://localhost:5000
```

> Requires a trained model at `corroscan/CNNmodel/best_model.pth`. Run `train.py` first if you don't have one.

### 2. React frontend

```bash
cd corroscan
npm install
npm run dev
# App available at http://localhost:5173
```

## Features

- **Severity classification** — CNN classifies images as Low or High corrosion severity with confidence scores
- **Corroded area** — pixel-level segmentation of corrosion pits, excluding black backgrounds
- **Scale bar tool** — draw over the image's scale bar to convert pixel measurements to real-world units (µm, mm, nm)
- **Pit depth distribution** — KDE probability curve of pit depth measured via distance transform from the convex hull (ideal undamaged surface boundary)
- **PDF export** — full report including stats, probability bars, depth distribution chart, and processed images

## Output

- Severity label + confidence
- Corroded pixel count and percentage of sample area
- Corroded area in real-world units (requires scale bar)
- Max and mean pit depth
- Pit depth KDE distribution plot
- Processed image views: original, grayscale, corrosion overlay, mask, edge detection
