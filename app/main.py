import io
import json
import os
import uuid
import zipfile
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .schema import UploadResponse
from .storage import MetadataEntry, Storage

app = FastAPI(title="Audio Processing Prototype")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


storage = Storage(base_path=os.getenv("DATA_DIR", "./audio-data"))


@app.on_event("startup")
async def startup_event():
    await storage.ensure_metadata()



@app.get("/list")
async def list_uploads(user_id: str = Query(...), tag: Optional[str] = Query(None)):
    """Return uploads for a user, optionally filtered by tag."""
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    results = await storage.list_user_uploads(user_id=user_id, tag=tag)
    return JSONResponse(
        content={
            "user_id": user_id,
            "count": len(results),
            "items": [r.model_dump() for r in results]
            }
            )


@app.post("/upload", response_model=UploadResponse)
async def upload_audio(
    user_id: str = Form(...),
    tags: Optional[str] = Form(None),
    audio: UploadFile = File(...),
    title: Optional[str] = Form(None),
    artist: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
):

    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    if not audio.filename:
        raise HTTPException(status_code=400, detail="audio file must have a filename")

    parsed_tags: List[str] = []
    if tags:
        try:
            parsed_tags = json.loads(tags)
            if not isinstance(parsed_tags, list) or not all(isinstance(t, str) for t in parsed_tags):
                raise ValueError()
        except Exception:
            parsed_tags = [t.strip() for t in tags.split(",") if t.strip()]

    entry_id = str(uuid.uuid4())
    try:
        # Read file content to get size
        file_content = await audio.read()
        file_size = len(file_content)
        
        meta = MetadataEntry(
            id=entry_id,
            user_id=user_id,
            filename=audio.filename,
            content_type=audio.content_type or "application/octet-stream",
            tags=parsed_tags,
            file_size=file_size,
            title=title,
            artist=artist,
            description=description,
        )
        await storage.save_upload(entry=meta, file=file_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed saving upload: {e}")

    return UploadResponse(status="ok", id=entry_id)


@app.get("/download")
async def download_user_zip(user_id: str = Query(...)):
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    entries = await storage.list_user_uploads(user_id=user_id)
    if not entries:
        raise HTTPException(status_code=404, detail="no uploads found for user")

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for e in entries:
            file_path = storage.get_user_file_path(e)
            arcname = os.path.basename(file_path)
            zf.write(file_path, arcname=f"uploads/{arcname}")

        meta_list = [e.model_dump() for e in entries]
        zf.writestr("metadata.json", json.dumps(meta_list, indent=2, ensure_ascii=False))

    buffer.seek(0)

    headers = {
        "Content-Disposition": f"attachment; filename=uploads_{user_id}.zip"
    }
    return StreamingResponse(buffer, media_type="application/zip", headers=headers)


@app.get("/files/{file_id}")
async def get_file(file_id: str, user_id: str = Query(...)):
    """Download individual file by ID."""
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    entries = await storage.list_user_uploads(user_id=user_id)
    entry = next((e for e in entries if e.id == file_id), None)
    
    if not entry:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = storage.get_user_file_path(entry)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    return StreamingResponse(
        open(file_path, "rb"),
        media_type=entry.content_type,
        headers={"Content-Disposition": f"attachment; filename={entry.filename}"}
    )


@app.delete("/files/{file_id}")
async def delete_file(file_id: str, user_id: str = Query(...)):
    """Delete a file by ID."""
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    entries = await storage.list_user_uploads(user_id=user_id)
    entry = next((e for e in entries if e.id == file_id), None)
    
    if not entry:
        raise HTTPException(status_code=404, detail="File or user not associated with file")
    
    # Remove from storage
    await storage.delete_upload(entry)
    return {"status": "deleted", "id": file_id}


@app.get("/files/{file_id}/info")
async def get_file_info(file_id: str, user_id: str = Query(...)):
    """Get file metadata by ID."""
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    entries = await storage.list_user_uploads(user_id=user_id)
    entry = next((e for e in entries if e.id == file_id), None)
    
    if not entry:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = storage.get_user_file_path(entry)
    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    
    entry_dict = entry.model_dump()
    entry_dict['file_size'] = file_size
    return entry_dict


@app.get("/health")
async def health():
    return {"status": "ok"}