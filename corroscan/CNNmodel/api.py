"""
api.py
------
Flask API that connects the trained CNN model to the React frontend.

Run with:
    python api.py

Exposes:
    POST /analyze   -- accepts an image, returns severity + corroded area + depth distribution + transformed images
"""

import io
import os
import sys
import tempfile
import base64

import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
from flask import Flask, request, jsonify
from flask_cors import CORS
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train import predict_image, build_model, CONFIG

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


def _get_masks(img_bgr: np.ndarray):
    """
    Shared helper — returns (smask, cmask, gray).
    Mirrors estimate_corroded_area so all functions use identical masks.
    """
    h, w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    _, smask = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY)
    k_c = np.ones((30, 30), np.uint8)
    k_o = np.ones((10, 10), np.uint8)
    smask = cv2.morphologyEx(smask, cv2.MORPH_CLOSE, k_c)
    smask = cv2.morphologyEx(smask, cv2.MORPH_OPEN,  k_o)
    smask[int(h * 0.82):, int(w * 0.65):] = 0

    local_bg = cv2.GaussianBlur(gray, (61, 61), 0)
    diff     = local_bg.astype(np.int16) - gray.astype(np.int16)
    pit_map  = np.clip(diff, 0, 255).astype(np.uint8)
    _, cmask = cv2.threshold(pit_map, 40, 255, cv2.THRESH_BINARY)
    cmask    = cv2.bitwise_and(cmask, smask)

    k     = np.ones((3, 3), np.uint8)
    cmask = cv2.morphologyEx(cmask, cv2.MORPH_OPEN,  k)
    cmask = cv2.morphologyEx(cmask, cv2.MORPH_CLOSE, k)

    filtered  = np.zeros_like(cmask)
    n_lbl, lbl_map, stats, _ = cv2.connectedComponentsWithStats(cmask, connectivity=8)
    for lbl in range(1, n_lbl):
        cw      = stats[lbl, cv2.CC_STAT_WIDTH]
        ch      = stats[lbl, cv2.CC_STAT_HEIGHT]
        area_cc = stats[lbl, cv2.CC_STAT_AREA]
        if area_cc < 5 or ch > cw * 5:
            continue
        filtered[lbl_map == lbl] = 255

    return smask, filtered, gray


def build_transforms(img_bgr: np.ndarray, smask, cmask, gray) -> dict:
    images = {"original": to_b64(img_bgr)}
    images["grayscale"] = to_b64(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))

    overlay            = img_bgr.copy()
    overlay[cmask > 0] = (
        overlay[cmask > 0] * 0.4 + np.array([0, 0, 180])
    ).clip(0, 255).astype(np.uint8)
    seg = cv2.addWeighted(img_bgr, 0.5, overlay, 0.5, 0)
    images["segmentation"] = to_b64(seg)

    images["mask"]  = to_b64(cv2.cvtColor(cmask, cv2.COLOR_GRAY2BGR))
    edges           = cv2.Canny(gray, 50, 150)
    images["edges"] = to_b64(cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR))

    return images


def compute_depth_stats(smask, cmask) -> dict:
    """
    Measure corrosion pit depth using a distance transform.

    Each pixel in the sample mask is assigned its distance to the nearest
    sample edge (the metal surface). Pit pixels deeper inside the material
    get higher values — this is their depth from the surface.

    The probability distribution is a smooth KDE curve (kernel density
    estimate), giving a continuous distribution of depth across all pit
    pixels — similar to a Maxwell-Boltzmann curve in chemistry.
    """
    if np.sum(cmask > 0) == 0:
        return {
            "max_depth_px":  0.0,
            "mean_depth_px": 0.0,
            "kde_x":         [],
            "kde_y":         [],
            "hist_img":      None,
        }

    # Distance transform — depth of each sample pixel from nearest surface
    dist       = cv2.distanceTransform(smask, cv2.DIST_L2, 5)
    pit_depths = dist[cmask > 0].astype(float)

    # Subsample for KDE if too many points (keeps it fast)
    if len(pit_depths) > 50_000:
        rng = np.random.default_rng(42)
        pit_depths = rng.choice(pit_depths, 50_000, replace=False)

    max_depth  = float(pit_depths.max())
    mean_depth = float(pit_depths.mean())

    # ── KDE curve ─────────────────────────────────────────────────────
    kde    = gaussian_kde(pit_depths, bw_method="scott")
    x_vals = np.linspace(0, max_depth * 1.05, 300)
    y_vals = kde(x_vals)

    # ── Matplotlib plot ────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(7, 3.5))

    ax.fill_between(x_vals, y_vals, alpha=0.35, color="#ef4444")
    ax.plot(x_vals, y_vals, color="#ef4444", linewidth=2.5)

    ax.axvline(max_depth,  color="#facc15", linestyle="--", linewidth=2,
               label=f"Max depth:  {max_depth:.1f} px")
    ax.axvline(mean_depth, color="#60a5fa", linestyle="--", linewidth=2,
               label=f"Mean depth: {mean_depth:.1f} px")

    ax.set_xlabel("Depth from surface (px)", color="#c0c4d6", fontsize=11)
    ax.set_ylabel("Probability density",     color="#c0c4d6", fontsize=11)
    ax.set_title("Corrosion Pit Depth Distribution",
                 color="#ffffff", fontsize=13, pad=10)
    ax.legend(facecolor="#1a1f2e", labelcolor="#c0c4d6", edgecolor="#2e3147")
    ax.set_facecolor("#1a1f2e")
    fig.patch.set_facecolor("#0f1117")
    ax.tick_params(colors="#8b8fa8")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    for spine in ax.spines.values():
        spine.set_color("#2e3147")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="jpeg", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    hist_img = base64.b64encode(buf.read()).decode("utf-8")

    return {
        "max_depth_px":  max_depth,
        "mean_depth_px": mean_depth,
        "kde_x":         x_vals.tolist(),
        "kde_y":         y_vals.tolist(),
        "hist_img":      hist_img,
    }


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

        smask, cmask, gray = _get_masks(img)
        imgs               = build_transforms(img, smask, cmask, gray)
        depth              = compute_depth_stats(smask, cmask)

        return jsonify({
            "severity":      result["severity"],
            "confidence":    result["confidence"],
            "probabilities": result["probabilities"],
            "corroded_px":   result["corroded_px"],
            "corroded_pct":  result["corroded_pct"],
            "sample_px":     result["sample_px"],
            "depth":         depth,
            "images":        imgs,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    print("Loading model...")
    get_model()
    print("API ready at http://localhost:5000")
    app.run(debug=False, port=5000)
