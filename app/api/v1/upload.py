from typing import List
from app.core.config import settings
from supabase import create_client, Client
from fastapi import APIRouter, UploadFile, File, HTTPException, Path

router = APIRouter()
get_settings = settings()

supabase: Client = create_client(
    get_settings.SUPABASE_URL, 
    get_settings.SUPABASE_SERVICE_ROLE_KEY
)

async def upload(file: UploadFile, path: str):
    try:
        file_content = await file.read()
        content_type = file.content_type
        
        res = supabase.storage.from_(get_settings.BUCKET_NAME).upload(
            path=path,
            file=file_content,
            file_options={"content-type": content_type, "upsert": "true"}
        )
        
        url = supabase.storage.from_(get_settings.BUCKET_NAME).get_public_url(path)
        return url
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/customer/{id}/profile")
async def upload_customer_profile(
    id: str = Path(...), 
    file: UploadFile = File(...)
):
    ext = file.filename.split(".")[-1]
    path = f"customers/{id}/profile.{ext}"
    
    url = await upload(file, path)
    return {"success": True, "data": {"url":url}}

@router.post("/barber/{id}/profile")
async def upload_barber_profile(
    id: str = Path(...), 
    file: UploadFile = File(...)
):
    ext = file.filename.split(".")[-1]
    path = f"barbers/{id}/profile.{ext}"
    
    url = await upload(file, path)
    return {"success": True, "data": {"url":url}}


@router.post("/barber/{id}/shop-images")
async def upload_barber_shop_images(
    id: str = Path(...), 
    files: List[UploadFile] = File(...)
):
    urls = []
    
    for i, file in enumerate(files):
        ext = file.filename.split(".")[-1]
        path = f"barbers/{id}/shopimages/{i}.{ext}"
        url = await upload(file, path)
        urls.append(url)
    return {"success": True, "data": {"urls":urls}}