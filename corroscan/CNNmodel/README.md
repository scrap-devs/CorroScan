# CorroScan — CNN Model

Classifies corrosion severity from optical/fluorescence microscopy images and estimates the corroded area using the scale bar embedded in each image.

## What it does

| Output | How |
|--------|-----|
| **Severity** — `moderate` or `severe` | EfficientNet-B0 pretrained on ImageNet, fine-tuned on the labelled dataset |
| **Corroded area** — in mm² (or px² fallback) | OpenCV local-contrast segmentation + scale bar pixel-to-mm conversion |

The model handles three image types from the microscope:
- Fluorescence (green channel) images
- Reflected light — golden surface
- Reflected light — white/grey surface

---

## Setup

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Install Tesseract-OCR (for scale bar text reading)
Download and install from: https://github.com/UB-Mannheim/tesseract/wiki

Then open `train.py` and set the path near the top:
```python
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

### 3. Arrange your data
```
CNNmodel/
  data/
    rustorbustlabels.csv        # filename, labels (moderate/severe)
    images/
      Pit Training Data/        # all .jpg images go here
```

---

## Usage

### Test the CV pipeline first (no training needed)
Checks scale bar detection and corrosion segmentation on your images before committing to a full training run.
```bash
python test_pipeline.py
```
Outputs go to `debug_output/`. Each image produces:
- `_1_scalebar.jpg` — detected scale bar region highlighted
- `_2_segmentation.jpg` — corrosion highlighted in red over the original
- `_3_mask.jpg` — raw binary corrosion mask

You can also test a single image:
```bash
python test_pipeline.py "path/to/image.jpg"
```

### Train the model
```bash
python train.py
```
- Runs a stratified 80/20 train/test split
- Handles class imbalance (weighted sampler + weighted loss)
- Saves the best model to `best_model.pth`
- Saves a training curve plot to `training_history.png`
- Prints a full classification report and per-image inference results

---

## Files

| File | Purpose |
|------|---------|
| `train.py` | Full pipeline: scale bar detection, segmentation, CNN training, inference |
| `test_pipeline.py` | Visual diagnostic — run this before training to verify CV outputs |
| `requirements.txt` | Python dependencies |
| `best_model.pth` | Saved model weights (created after training) |
| `training_history.png` | Loss/accuracy curves (created after training) |
| `debug_output/` | Visual outputs from test_pipeline.py |
