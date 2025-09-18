from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import uuid
import io
import zipfile
import json
import os
from .storage import Storage, MetadataEntry
from .schema import UploadResponse

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
    serializable_items = []
    for r in results:
        item_dict = r.model_dump()
        if 'upload_timestamp' in item_dict and hasattr(item_dict['upload_timestamp'], 'isoformat'):
            item_dict['upload_timestamp'] = item_dict['upload_timestamp'].isoformat()
        serializable_items.append(item_dict)
    
    return JSONResponse(content={"user_id": user_id, "count": len(results), "items": serializable_items})


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

    entry_id = f"audio-{uuid.uuid4().time}"
    try:
        audio.file.seek(0, 2)
        file_size = audio.file.tell()
        audio.file.seek(0) 
        
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
        await storage.save_upload(entry=meta, file=audio.file)
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

        meta_list = []
        for e in entries:
            item_dict = e.model_dump()
            if 'upload_timestamp' in item_dict and hasattr(item_dict['upload_timestamp'], 'isoformat'):
                item_dict['upload_timestamp'] = item_dict['upload_timestamp'].isoformat()
            meta_list.append(item_dict)
        zf.writestr("metadata.json", json.dumps(meta_list, indent=2, ensure_ascii=False))

    buffer.seek(0)

    headers = {
        "Content-Disposition": f"attachment; filename=uploads_{user_id}.zip"
        }
    return StreamingResponse(buffer, media_type="application/zip", headers=headers, message="download zip", status_code=200)

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
    if 'upload_timestamp' in entry_dict and hasattr(entry_dict['upload_timestamp'], 'isoformat'):
        entry_dict['upload_timestamp'] = entry_dict['upload_timestamp'].isoformat()
    
    entry_dict['file_size'] = file_size  
    return entry_dict


@app.get("/health")
async def health():
    return {"status": "ok"}