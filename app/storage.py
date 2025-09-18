import os
import json
import asyncio
from typing import List, Optional
import aiofiles
from pydantic import BaseModel, Field
from datetime import datetime

class MetadataEntry(BaseModel):
    id: str
    user_id: str
    filename: str
    content_type: str
    tags: Optional[List[str]] = None
    
    file_size: Optional[int] = None
    upload_timestamp: datetime = Field(default_factory=datetime.now)

    title: Optional[str] = None
    artist: Optional[str] = None
    description: Optional[str] = None

class Storage:
    def __init__(self, base_path: str = "./audio-data"):
        self.base_path = base_path
        self.uploads_path = os.path.join(self.base_path, "uploads")
        self.metadata_path = os.path.join(self.base_path, "metadata.json")
        self._lock = asyncio.Lock()

    async def ensure_metadata(self):
        os.makedirs(self.uploads_path, exist_ok=True)
        if not os.path.exists(self.metadata_path):
            async with aiofiles.open(self.metadata_path, mode="w") as f:
                await f.write(json.dumps([]))


    async def _read_metadata(self) -> List[MetadataEntry]:
        async with self._lock:
            async with aiofiles.open(self.metadata_path, mode="r") as f:
                content = await f.read()
                try:
                    raw = json.loads(content or "[]")
                except Exception:
                    raw = []

                entries = []
                for r in raw:
                    if 'upload_timestamp' in r and isinstance(r['upload_timestamp'], str):
                        try:
                            r['upload_timestamp'] = datetime.fromisoformat(r['upload_timestamp'])
                        except:
                            r['upload_timestamp'] = datetime.now()
                    entries.append(MetadataEntry(**r))
                return entries


    async def _write_metadata(self, items: List[MetadataEntry]):
        async with self._lock:
            async with aiofiles.open(self.metadata_path, mode="w") as f:
                serializable_items = []
                for item in items:
                    item_dict = item.model_dump()
                    if isinstance(item_dict.get('upload_timestamp'), datetime):
                        item_dict['upload_timestamp'] = item_dict['upload_timestamp'].isoformat()
                    serializable_items.append(item_dict)
                await f.write(json.dumps(serializable_items, indent=2, ensure_ascii=False))


    def _user_folder(self, user_id: str) -> str:
        path = os.path.join(self.uploads_path, user_id)
        os.makedirs(path, exist_ok=True)
        return path


    async def save_upload(self, entry: MetadataEntry, file) -> None:
        user_folder = self._user_folder(entry.user_id)
        # ensure filename safe
        filename = f"{entry.id}_{entry.filename}"
        path = os.path.join(user_folder, filename)

        async with aiofiles.open(path, mode="wb") as out_f:
            file.seek(0)
            while True:
                chunk = file.read(1024 * 64)
                if not chunk:
                    break
                await out_f.write(chunk)

        items = await self._read_metadata()
        items.append(entry)
        await self._write_metadata(items)


    async def list_user_uploads(self, user_id: str, tag: Optional[str] = None) -> List[MetadataEntry]:
        items = await self._read_metadata()
        filtered = [i for i in items if i.user_id == user_id]
        if tag:
            filtered = [i for i in filtered if tag in (i.tags or [])]
        return filtered


    def get_user_file_path(self, entry: MetadataEntry) -> str:
        user_folder = self._user_folder(entry.user_id)
        filename = f"{entry.id}_{entry.filename}"
        return os.path.join(user_folder, filename)

    async def delete_upload(self, entry: MetadataEntry) -> None:
        """Delete a file and remove from metadata."""
        # Delete physical file
        file_path = self.get_user_file_path(entry)
        if os.path.exists(file_path):
            os.remove(file_path)
            
        items = await self._read_metadata()
        items = [i for i in items if i.id != entry.id]
        await self._write_metadata(items)