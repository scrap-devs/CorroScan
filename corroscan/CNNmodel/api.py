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


def _convex_hull_mask(smask: np.ndarray) -> np.ndarray:
    """
    Fill the convex hull of the largest contour in smask.
    Returns a filled mask the same size as smask.
    This represents the 'ideal undamaged metal footprint'.
    """
    contours, _ = cv2.findContours(smask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    ideal = np.zeros_like(smask)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        hull = cv2.convexHull(largest)
        cv2.fillPoly(ideal, [hull], 255)
    return ideal


def _get_masks(img_bgr: np.ndarray):
    """
    Returns (smask, cmask, gray, pit_map, ideal_metal).

    Strategy
    --------
    Corrosion pits are RECESSES in the metal surface — they are outer-background
    regions that occupy space within the ideal (undamaged) metal outline.  This is
    physically correct and automatically excludes:
      - Polishing marks  (fine scratches INSIDE the metal, not connected to bg)
      - Inclusions       (dark particles INSIDE the metal, not connected to bg)
      - Scale bar widget (excluded from smask before hull computation)

    Steps:
    1. smask      = metal region (threshold > 20, minimal morphology to avoid
                    filling pit openings with a large close).
    2. outer_bg   = dark pixels connected to the image border.
    3. ideal_metal = convex hull of smask = what the undamaged surface would look like.
    4. cmask      = outer_bg ∩ ideal_metal = the actual pit-hole pixels.
    """
    h, w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # ── smask: bright metal pixels (Otsu threshold) ─────────────────────────
    # Otsu adapts per image so images where background > 20 grey still work.
    _, smask = cv2.threshold(gray, 0, 255,
                             cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    smask[int(h * 0.82):, int(w * 0.65):] = 0
    disk25 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    smask = cv2.morphologyEx(smask, cv2.MORPH_OPEN,  np.ones((5, 5), np.uint8))
    smask = cv2.morphologyEx(smask, cv2.MORPH_CLOSE, disk25)

    # ── Outer background (not-smask connected to image border) ───────────────
    # Includes the large exterior background AND pit holes (pit holes are dark
    # = not-smask, and are connected to the exterior through the surface opening).
    not_smask = cv2.bitwise_not(smask)
    _, bg_labels = cv2.connectedComponents(not_smask)
    border_labels = set()
    border_labels.update(bg_labels[0, :].tolist())
    border_labels.update(bg_labels[h-1, :].tolist())
    border_labels.update(bg_labels[:, 0].tolist())
    border_labels.update(bg_labels[:, w-1].tolist())
    border_labels.discard(0)

    outer_bg = np.isin(bg_labels, list(border_labels)).astype(np.uint8) * 255
    outer_bg[int(h * 0.82):, int(w * 0.65):] = 0

    # ── Ideal metal footprint ────────────────────────────────────────────────
    # Problem: Otsu smask captures only bright spots, so the hull starts well
    # inside the metal surface — causing the red to stop short of the edge.
    # Fix: use a low threshold (15) to capture dark edge pixels too, then
    # subtract outer_bg so the background isn't included in the hull region.
    _, smask_wide = cv2.threshold(gray, 15, 255, cv2.THRESH_BINARY)
    smask_wide[int(h * 0.82):, int(w * 0.65):] = 0
    smask_for_hull = cv2.bitwise_and(smask_wide, cv2.bitwise_not(outer_bg))
    smask_for_hull = cv2.morphologyEx(smask_for_hull, cv2.MORPH_OPEN,
                                      np.ones((5, 5), np.uint8))
    smask_for_hull = cv2.morphologyEx(smask_for_hull, cv2.MORPH_CLOSE,
                                      np.ones((15, 15), np.uint8))
    ideal_metal = _convex_hull_mask(smask_for_hull)

    # ── Pit mask: outer background within the ideal metal outline ────────────
    # These are the actual corroded recesses — the holes in the surface.
    cmask = cv2.bitwise_and(outer_bg, ideal_metal)

    # ── Filter: keep elongated pits, discard circular inclusions ─────────────
    # Corrosion pits are finger/channel shaped → high aspect ratio (W >> H or H >> W).
    # Inclusions / second-phase particles are compact dots → aspect ratio ≈ 1.
    # Rules (applied per connected component):
    #   • Drop anything < 100 px²  (pure noise).
    #   • Drop anything < 4000 px² whose bounding-box aspect ratio < 2.0.
    #     These are the small circular dots.  Large blobs (≥ 4000 px²) are
    #     kept regardless of shape so wide pit openings aren't lost.
    n_lbl, lbl_map, stats, _ = cv2.connectedComponentsWithStats(cmask, connectivity=8)
    filtered = np.zeros_like(cmask)
    for lbl in range(1, n_lbl):
        area_cc = stats[lbl, cv2.CC_STAT_AREA]
        cw      = stats[lbl, cv2.CC_STAT_WIDTH]
        ch      = stats[lbl, cv2.CC_STAT_HEIGHT]
        if area_cc < 100:
            continue
        aspect = max(cw, ch) / max(min(cw, ch), 1)
        if area_cc < 4000 and aspect < 2.0:   # small + circular = inclusion dot
            continue
        filtered[lbl_map == lbl] = 255
    cmask = filtered

    # ── pit_map kept for visualisation compatibility ─────────────────────────
    local_bg = cv2.GaussianBlur(gray, (201, 201), 0)
    diff     = local_bg.astype(np.int16) - gray.astype(np.int16)
    pit_map  = np.clip(diff, 0, 255).astype(np.uint8)

    return smask, cmask, gray, pit_map, ideal_metal


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


def compute_depth_stats(smask, cmask, _pit_map, ideal_metal=None,
                        pixels_per_unit: float = None, scale_unit: str = "px") -> dict:
    """
    Measure corrosion pit depth from the exposed metal surface.

    Depth definition
    ----------------
    For each pit pixel (in cmask), depth = its Euclidean distance to the
    nearest pixel on the IDEAL metal surface boundary (convex hull edge).

    This is physically correct:
    - The convex hull boundary represents the undamaged surface line.
    - Distance from a pit pixel to that boundary = how deep into the
      material the corrosion has penetrated at that location.
    - Works for any pit orientation (vertical, horizontal, oblique).
    - Correctly handles narrow finger-shaped pits: the pixel at the tip
      of a finger pit is far from the hull boundary (correct depth), not
      just far from the nearest pit wall.

    No polishing marks or inclusions contaminate this measurement because
    cmask was built from outer_bg ∩ ideal_metal (see _get_masks).
    """
    if np.sum(cmask > 0) == 0:
        return {
            "max_depth_px":  0.0,
            "mean_depth_px": 0.0,
            "kde_x":         [],
            "kde_y":         [],
            "hist_img":      None,
        }

    # Recompute ideal_metal if not provided
    if ideal_metal is None:
        ideal_metal = _convex_hull_mask(smask)

    # ── Distance from each pixel to the ideal surface boundary ───────────────
    # The boundary is the 1-pixel-wide outer edge of the convex hull.
    # Any pixel inside the hull has a well-defined distance to this boundary,
    # which equals its depth below the undamaged surface.
    ideal_interior = cv2.erode(ideal_metal, np.ones((3, 3), np.uint8))
    ideal_boundary = cv2.subtract(ideal_metal, ideal_interior)     # 1-px ring

    # distanceTransform needs the REFERENCE pixels to be 0
    boundary_inv = np.where(ideal_boundary > 0, 0, 255).astype(np.uint8)
    dist_to_surface = cv2.distanceTransform(boundary_inv, cv2.DIST_L2, 5)

    # ── Sample depths at pit pixels ───────────────────────────────────────────
    pit_depths = dist_to_surface[cmask > 0].astype(float)

    # Discard near-zero values (pixels right on the hull edge, 1-2 px rounding)
    pit_depths = pit_depths[pit_depths > 2.0]

    if len(pit_depths) < 10:
        return {
            "max_depth_px":  0.0,
            "mean_depth_px": 0.0,
            "kde_x":         [],
            "kde_y":         [],
            "hist_img":      None,
        }

    # Subsample for KDE speed
    if len(pit_depths) > 50_000:
        rng = np.random.default_rng(42)
        pit_depths = rng.choice(pit_depths, 50_000, replace=False)

    max_depth  = float(np.percentile(pit_depths, 99))
    mean_depth = float(pit_depths.mean())

    # ── Convert to real units if scale provided ───────────────────────────────
    if pixels_per_unit and pixels_per_unit > 0:
        plot_depths    = pit_depths / pixels_per_unit
        plot_max       = max_depth  / pixels_per_unit
        plot_mean      = mean_depth / pixels_per_unit
        unit_label     = scale_unit
        depth_fmt      = ".3f"
    else:
        plot_depths    = pit_depths
        plot_max       = max_depth
        plot_mean      = mean_depth
        unit_label     = "px"
        depth_fmt      = ".1f"

    # ── KDE curve ─────────────────────────────────────────────────────────────
    kde    = gaussian_kde(plot_depths, bw_method="scott")
    x_vals = np.linspace(0, plot_max * 1.05, 300)
    y_vals = kde(x_vals)

    # ── Matplotlib plot ────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(7, 3.5))

    ax.fill_between(x_vals, y_vals, alpha=0.35, color="#ef4444")
    ax.plot(x_vals, y_vals, color="#ef4444", linewidth=2.5)

    ax.axvline(plot_max,  color="#facc15", linestyle="--", linewidth=2,
               label=f"Max depth:  {plot_max:{depth_fmt}} {unit_label}")
    ax.axvline(plot_mean, color="#60a5fa", linestyle="--", linewidth=2,
               label=f"Mean depth: {plot_mean:{depth_fmt}} {unit_label}")

    ax.set_xlabel(f"Depth from undamaged surface ({unit_label})", color="#c0c4d6", fontsize=11)
    ax.set_ylabel("Probability density",                   color="#c0c4d6", fontsize=11)
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
        ppu_raw    = request.form.get("pixels_per_unit")
        ppu        = float(ppu_raw) if ppu_raw else None
        s_unit     = request.form.get("scale_unit", "px")

        model  = get_model()
        result = predict_image(tmp_path, model, CONFIG["device"])
        img    = cv2.imread(tmp_path)

        smask, cmask, gray, pit_map, ideal_metal = _get_masks(img)
        imgs                                     = build_transforms(img, smask, cmask, gray)
        depth                                    = compute_depth_stats(smask, cmask, pit_map, ideal_metal,
                                                                       pixels_per_unit=ppu, scale_unit=s_unit)

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
