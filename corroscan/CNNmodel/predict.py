"""
predict.py
----------
Run the trained CorroScan model on one or more images.

Usage:
    python predict.py path/to/image.jpg
    python predict.py path/to/folder/
"""

import sys
import os
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train import predict_image, build_model, CONFIG

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "best_model.pth")


def load_model():
    if not os.path.exists(MODEL_PATH):
        print(f"[ERROR] No trained model found at {MODEL_PATH}")
        print("Run  python train.py  first.")
        sys.exit(1)
    device = CONFIG["device"]
    model  = build_model(num_classes=2, device=device)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    model.eval()
    print(f"Model loaded from {MODEL_PATH}\n")
    return model, device


def run(image_path: str, model, device):
    print(f"Image : {os.path.basename(image_path)}")
    try:
        result = predict_image(image_path, model, device)
    except FileNotFoundError as e:
        print(f"  [ERROR] {e}\n")
        return

    print(f"  Severity    : {result['severity'].upper()}")
    print(f"  Confidence  : {result['confidence'] * 100:.1f}%")
    print(f"  Probabilities:")
    for label, prob in result["probabilities"].items():
        bar = "█" * int(prob * 20)
        print(f"    {label:<10} {prob * 100:5.1f}%  {bar}")
    print(f"  Corroded px : {result['corroded_px']:,}")
    print(f"  Corroded    : {result['corroded_pct']:.2f}% of image")
    print()


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python predict.py path/to/image.jpg")
        print("  python predict.py path/to/folder/")
        sys.exit(1)

    model, device = load_model()
    target = sys.argv[1]

    if os.path.isdir(target):
        images = [
            os.path.join(target, f)
            for f in sorted(os.listdir(target))
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        if not images:
            print(f"[ERROR] No images found in {target}")
            sys.exit(1)
        print(f"Found {len(images)} images in {target}\n{'─'*50}")
        for path in images:
            run(path, model, device)
    elif os.path.isfile(target):
        run(target, model, device)
    else:
        print(f"[ERROR] Path not found: {target}")
        sys.exit(1)


if __name__ == "__main__":
    main()
