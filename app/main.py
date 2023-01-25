from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, user, ocr

app = FastAPI()

# origins = [
#     settings.CLIENT_ORIGIN, # now in development mode
# ]

app.add_middleware(
    CORSMiddleware,
    # allow_origins=origins,
    allow_origins=['*'],  # now in development mode
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    return {
        "Message": "Search - BackEnd",
        "Author": "Farhan Aulianda"
    }

app.include_router(auth.router, tags=['Auth'], prefix='/api/auth')
app.include_router(user.router, tags=['Users'], prefix='/api/users')
app.include_router(ocr.ocr, tags=['OCR'], prefix='/api/ocr')
