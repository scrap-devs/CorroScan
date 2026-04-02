"""
api.py
------
Flask API that connects the trained CNN model to the React frontend.

Run with:
    python api.py

Exposes:
    POST /analyze   — accepts an image, returns severity + corroded area + transformed images
"""

import os
import sys
import tempfile
import base64

import cv2
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train import predict_image, build_model, estimate_corroded_area, CONFIG

app  = Flask(__name__)
CORS(app)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "best_model.pth")
_model     = None


def get_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"No trained model found at {MODEL_PATH}. Run train.py first."
            )
        device = CONFIG["device"]
        _model = build_model(num_classes=2, device=device)
        _model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
        _model.eval()
        print("Model loaded.")
    return _model


def to_b64(img_bgr: np.ndarray) -> str:
    _, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return base64.b64encode(buf).decode("utf-8")


def build_transforms(img_bgr: np.ndarray) -> dict:
    """Return a dict of base64-encoded transformed images for the report."""
    h, w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # ── Original ──────────────────────────────────────────────────────
    images = {"original": to_b64(img_bgr)}

    # ── Grayscale ─────────────────────────────────────────────────────
    images["grayscale"] = to_b64(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))

    # ── Corrosion mask (mirrors estimate_corroded_area logic) ─────────
    local_bg  = cv2.GaussianBlur(gray, (61, 61), 0)
    diff      = local_bg.astype(np.int16) - gray.astype(np.int16)
    pit_map   = np.clip(diff, 0, 255).astype(np.uint8)
    _, cmask  = cv2.threshold(pit_map, 40, 255, cv2.THRESH_BINARY)

    _, smask  = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY)
    k_c = np.ones((30, 30), np.uint8)
    k_o = np.ones((10, 10), np.uint8)
    smask = cv2.morphologyEx(smask, cv2.MORPH_CLOSE, k_c)
    smask = cv2.morphologyEx(smask, cv2.MORPH_OPEN,  k_o)
    smask[int(h * 0.82):, int(w * 0.65):] = 0
    cmask = cv2.bitwise_and(cmask, smask)

    k     = np.ones((3, 3), np.uint8)
    cmask = cv2.morphologyEx(cmask, cv2.MORPH_OPEN,  k)
    cmask = cv2.morphologyEx(cmask, cv2.MORPH_CLOSE, k)

    # Shape filter — remove thin vertical scratch lines
    filtered  = np.zeros_like(cmask)
    n_lbl, lbl_map, stats, _ = cv2.connectedComponentsWithStats(cmask, connectivity=8)
    for lbl in range(1, n_lbl):
        cw      = stats[lbl, cv2.CC_STAT_WIDTH]
        ch      = stats[lbl, cv2.CC_STAT_HEIGHT]
        area_cc = stats[lbl, cv2.CC_STAT_AREA]
        if area_cc < 5 or ch > cw * 5:
            continue
        filtered[lbl_map == lbl] = 255
    cmask = filtered

    # ── Segmentation overlay (red highlights on original) ─────────────
    overlay               = img_bgr.copy()
    overlay[cmask > 0]    = (
        overlay[cmask > 0] * 0.4 + np.array([0, 0, 180])
    ).clip(0, 255).astype(np.uint8)
    seg = cv2.addWeighted(img_bgr, 0.5, overlay, 0.5, 0)
    images["segmentation"] = to_b64(seg)

    # ── Binary mask ───────────────────────────────────────────────────
    images["mask"] = to_b64(cv2.cvtColor(cmask, cv2.COLOR_GRAY2BGR))

    # ── Edge detection ────────────────────────────────────────────────
    edges = cv2.Canny(gray, 50, 150)
    images["edges"] = to_b64(cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR))

    return images


@app.route("/analyze", methods=["POST"])
def analyze():
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    file = request.files["image"]

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name
        file.save(tmp_path)

    try:
        model  = get_model()
        result = predict_image(tmp_path, model, CONFIG["device"])
        img    = cv2.imread(tmp_path)
        imgs   = build_transforms(img)

        return jsonify({
            "severity":     result["severity"],
            "confidence":   result["confidence"],
            "probabilities": result["probabilities"],
            "corroded_px":  result["corroded_px"],
            "corroded_pct": result["corroded_pct"],
            "images":       imgs,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    print("Loading model...")
    get_model()
    print("API ready → http://localhost:5000")
    app.run(debug=False, port=5000)
