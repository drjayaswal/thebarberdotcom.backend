import asyncio

from app.core.config import settings
from supabase import create_client, Client
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Path

from app.database.db import get_db
from app.models.schema import Barber
from app.models.schema import Barber

router = APIRouter()
get_settings = settings()

supabase: Client = create_client(
    get_settings.SUPABASE_URL, 
    get_settings.SUPABASE_SERVICE_ROLE_KEY
)

upload_semaphore = asyncio.Semaphore(2)

async def upload(file: UploadFile, path: str):
    async with upload_semaphore:
        try:
            file_content = await file.read()
            content_type = file.content_type
            
            options = {"content-type": content_type, "x-upsert": "true"}

            await run_in_threadpool(
                supabase.storage.from_(get_settings.BUCKET_NAME).upload,
                path=path,
                file=file_content,
                file_options=options
            )
            
            url = supabase.storage.from_(get_settings.BUCKET_NAME).get_public_url(path)
            return url
        except Exception as e:
            print(f"UPLOAD ERROR: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/customer/{id}/profile")
async def upload_customer_profile(
    id: str = Path(...), 
    file: UploadFile = File(...)
):
    try:
        ext = file.filename.split(".")[-1] if file.filename else "jpg"
        path = f"customers/{id}/profile.{ext}"
        
        url = await upload(file, path)
        return {"success": True, "data": {"url":url}}
    except Exception as e:
        error_msg = e.detail if isinstance(e, HTTPException) else str(e)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Internal Server Error: {error_msg}"}
        )

@router.post("/barber/{id}/profile")
async def upload_barber_profile(
    id: str = Path(...), 
    file: UploadFile = File(...)
):
    try:
        ext = file.filename.split(".")[-1] if file.filename else "jpg"
        path = f"barbers/{id}/profile.{ext}"
        
        url = await upload(file, path)
        return {"success": True, "data": {"url":url}}
    except Exception as e:
        error_msg = e.detail if isinstance(e, HTTPException) else str(e)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Internal Server Error: {error_msg}"}
        )

@router.post("/barber/{id}/shop-images")
async def upload_barber_shop_images(
    id: str = Path(...), 
    file: UploadFile = File(...),
    db = Depends(get_db)
):
    try:
        barber = db.query(Barber).filter(Barber.id == id).first()
        if not barber:
            raise HTTPException(status_code=404, detail="Barber not found")
        
        barber.shop_images = barber.shop_images or []

        ext = file.filename.split(".")[-1] if file.filename else "jpg"
        path = f"barbers/{id}/shopimages/{int(barber.shop_images[-1].split('/')[-1].split('.')[0])+1 if barber.shop_images else 0}.{ext}"
        url = await upload(file, path)
        return {"success": True, "data": {"url": url}}
    except Exception as e:
        error_msg = e.detail if isinstance(e, HTTPException) else str(e)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Internal Server Error: {error_msg}"}
        )    