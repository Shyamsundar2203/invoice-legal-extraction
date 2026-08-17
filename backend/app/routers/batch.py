import csv
import io
import shutil
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app import config
from app.pipeline.orchestrator import process_batch
from app.schemas import BatchSummaryRow, ProcessingResult

router = APIRouter(prefix="/batch", tags=["batch"])


@router.post("", response_model=List[ProcessingResult])
async def batch_extract(
    files: List[UploadFile] = File(...), doc_type: str = "invoice"
):
    saved_paths = []
    for file in files:
        dest = config.UPLOAD_DIR / file.filename
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        saved_paths.append(str(dest))

    try:
        results = process_batch(saved_paths, doc_type=doc_type)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return results


@router.get("/summary.csv")
async def batch_summary_csv():
    """Aggregate every processed *_result.json into one CSV report."""
    rows: List[BatchSummaryRow] = []
    for result_file in sorted(config.OUTPUT_DIR.glob("*_result.json")):
        import json

        payload = json.loads(result_file.read_text(encoding="utf-8"))
        rows.append(
            BatchSummaryRow(
                document_id=payload["document_id"],
                filename=payload["filename"],
                doc_type=payload["doc_type"],
                overall_confidence=payload["overall_confidence"],
                needs_review=payload["needs_review"],
                processing_time_ms=payload["processing_time_ms"],
                status="review" if payload["needs_review"] else "ok",
            )
        )

    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "document_id",
            "filename",
            "doc_type",
            "overall_confidence",
            "needs_review",
            "processing_time_ms",
            "status",
        ],
    )
    writer.writeheader()
    for r in rows:
        writer.writerow(r.model_dump())

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=batch_summary.csv"},
    )
