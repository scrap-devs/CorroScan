"""
CorroScan CNN Training Pipeline
================================
- Severity classification : moderate | severe  (EfficientNet-B0, transfer learning)
- Scale bar detection      : OpenCV morphology + pytesseract OCR
- Corrosion area estimation: HSV colour segmentation, result in mm² (or px² fallback)

Expected data layout
--------------------
CNNmodel/
  data/
    rustorbustlabels.csv   # filename,labels
    images/                # all .jpg images
  train.py                 # this file

Install dependencies
--------------------
pip install torch torchvision opencv-python pillow pandas scikit-learn matplotlib pytesseract
# Windows: also install Tesseract-OCR and set TESSERACT_CMD below if not on PATH
"""

import os
import re
import warnings
import numpy as np
import pandas as pd
import cv2
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision import transforms, models
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from PIL import Image
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

# If Tesseract is not on PATH, set the executable path here:
# e.g. TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

try:
    import pytesseract
    if TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    pytesseract.get_tesseract_version()
    HAS_TESSERACT = True
except Exception:
    HAS_TESSERACT = False
    print("[WARNING] pytesseract / Tesseract-OCR not available — "
          "scale bar will not be read; area will be reported in px².")

# ── CONFIG ────────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG = {
    "csv_path":    os.path.join(BASE_DIR, "data", "rustorbustlabels.csv"),
    "images_dir":  os.path.join(BASE_DIR, "data", "images", "Pit Training Data"),
    "img_size":    224,
    "batch_size":  8,
    "epochs":      40,
    "lr":          1e-4,
    "test_size":   0.2,
    "random_seed": 42,
    "num_classes": 2,
    "model_save":  os.path.join(BASE_DIR, "best_model.pth"),
    "device":      "cuda" if torch.cuda.is_available() else "cpu",
}

LABEL_MAP  = {"moderate": 0, "severe": 1}
IDX_TO_LBL = {v: k for k, v in LABEL_MAP.items()}


# ── SCALE BAR DETECTION ───────────────────────────────────────────────────────

def parse_scale_text(text: str):
    """Parse OCR text like '1 mm', '500 µm', '0.5 cm' → value in mm. Returns None on failure."""
    text = text.lower().replace("\n", " ")
    for ch in ("μ", "µ", "u"):
        text = text.replace(ch, "u")
    m = re.search(r"([\d]+(?:[.,][\d]+)?)\s*(nm|um|mm|cm)", text)
    if not m:
        return None
    value = float(m.group(1).replace(",", "."))
    unit  = m.group(2)
    return value * {"nm": 1e-6, "um": 1e-3, "mm": 1.0, "cm": 10.0}[unit]


