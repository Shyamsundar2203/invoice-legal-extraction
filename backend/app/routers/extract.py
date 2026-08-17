import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app import config
from app.pipeline.orchestrator import process_document
from app.schemas import ProcessingResult

router = APIRouter(prefix="/extract", tags=["extract"])

ALLOWED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tiff"}


@router.post("", response_model=ProcessingResult)
async def extract_document(
    file: UploadFile = File(...), doc_type: str = "invoice"
):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {ALLOWED_SUFFIXES}",
        )
    if doc_type not in {"invoice", "contract"}:
        raise HTTPException(status_code=400, detail="doc_type must be invoice|contract")

    dest = config.UPLOAD_DIR / file.filename
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        result = process_document(str(dest), doc_type=doc_type)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return result


@router.get("/{document_id}/overlay")
async def get_overlay_pdf(document_id: str):
    path = config.OUTPUT_DIR / f"{document_id}_overlay.pdf"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Overlay not found")
    return FileResponse(path, media_type="application/pdf", filename=path.name)
