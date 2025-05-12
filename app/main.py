from pathlib import Path
import uuid
import tempfile
import shutil
import os
import base64
from typing import Set, Annotated
import random
import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field

from .utils import random_img_and_label, jpeg_with_boxes

app = FastAPI()

# --- config -----------------------------------------------------------
DATASET_ROOT = Path("datasets")
SPLITS = ["train", "val", "test"]
SPLIT_WEIGHTS = [0.8, 0.1, 0.1]           # 80/10/10

def pick_split() -> str:
    return random.choices(SPLITS, weights=SPLIT_WEIGHTS, k=1)[0]

def gen_filename() -> str:
    ts   = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    tail = uuid.uuid4().hex[:8]
    return f"{ts}-{tail}.jpg"

# ----------------------------------------------------------------------

class UploadRequest(BaseModel):
    dataset: Annotated[str, Field(min_length=1, pattern=r"^[\w\-]+$")]
    image_b64: str
    label: str

# --- helpers ----------------------------------------------------------
def _ensure_dirs(dataset: str):
    for split in SPLITS:
        (DATASET_ROOT / dataset / split / "images").mkdir(parents=True, exist_ok=True)
        (DATASET_ROOT / dataset / split / "labels").mkdir(parents=True, exist_ok=True)

def _validate_label(label: str) -> None:
    """Validate the label format."""
    if not label.strip():
        raise HTTPException(400, "Label cannot be empty")
    # Add any additional label validation rules here

def _decode_base64_image(image_b64: str) -> bytes:
    """Decode base64 image string to bytes."""
    try:
        return base64.b64decode(image_b64)
    except Exception as e:
        raise HTTPException(400, f"Invalid base64 image: {str(e)}")
# ----------------------------------------------------------------------

@app.post("/upload", status_code=201)
def upload(item: UploadRequest):
    _validate_label(item.label)
    img_bytes = _decode_base64_image(item.image_b64)

    _ensure_dirs(item.dataset)

    split     = pick_split()          # ← backend decides
    filename  = gen_filename()        # ← backend decides
    img_path  = DATASET_ROOT / item.dataset / split / "images"  / filename
    label_path= DATASET_ROOT / item.dataset / split / "labels" / filename.replace(".jpg", ".txt")

    img_path.write_bytes(img_bytes)
    label_path.write_text(item.label.strip() + "\n")

    return {
        "status":  "stored",
        "dataset": item.dataset,
        "split":   split,
        "image":   str(img_path.relative_to(DATASET_ROOT)),
        "label":   str(label_path.relative_to(DATASET_ROOT)),
    }

# ----------------------------------------------------------------------

@app.get("/dataset/{dataset}/preview", response_class=Response)
def preview_random(dataset: str):
    ds_root = DATASET_ROOT / dataset
    if not ds_root.exists():
        raise HTTPException(404, f"Dataset '{dataset}' not found")

    try:
        img_path, label_path = random_img_and_label(ds_root)
        jpeg = jpeg_with_boxes(img_path, label_path)
    except FileNotFoundError:
        raise HTTPException(404, "No images available in this dataset")

    return Response(jpeg, media_type="image/jpeg")


# ----------------------------------------------------------------------

@app.get("/dataset/{dataset}/download")
def download_dataset(dataset: str, bg: BackgroundTasks):
    ds_path = DATASET_ROOT / dataset
    if not ds_path.exists():
        raise HTTPException(404, f"Dataset '{dataset}' not found")

    tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp_zip.close()
    shutil.make_archive(tmp_zip.name[:-4], "zip", ds_path)

    bg.add_task(lambda: os.remove(tmp_zip.name))
    return StreamingResponse(
        open(tmp_zip.name, "rb"),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{dataset}.zip"'
        },
    )
