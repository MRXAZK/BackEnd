# routes/file.py
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, Depends
from fastapi.responses import JSONResponse,  StreamingResponse
from typing import List
from app import oauth2
import io
from datetime import datetime
from app.database import OCR
from app.config import settings
import boto3


file = APIRouter()

s3 = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY,
    aws_secret_access_key=settings.AWS_SECRET_KEY,
    region_name=settings.AWS_REGION
)


@file.post("/upload")
async def upload_file(files: List[UploadFile], user_id: int = Depends(oauth2.require_user)):
    stored_files = []
    for file in files:
        file_id = str(uuid.uuid4())
        s3_key = f"{user_id}/{file_id}"
        s3.put_object(Bucket=settings.AWS_BUCKET_NAME,
                      Key=s3_key, Body=await file.read())
        stored_files.append({
            "file_id": file_id,
            "file_name": file.filename,
            "user_id": user_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    OCR.insert_many(stored_files)
    return JSONResponse(content={"message": "File uploaded successfully"})


@file.post("/list")
async def list_files(user_id: int = Depends(oauth2.require_user)):
    files = OCR.objects(user_id=user_id)
    files_list = []
    for file in files:
        files_list.append({
            "id": str(file.id),
            "filename": file.filename,
            "file_size": file.file_size,
            "timestamp": file.timestamp
        })
    return JSONResponse(content={"files": files_list})


@file.get("/download/{file_id}")
async def download_file(file_id: str, user_id: int = Depends(oauth2.require_user)):
    file = OCR.find_one({"file_id": file_id, "user_id": user_id})
    if file is None:
        raise HTTPException(status_code=400, detail="File not found")
    s3_key = f"{user_id}/{file_id}"
    obj = s3.get_object(Bucket=settings.AWS_BUCKET_NAME, Key=s3_key)
    file_content = obj["Body"].read()
    return StreamingResponse(io.BytesIO(file_content), media_type="application/octet-stream", headers={"Content-Disposition": f"attachment;filename={file['file_name']}"})
