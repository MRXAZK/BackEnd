# routes/ocr.py
from fastapi import APIRouter, UploadFile, Depends
from fastapi.responses import JSONResponse
from typing import List
from app import oauth2
import pymongo
import cv2
import io
import numpy as np
import pytesseract
from datetime import datetime
from app.database import OCR
from app.config import settings
import fitz
import pandas as pd
from docx import Document
import boto3


ocr = APIRouter()

s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_KEY,
        region_name=settings.AWS_REGION
    )


def read_pdf(pdf_file):
    pdf = fitz.open(stream=pdf_file)
    text = ""
    for page in pdf:
        text += page.get_text("text")
    return text


def read_excel(excel_file):
    df = pd.read_excel(excel_file)
    text = "".join(df.to_string())
    return text


def read_csv(csv_file):
    df = pd.read_csv(csv_file)
    text = "".join(df.to_string())
    return text


def read_word(word_file):
    doc = Document(word_file)
    text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += '\n'+cell.text
    return text


def read_img(img):
    text = pytesseract.image_to_string(img)
    return (text)


@ocr.post("/extract_text")
async def extract_text(files: List[UploadFile], user_id: int = Depends(oauth2.require_user)):
    extracted_texts = []
    for file in files:
        try:
            text = ""
            if file.content_type == "application/pdf":
                pdf_file = io.BytesIO(await file.read())
                text = read_pdf(pdf_file)
            elif file.content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                excel_file = io.BytesIO(await file.read())
                text = read_excel(excel_file)
            elif file.content_type == "text/csv":
                csv_file = io.BytesIO(await file.read())
                text = read_csv(csv_file)
            elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                word_file = io.BytesIO(await file.read())
                text = read_word(word_file)
            else:
                img = await file.read()
                image_stream = io.BytesIO(img)
                image_stream.seek(0)
                file_bytes = np.asarray(
                    bytearray(image_stream.read()), dtype=np.uint8)
                frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                text = read_img(frame)
            extracted_texts.append(text)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            s3_key = f"{user_id}/{file.filename}_{timestamp}"
            s3.put_object(Bucket=settings.AWS_BUCKET_NAME, Key=s3_key, Body=text)
        except Exception as e:
            print(f'Error: {e}')
    return JSONResponse(content={"status": "success", "extracted_texts": extracted_texts})
