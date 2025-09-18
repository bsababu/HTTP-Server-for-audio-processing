from pydantic import BaseModel

class UploadResponse(BaseModel):
    status: str
    id: str