"""Batch upload endpoint — upload multiple PDFs at once."""
from __future__ import annotations

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List

from revival.services.batch_upload import batch_upload, validate_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/batch", tags=["batch"])


@router.post("/upload")
async def upload_multiple(files: List[UploadFile] = File(...)):
    """Upload multiple PDF files for processing."""
    if len(files) > 10:
        raise HTTPException(400, "Maximum 10 files per batch")

    if len(files) == 0:
        raise HTTPException(400, "No files provided")

    # Read and validate all files
    validated = []
    errors = []

    for file in files:
        content = await file.read()
        error = validate_file(file.filename, content)
        if error:
            errors.append({"filename": file.filename, "error": error})
        else:
            validated.append((file.filename, content))

    if not validated and errors:
        raise HTTPException(400, detail={"message": "All files failed validation", "errors": errors})

    # Process valid files
    results = await batch_upload(validated)

    return {
        "processed": len(results),
        "results": results,
        "validation_errors": errors,
    }


@router.get("/status/{batch_id}")
async def get_batch_status(batch_id: str):
    """Get the status of a batch upload."""
    # TODO: implement batch tracking with database
    return {"batch_id": batch_id, "status": "not_implemented"}
