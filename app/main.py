from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from fastapi.openapi.utils import get_openapi
from app.routers import auth, dashboard, file, user

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


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Career Assistant BackEnd",
        version="0.1",
        description="This is Rest API for FrontEnd https://fe.farhanaulianda.tech/",
        routes=app.routes,
    )

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/", tags=["Root"])
async def root():
    return {
        "Message": "BackEnd",
        "Author": "Farhan Aulianda"
    }

app.include_router(auth.router, tags=['Auth'], prefix='/api/auth')
app.include_router(file.file, tags=['Files'], prefix='/api/file')
app.include_router(dashboard.router, tags=[
                   'Dashboard'], prefix='/api/dashboard')
app.include_router(user.router, tags=['Users'], prefix='/api/users')
