import os
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from auth import require_auth
from config import UPLOADS_DIR

router = APIRouter(prefix="/api/uploads", tags=["Uploads"])

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".md", ".json", ".zip"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("")
async def upload_file(file: UploadFile = File(...), user=Depends(require_auth)):
    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Generate safe unique filename
    safe_name = f"{uuid.uuid4().hex[:10]}_{re_slug(Path(filename).stem)}{ext}"
    target_path = UPLOADS_DIR / safe_name

    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    file_size = target_path.stat().st_size
    relative_url = f"/static/uploads/{safe_name}"

    return {
        "original_name": filename,
        "saved_name": safe_name,
        "url": relative_url,
        "file_path": str(target_path),
        "size_bytes": file_size,
        "extension": ext,
    }


def re_slug(text: str) -> str:
    import re
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "_", text)[:50]
