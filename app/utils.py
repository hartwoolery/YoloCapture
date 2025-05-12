import random, glob, io, cv2, numpy as np
from pathlib import Path
import supervision as sv               

# ---------- picking a file --------------------------------
def random_img_and_label(ds_root: Path) -> tuple[Path, Path]:
    matches = glob.glob(str(ds_root / "*" / "images" / "*.jpg"))
    if not matches:
        raise FileNotFoundError("Dataset is empty")
    img_path = Path(random.choice(matches))
    label_path = (
        img_path.parent.parent / "labels" / img_path.name.replace(".jpg", ".txt")
    )
    return img_path, label_path

# ---------- drawing with supervision ----------------------
def jpeg_with_boxes(img_path: Path, label_path: Path) -> bytes:
    image = cv2.imread(str(img_path))          # BGR uint8
    if image is None:
        raise RuntimeError(f"Couldn’t read {img_path}")

    h, w = image.shape[:2]

    # Parse YOLOv7 txt → xyxy + class IDs
    boxes, class_ids = [], []
    if label_path.exists():
        for line in label_path.read_text().strip().splitlines():
            cls, xc, yc, bw, bh = map(float, line.split())
            x0 = (xc - bw / 2) * w
            y0 = (yc - bh / 2) * h
            x1 = (xc + bw / 2) * w
            y1 = (yc + bh / 2) * h
            boxes.append([x0, y0, x1, y1])
            class_ids.append(int(cls))

    if boxes:
        detections = sv.Detections(
            xyxy=np.array(boxes, dtype=float),
            class_id=np.array(class_ids, dtype=int),
        )
        annotator = sv.BoxAnnotator()          # red boxes + class ID text
        image = annotator.annotate(scene=image, detections=detections)

    ok, buf = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ok:
        raise RuntimeError("JPEG encode failed")
    return buf.tobytes()