def detect_scale_bar(image_bgr: np.ndarray):
    """
    Locate the green scale bar widget always in the bottom-right corner.

    The widget is a green comb/ruler graphic with a text label below it
    (e.g. "150 µm", "30 µm"). It sits in roughly the bottom 18%, right 35%
    of the frame.

    The key challenge is that some images are entirely green (fluorescence).
    We distinguish the overlay by requiring VERY high saturation (S > 160) —
    programmatic overlays use pure neon green; organic/optical greens are duller.

    Returns
    -------
    pixels_per_mm : float | None
    bar_length_px : int   | None
    scale_mm      : float | None
    """
    h, w = image_bgr.shape[:2]

    # Crop to the bottom-right corner where the widget always lives
    roi_y = int(h * 0.82)
    roi_x = int(w * 0.65)
    roi   = image_bgr[roi_y:, roi_x:]

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # Neon/programmatic green: H 35-85 (OpenCV 0-180 scale), S > 160, V > 80
    # This excludes dull organic greens present in fluorescence images
    green_mask = cv2.inRange(hsv, (35, 160, 80), (85, 255, 255))

    cnts, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None, None, None

    # The ruler bar is the widest contour in the region
    best_bar = max(cnts, key=lambda c: cv2.boundingRect(c)[2])
    bx, by, bw, bh = cv2.boundingRect(best_bar)

    if bw < 15:   # too small to be a real scale bar
        return None, None, None

    bar_length_px = bw

    if not HAS_TESSERACT:
        return None, bar_length_px, None

    # OCR: grab the full widget area (bar + text label below)
    ox1 = max(0, bx - 5)
    ox2 = min(roi.shape[1], bx + bw + 5)
    oy1 = max(0, by - 5)
    oy2 = min(roi.shape[0], by + bh + 40)
    ocr_crop = roi[oy1:oy2, ox1:ox2]

    # Green channel is brightest for this overlay; upscale 4× for Tesseract
    g_chan = ocr_crop[:, :, 1]
    g_chan = cv2.resize(g_chan, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    _, ocr_bin = cv2.threshold(g_chan, 100, 255, cv2.THRESH_BINARY)

    # No character whitelist — it blocks the µ symbol on many Tesseract builds.
    # parse_scale_text handles noisy output via regex.
    for psm in (7, 6, 8, 13):
        text = pytesseract.image_to_string(ocr_bin, config=f"--psm {psm} --oem 3")
        scale_mm = parse_scale_text(text)
        if scale_mm and scale_mm > 0:
            return bar_length_px / scale_mm, bar_length_px, scale_mm

    return None, bar_length_px, None


# ── CORROSION AREA SEGMENTATION ───────────────────────────────────────────────

def estimate_corroded_area(image_bgr: np.ndarray):
    """
    Detect corrosion as dark pits/regions relative to the local metal surface.

    These images are optical/fluorescence microscopy of polished metal cross-
    sections. Corrosion appears as dark pits or delaminated black regions on
    the metal surface, regardless of the imaging mode:
      - Fluorescence (green image): dark spots on bright green metal
      - Reflected light (golden):   black pits on golden surface
      - Reflected light (white):    dark spots on grey/white surface

    Approach
    --------
    1. Convert to grayscale.
    2. Identify the "sample" region — the actual metal — by excluding the large
       pure-black background regions at the image edges.
    3. Also exclude the scale bar widget (bottom-right corner).
    4. Within the sample, find pixels that are significantly darker than their
       local neighbourhood (Gaussian background subtraction). These are pits.
    5. Return corroded pixel count and percentage of total image area.

    Returns (corroded_px: int, pct_of_image: float).
    """
    h, w = image_bgr.shape[:2]
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    # ── Step 1: find sample region (exclude large dark background) ──
    # The out-of-sample background is a large contiguous very-dark region.
    _, sample_mask = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY)

    # Close small gaps in the metal surface, open away noise
    k_close = np.ones((30, 30), np.uint8)
    k_open  = np.ones((10, 10), np.uint8)
    sample_mask = cv2.morphologyEx(sample_mask, cv2.MORPH_CLOSE, k_close)
    sample_mask = cv2.morphologyEx(sample_mask, cv2.MORPH_OPEN,  k_open)

    # ── Step 2: blank out the scale bar widget (bottom-right corner) ──
    sample_mask[int(h * 0.82):, int(w * 0.65):] = 0

    # ── Step 3: local contrast dark-pit detection (large kernel) ──
    # A 201px blur includes surrounding bright metal even for 200-400px wide
    # dark bands, so band interiors get nonzero contrast and are detected.
    local_bg = cv2.GaussianBlur(gray, (201, 201), 0)
    diff     = local_bg.astype(np.int16) - gray.astype(np.int16)
    pit_map  = np.clip(diff, 0, 255).astype(np.uint8)

    sample_vals = pit_map[sample_mask > 0].astype(np.uint8)
    thresh_otsu, _ = cv2.threshold(sample_vals.reshape(1, -1), 0, 255,
                                   cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thresh = max(20, int(thresh_otsu))
    _, raw = cv2.threshold(pit_map, thresh, 255, cv2.THRESH_BINARY)
    raw = cv2.bitwise_and(raw, sample_mask)

    # Suppress polishing marks with circular morphological opening.
    # Marks are thin lines (1-3 px wide) regardless of angle; a 9×9 disk
    # removes them while preserving genuine pits (10-20+ px blobs) and bands.
    disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    corr_mask = cv2.morphologyEx(raw, cv2.MORPH_OPEN, disk)

    # Morphological cleanup — remove single-pixel noise, close tiny gaps
    k = np.ones((3, 3), np.uint8)
    corr_mask = cv2.morphologyEx(corr_mask, cv2.MORPH_OPEN,  k)
    corr_mask = cv2.morphologyEx(corr_mask, cv2.MORPH_CLOSE, k)

    # ── Step 4: shape filter — remove scratch lines ──
    # Polishing/grinding marks are thin vertical lines (height >> width).
    # Real corrosion pits are roughly blob-shaped.
    # Filter out connected components where height > 5 × width.
    filtered = np.zeros_like(corr_mask)
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(corr_mask, connectivity=8)
    for lbl in range(1, n_labels):
        cw = stats[lbl, cv2.CC_STAT_WIDTH]
        ch = stats[lbl, cv2.CC_STAT_HEIGHT]
        area_cc = stats[lbl, cv2.CC_STAT_AREA]
        if area_cc < 30:       # skip noise and fine texture fragments
            continue
        if ch > cw * 5:        # tall & thin → scratch line, skip
            continue
        filtered[labels == lbl] = 255
    corr_mask = filtered

    corroded_px  = int(np.sum(corr_mask > 0))
    sample_px    = int(np.sum(sample_mask > 0))
    pct_of_sample = round(100.0 * corroded_px / max(sample_px, 1), 2)

    return corroded_px, pct_of_sample, sample_px


# ── DATASET ───────────────────────────────────────────────────────────────────

class CorrosionDataset(Dataset):
    def __init__(self, df: pd.DataFrame, images_dir: str, transform=None):
        self.df         = df.reset_index(drop=True)
        self.images_dir = images_dir
        self.transform  = transform

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row      = self.df.iloc[idx]
        img_path = os.path.join(self.images_dir, row["filename"])
        label    = LABEL_MAP[row["labels"]]

        img_bgr = cv2.imread(img_path)
        if img_bgr is None:
            raise FileNotFoundError(f"Image not found: {img_path}")

        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)

        if self.transform:
            img_pil = self.transform(img_pil)
        return img_pil, label


