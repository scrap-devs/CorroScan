# CorroScan

AI-powered pitting corrosion analysis platform. Upload a microscopy image, get a severity classification, corroded area estimate, and a downloadable PDF report.

---

## How the app works

```
React frontend (Vite)
  └── /extraction page
        drag & drop image upload
            │
            │  POST /analyze  (multipart image)
            ▼
        Flask API  (api.py — port 5000)
            │
            ├── CNN model (best_model.pth)
            │     EfficientNet-B0 → severity + confidence
            │
            ├── OpenCV segmentation
            │     Otsu threshold + convex hull + distance transform
            │     → corroded px, % of sample, pit depth KDE (pixels)
            │
            └── Image transforms
                  original, grayscale, corrosion overlay,
                  binary mask, edge detection  (returned as base64)
            │
            │  JSON response
            ▼
        Frontend renders results
            └── Download PDF report (jsPDF)
```

---

## Running locally

You need **two terminals open at the same time**.

### Prerequisites
- Python 3.9+
- Node.js 18+

### 1. Install dependencies

```bash
# Python
cd corroscan/CNNmodel
pip install -r requirements.txt

# Frontend
cd corroscan
npm install
```

### 2. Train the model (first time only)

```bash
cd corroscan/CNNmodel
python train.py
```

This produces `best_model.pth`. You only need to re-run this if you add new training data.

### 3. Start the API

```bash
cd corroscan/CNNmodel
python api.py
```

Runs on `http://localhost:5000`

### 4. Start the frontend

```bash
cd corroscan
npm run dev
```

Runs on `http://localhost:5173`

Open the browser, click **Start Analysis**, drop in an image and hit **Analyse Image**.

---

## Project structure

```
CorroScan/
├── README.md
└── corroscan/
    ├── src/
    │   ├── pages/
    │   │   ├── Home.jsx          landing page
    │   │   └── Extraction.jsx    drag & drop + results + PDF
    │   └── styles/               CSS files
    ├── CNNmodel/
    │   ├── train.py              CNN definition, training, inference functions
    │   ├── api.py                Flask API (connects model to frontend)
    │   ├── predict.py            CLI inference (no frontend needed)
    │   ├── test_pipeline.py      debug tool — visualises CV outputs
    │   ├── best_model.pth        trained model weights
    │   ├── requirements.txt      Python dependencies
    │   └── data/
    │       ├── rustorbustlabels.csv
    │       └── images/
    │           └── Pit Training Data/   ← microscopy images
    └── package.json
```
