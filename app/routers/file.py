# routes/file.py
import hashlib
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, Depends
from fastapi.responses import JSONResponse,  StreamingResponse
from typing import List
from app import oauth2
import io
from datetime import datetime
from app.database import FILE
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
    failed_files = []
    success = False
    for file in files:
        # hash the contents of the file
        hasher = hashlib.sha256()
        file_content = await file.read()
        hasher.update(file_content)
        file_hash = hasher.hexdigest()

        # check if the file already exists in the database
        existing_file = FILE.find_one({"hash": file_hash, "user_id": user_id})
        if existing_file:
            # the file already exists in the database, add it to the failed_files list
            failed_files.append(file.filename)
            continue

        file_id = str(uuid.uuid4())
        s3_key = f"{user_id}/{file.filename}"

        # upload the file to S3
        s3.put_object(Bucket=settings.AWS_BUCKET_NAME,
                      Key=s3_key, Body=file_content)

        # store the file information in the database
        stored_files.append({
            "file_id": file_id,
            "file_name": file.filename,
            "user_id": user_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "hash": file_hash
        })
        FILE.insert_one({
            "file_id": file_id,
            "file_name": file.filename,
            "user_id": user_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "hash": file_hash
        })

        success = True

    if success:
        if failed_files:
            return JSONResponse(content={"status": "success",
                                         "message": "Some files already exists and were not uploaded",
                                         "files": stored_files,
                                         "failed_files": failed_files})
        else:
            return JSONResponse(content={"status": "success",
                                         "message": "All files uploaded successfully",
                                         "files": stored_files})
    else:
        return JSONResponse(content={"status": "failed",
                                     "message": "All files already exist",
                                     "failed_files": failed_files})


@file.get("/list")
async def list_files(
    skip: int = 0,
    limit: int = 20,
    user_id: int = Depends(oauth2.require_user)
):
    files = FILE.find({"user_id": user_id}).skip(skip).limit(limit)
    files_list = []
    for file in files:
        s3_key = f"{user_id}/{file['file_id']}"
        try:
            obj = s3.head_object(Bucket=settings.AWS_BUCKET_NAME, Key=s3_key)
            timestamp = file.get("timestamp")
            file_timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            now = datetime.now()
            delta = now - file_timestamp
            if delta.days == 0:
                if delta.seconds < 60:
                    formatted_timestamp = f"{delta.seconds} seconds ago"
                elif delta.seconds < 3600:
                    formatted_timestamp = f"{delta.seconds // 60} minutes ago"
                elif delta.seconds < 7200:
                    formatted_timestamp = f"{delta.seconds // 3600} hour ago"
                else:
                    formatted_timestamp = f"{file_timestamp.strftime('%H:%M')}"
            elif delta.days == 1:
                formatted_timestamp = "yesterday"
            else:
                formatted_timestamp = f"{file_timestamp.strftime('%d %b %Y')}"
            file_size = max(round(obj['ContentLength'] / 1024, 1), 1)
            if file_size < 1024:
                formatted_file_size = f"{file_size} KB"
            else:
                formatted_file_size = f"{file_size / 1024:.1f} MB"
            files_list.append({
                "file_id": file.get("file_id"),
                "filename": file.get("file_name"),
                "timestamp": formatted_timestamp,
                "file_size": formatted_file_size,
            })
        except:
            pass

    if len(files_list) == 0:
        return JSONResponse(content={"message": "No data found"})

    return JSONResponse(content={"files": files_list})


@file.get("/download/{file_id}")
async def download_file(file_id: str, user_id: int = Depends(oauth2.require_user)):
    file = FILE.find_one({"file_id": file_id, "user_id": user_id})
    if file is None:
        raise HTTPException(status_code=400, detail="File not found")
    s3_key = f"{user_id}/{file_id}"
    obj = s3.get_object(Bucket=settings.AWS_BUCKET_NAME, Key=s3_key)
    file_content = obj["Body"].read()
    return StreamingResponse(io.BytesIO(file_content), media_type="application/octet-stream", headers={"Content-Disposition": f"attachment;filename={file['file_name']}"})