# ── MODEL ─────────────────────────────────────────────────────────────────────

def build_model(num_classes: int, device: str) -> nn.Module:
    """EfficientNet-B0 pretrained on ImageNet, fine-tuned classifier head."""
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.4),
        nn.Linear(in_features, 128),
        nn.ReLU(),
        nn.Dropout(p=0.2),
        nn.Linear(128, num_classes),
    )
    return model.to(device)


# ── TRANSFORMS ────────────────────────────────────────────────────────────────

def get_transforms(img_size: int):
    train_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(20),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.05),
        transforms.RandomAffine(degrees=0, translate=(0.05, 0.05)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    return train_tf, val_tf


# ── TRAINING HELPERS ──────────────────────────────────────────────────────────

def make_weighted_sampler(df: pd.DataFrame) -> WeightedRandomSampler:
    """Over-sample minority class to counter imbalance (19 moderate vs 52 severe)."""
    labels  = df["labels"].map(LABEL_MAP).values
    counts  = np.bincount(labels)
    weights = 1.0 / counts[labels]
    return WeightedRandomSampler(weights.tolist(), num_samples=len(weights), replacement=True)


def train_one_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss, correct, total = 0.0, 0, 0
    for imgs, labels in loader:
        imgs, labels = imgs.to(device), labels.to(device)
        optimizer.zero_grad()
        out  = model(imgs)
        loss = criterion(out, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * imgs.size(0)
        correct    += (out.argmax(1) == labels).sum().item()
        total      += imgs.size(0)
    return total_loss / total, correct / total


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss, correct, total = 0.0, 0, 0
    all_preds, all_labels = [], []
    for imgs, labels in loader:
        imgs, labels = imgs.to(device), labels.to(device)
        out  = model(imgs)
        loss = criterion(out, labels)
        total_loss += loss.item() * imgs.size(0)
        preds       = out.argmax(1)
        correct    += (preds == labels).sum().item()
        total      += imgs.size(0)
        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())
    return total_loss / total, correct / total, all_preds, all_labels


def plot_history(train_losses, val_losses, train_accs, val_accs):
    save_path = os.path.join(BASE_DIR, "training_history.png")
    epochs = range(1, len(train_losses) + 1)
    _, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    ax1.plot(epochs, train_losses, label="Train")
    ax1.plot(epochs, val_losses,   label="Val")
    ax1.set_title("Loss"); ax1.set_xlabel("Epoch"); ax1.legend(); ax1.grid(True)
    ax2.plot(epochs, train_accs, label="Train")
    ax2.plot(epochs, val_accs,   label="Val")
    ax2.set_title("Accuracy"); ax2.set_xlabel("Epoch"); ax2.legend(); ax2.grid(True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=120)
    plt.close()
    print(f"Training history saved → {save_path}")


# ── INFERENCE (single image) ──────────────────────────────────────────────────

def predict_image(image_path: str, model: nn.Module, device: str, img_size: int = 224) -> dict:
    """
    Full inference on one image.

    Returns a dict with:
      severity, confidence, probabilities,
      corroded_px, corroded_pct
    """
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        raise FileNotFoundError(f"Cannot open: {image_path}")

    # Corrosion area
    corroded_px, corroded_pct, sample_px = estimate_corroded_area(img_bgr)  # sample_px excludes black background

    # Classification
    tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    tensor = tf(Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)))
    tensor = tensor.unsqueeze(0).to(device)

    model.eval()
    with torch.no_grad():
        logits = model(tensor)
        probs  = torch.softmax(logits, dim=1).squeeze().cpu().numpy()
    pred = int(probs.argmax())

    return {
        "severity":      IDX_TO_LBL[pred],
        "confidence":    float(probs[pred]),
        "probabilities": {IDX_TO_LBL[i]: float(p) for i, p in enumerate(probs)},
        "corroded_px":   corroded_px,
        "corroded_pct":  corroded_pct,   # % of sample area only (excludes black background)
        "sample_px":     sample_px,
    }


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    cfg    = CONFIG
    device = cfg["device"]
    print(f"Device : {device}")
    print(f"Tesseract available: {HAS_TESSERACT}\n")

    # Load CSV
    df = pd.read_csv(cfg["csv_path"])
    df["filename"] = df["filename"].str.strip()
    df["labels"]   = df["labels"].str.strip().str.lower()
    df = df[df["labels"].isin(LABEL_MAP)].drop_duplicates("filename").reset_index(drop=True)

    label_counts = df["labels"].value_counts().to_dict()
    print(f"Dataset: {len(df)} images  |  {label_counts}")

    # Verify images exist; warn on missing
    missing = [r["filename"] for _, r in df.iterrows()
               if not os.path.exists(os.path.join(cfg["images_dir"], r["filename"]))]
    if missing:
        print(f"[WARNING] {len(missing)} image(s) not found in {cfg['images_dir']}:")
        for m in missing[:5]:
            print(f"  {m}")
        if len(missing) > 5:
            print(f"  ... and {len(missing) - 5} more")
        df = df[~df["filename"].isin(missing)].reset_index(drop=True)
        print(f"Continuing with {len(df)} images.\n")

    if len(df) < 4:
        raise RuntimeError("Too few images to train. Place images in data/images/.")

    # Stratified train/test split
    train_df, test_df = train_test_split(
        df,
        test_size=cfg["test_size"],
        random_state=cfg["random_seed"],
        stratify=df["labels"],
    )
    print(f"Train : {len(train_df)}  |  Test : {len(test_df)}\n")

    train_tf, val_tf = get_transforms(cfg["img_size"])

    train_ds = CorrosionDataset(train_df, cfg["images_dir"], train_tf)
    test_ds  = CorrosionDataset(test_df,  cfg["images_dir"], val_tf)

    sampler      = make_weighted_sampler(train_df)
    train_loader = DataLoader(train_ds, batch_size=cfg["batch_size"],
                              sampler=sampler, num_workers=0, pin_memory=(device == "cuda"))
    test_loader  = DataLoader(test_ds,  batch_size=cfg["batch_size"],
                              shuffle=False, num_workers=0, pin_memory=(device == "cuda"))

    # Class-weighted loss (handles imbalance on top of oversampling)
    counts  = train_df["labels"].value_counts()
    class_w = torch.tensor(
        [1.0 / counts.get(IDX_TO_LBL[i], 1) for i in range(cfg["num_classes"])],
        dtype=torch.float,
    ).to(device)

    model     = build_model(cfg["num_classes"], device)
    criterion = nn.CrossEntropyLoss(weight=class_w)
    optimizer = optim.AdamW(model.parameters(), lr=cfg["lr"], weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=cfg["epochs"])

    best_val_acc = 0.0
    train_losses, val_losses, train_accs, val_accs = [], [], [], []

    print(f"{'Epoch':>6}  {'TrLoss':>8}  {'TrAcc':>7}  {'VlLoss':>8}  {'VlAcc':>7}")
    print("─" * 50)

    for epoch in range(1, cfg["epochs"] + 1):
        tr_loss, tr_acc                   = train_one_epoch(model, train_loader, criterion, optimizer, device)
        vl_loss, vl_acc, preds, gt_labels = evaluate(model, test_loader, criterion, device)
        scheduler.step()

        train_losses.append(tr_loss); val_losses.append(vl_loss)
        train_accs.append(tr_acc);   val_accs.append(vl_acc)

        marker = " *" if vl_acc > best_val_acc else ""
        print(f"{epoch:>6}  {tr_loss:>8.4f}  {tr_acc:>7.3f}  {vl_loss:>8.4f}  {vl_acc:>7.3f}{marker}")

        if vl_acc > best_val_acc:
            best_val_acc = vl_acc
            torch.save(model.state_dict(), cfg["model_save"])

    print(f"\nBest val accuracy: {best_val_acc:.3f}")
    print(f"Model saved → {cfg['model_save']}\n")

    # Final evaluation with best weights
    model.load_state_dict(torch.load(cfg["model_save"], map_location=device))
    _, _, preds, gt_labels = evaluate(model, test_loader, criterion, device)

    print("─── Test Set Classification Report ───")
    print(classification_report(
        gt_labels, preds,
        target_names=[IDX_TO_LBL[i] for i in range(cfg["num_classes"])],
    ))
    cm = confusion_matrix(gt_labels, preds)
    print(f"Confusion matrix (rows=actual, cols=predicted):")
    print(f"  {'  '.join(IDX_TO_LBL[i] for i in range(cfg['num_classes']))}")
    for i, row in enumerate(cm):
        print(f"  {IDX_TO_LBL[i]:<10}  {row}")

    plot_history(train_losses, val_losses, train_accs, val_accs)

    # Per-image inference demo on test set
    print("\n─── Per-image Inference (test set) ───")
    for _, row in test_df.iterrows():
        img_path = os.path.join(cfg["images_dir"], row["filename"])
        if not os.path.exists(img_path):
            continue
        result = predict_image(img_path, model, device, cfg["img_size"])
        correct = "[OK]" if result["severity"] == row["labels"] else "[X]"
        print(f"{correct} {row['filename']}")
        print(f"     Truth      : {row['labels']}")
        print(f"     Prediction : {result['severity']}  (conf={result['confidence']:.1%})")
        print(f"     Corroded   : {result['corroded_px']} px  ({result['corroded_pct']}% of image)")
        print()


if __name__ == "__main__":
    main()
