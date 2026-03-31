"""
test_pipeline.py
----------------
Quick visual check of scale bar detection and corrosion segmentation.
Run BEFORE training to confirm the CV functions work on your images.

Usage:
    python test_pipeline.py                         # tests all images in data/images/
    python test_pipeline.py path/to/image.jpg       # tests one specific image

Outputs saved to: CNNmodel/debug_output/
"""

import sys
import os
import cv2
import numpy as np

# Import the two CV functions directly from train.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train import detect_scale_bar, estimate_corroded_area

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
OUT_DIR    = os.path.join(BASE_DIR, "debug_output")
IMAGES_DIR = os.path.join(BASE_DIR, "data", "images", "Pit Training Data")

os.makedirs(OUT_DIR, exist_ok=True)


def annotate_and_save(image_path: str):
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        print(f"  [ERROR] Cannot read {image_path}")
        return

    h, w = img_bgr.shape[:2]
    name  = os.path.splitext(os.path.basename(image_path))[0]

    print(f"\n{'-'*60}")
    print(f"Image : {os.path.basename(image_path)}")
    print(f"Size  : {w} x {h} px")

    # ── Scale bar detection ──────────────────────────────────────────
    _, bar_px, _ = detect_scale_bar(img_bgr)

    scale_img = img_bgr.copy()
    roi_y = int(h * 0.82)
    roi_x = int(w * 0.65)

    if bar_px:
        print(f"Scale bar  : {bar_px} px wide")

        # Draw a cyan box around the detected scale bar region
        cv2.rectangle(scale_img,
                      (roi_x, roi_y), (w - 1, h - 1),
                      (255, 255, 0), 2)
        label = f"{bar_px}px"
        cv2.putText(scale_img, label,
                    (roi_x, roi_y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    else:
        print("Scale bar  : NOT DETECTED")
        cv2.putText(scale_img, "SCALE BAR NOT DETECTED",
                    (20, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    # ── Corrosion segmentation ───────────────────────────────────────
    corroded_px, corroded_pct = estimate_corroded_area(img_bgr)
    print(f"Corroded   : {corroded_px} px  ({corroded_pct}% of image)")

    # Rebuild the masks for visualisation (mirrors estimate_corroded_area internals)
    gray     = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
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
    k        = np.ones((3, 3), np.uint8)
    cmask    = cv2.morphologyEx(cmask, cv2.MORPH_OPEN,  k)
    cmask    = cv2.morphologyEx(cmask, cv2.MORPH_CLOSE, k)

    # Shape filter: remove tall thin scratch lines (height > 5x width)
    filtered = np.zeros_like(cmask)
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(cmask, connectivity=8)
    for lbl in range(1, n_labels):
        cw = stats[lbl, cv2.CC_STAT_WIDTH]
        ch = stats[lbl, cv2.CC_STAT_HEIGHT]
        area_cc = stats[lbl, cv2.CC_STAT_AREA]
        if area_cc < 5:
            continue
        if ch > cw * 5:
            continue
        filtered[labels == lbl] = 255
    cmask = filtered

    # Overlay: sample region = faint blue tint, corrosion = red highlight
    overlay = img_bgr.copy()
    overlay[smask > 0] = (overlay[smask > 0] * 0.85 + np.array([30, 0, 0])).clip(0, 255).astype(np.uint8)
    overlay[cmask > 0] = (overlay[cmask > 0] * 0.4  + np.array([0, 0, 180])).clip(0, 255).astype(np.uint8)

    # Blend overlay with original
    seg_img = cv2.addWeighted(img_bgr, 0.5, overlay, 0.5, 0)
    cv2.putText(seg_img, f"Corroded: {corroded_px} px  ({corroded_pct}% of image)",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    # ── Save outputs ─────────────────────────────────────────────────
    scale_out = os.path.join(OUT_DIR, f"{name}_1_scalebar.jpg")
    seg_out   = os.path.join(OUT_DIR, f"{name}_2_segmentation.jpg")
    mask_out  = os.path.join(OUT_DIR, f"{name}_3_mask.jpg")

    cv2.imwrite(scale_out, scale_img)
    cv2.imwrite(seg_out,   seg_img)
    cv2.imwrite(mask_out,  cmask)

    print(f"Saved: {os.path.relpath(scale_out, BASE_DIR)}")
    print(f"Saved: {os.path.relpath(seg_out,   BASE_DIR)}")
    print(f"Saved: {os.path.relpath(mask_out,  BASE_DIR)}")


def main():
    print(f"Output directory    : {OUT_DIR}")

    if len(sys.argv) > 1:
        # Single image passed as argument
        targets = [sys.argv[1]]
    else:
        # Run on everything in data/images/
        if not os.path.isdir(IMAGES_DIR):
            print(f"\n[ERROR] No images folder found at: {IMAGES_DIR}")
            print("Create it and drop your .jpg files inside, or pass an image path as argument.")
            print("  e.g.  python test_pipeline.py C:/path/to/image.jpg")
            sys.exit(1)
        targets = [
            os.path.join(IMAGES_DIR, f)
            for f in sorted(os.listdir(IMAGES_DIR))
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        if not targets:
            print(f"\n[ERROR] No images found in {IMAGES_DIR}")
            sys.exit(1)

    for path in targets:
        annotate_and_save(path)

    print(f"\n{'-'*60}")
    print(f"Done. Open  {OUT_DIR}  to review the outputs.")
    print("Each image produces three files:")
    print("  _1_scalebar.jpg    — detected scale bar region highlighted")
    print("  _2_segmentation.jpg — corrosion highlighted in red over the image")
    print("  _3_mask.jpg        — raw binary corrosion mask")


if __name__ == "__main__":
    main()
